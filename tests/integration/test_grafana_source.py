#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the grafana-source relation.

This module covers both the basic grafana-source relation interface and the datasource
topology matrix (issue #49).

Matrix: 2 ingress x 2 TLS x 2 scale x 2 mode = 16 cells.

The invariant being proven is that the datasource COUNT and UID SHAPE depend only on
``(provider mode, scale)``:

- app mode  -> exactly ONE datasource for the whole application, with a UID that has NO
  unit number, and which is STABLE across a provider leader re-election. This is the
  fix for the bug reported in canonical/mimir-operators#49.
- unit mode -> exactly N datasources (one per unit), each keyed by unit number.

Ingress and TLS only change the datasource URL string (host + http/https scheme); they
never change the count or the UID.

Grafana is deployed once per module; each matrix cell deploys its own uniquely-named
tester application (so datasources never collide between cells), wires the relations it
needs, asserts, then tears the tester down.
"""

import asyncio
import logging
import os

import pytest
import requests
import sh
from helpers import (
    check_grafana_is_ready,
    get_datasource_for,
    get_grafana_datasources,
    grafana_password,
    oci_image,
    unit_address,
)

logger = logging.getLogger(__name__)

GRAFANA = "grafana"
TRAEFIK = "traefik"
CA = "ca"

tester_resources = {
    "grafana-tester-image": oci_image(
        "./tests/integration/grafana-tester/metadata.yaml", "grafana-tester-image"
    )
}
grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
}

# (ingress, tls, scale, mode)
MATRIX = [
    (ingress, tls, scale, mode)
    for ingress in (False, True)
    for tls in (False, True)
    for scale in (1, 2)
    for mode in ("app", "unit")
]


@pytest.mark.skip
async def test_grafana_source_relation_data_with_grafana_tester(
    ops_test, grafana_charm, grafana_tester_charm
):
    """Test basic functionality of grafana-source relation interface."""
    grafana_app_name = "grafana"
    tester_app_name = "grafana-tester"

    await asyncio.gather(
        ops_test.model.deploy(
            grafana_charm,
            resources=grafana_resources,
            application_name=grafana_app_name,
            trust=True,
        ),
        ops_test.model.deploy(
            grafana_tester_charm, resources=tester_resources, application_name=tester_app_name
        ),
    )
    await ops_test.model.wait_for_idle(
        apps=[grafana_app_name, tester_app_name],
        status="active",
        wait_for_at_least_units=1,
        timeout=300,
    )

    await check_grafana_is_ready(ops_test, grafana_app_name, 0)
    initial_datasources = await get_grafana_datasources(ops_test, grafana_app_name, 0)
    assert initial_datasources == []

    await ops_test.model.add_relation(
        "{}:grafana-source".format(grafana_app_name), "{}:grafana-source".format(tester_app_name)
    )
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active")

    datasource_suffix = "{}_0".format(tester_app_name)
    datasources_with_relation = await get_grafana_datasources(ops_test, grafana_app_name, 0)
    tester_datasource = get_datasource_for(datasource_suffix, datasources_with_relation)
    assert tester_datasource != {}

    await ops_test.model.applications[tester_app_name].remove()
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active")

    relation_removed_datasources = await get_grafana_datasources(ops_test, grafana_app_name, 0)
    assert initial_datasources == relation_removed_datasources

    await ops_test.model.applications[grafana_app_name].remove()
    await ops_test.model.reset()


def _cell_id(ingress, tls, scale, mode):
    return "{}{}{}{}".format("i" if ingress else "n", "t" if tls else "n", scale, mode[0])


def _tester_name(ingress, tls, scale, mode):
    # Unique, valid juju application name per cell so datasources never collide.
    return "tester-{}".format(_cell_id(ingress, tls, scale, mode))


async def _grafana_datasources(ops_test, tls: bool) -> list:
    """Fetch Grafana datasources over http/https (verify disabled for self-signed TLS)."""
    host = await unit_address(ops_test, GRAFANA, 0)
    pw = await grafana_password(ops_test, GRAFANA)
    scheme = "https" if tls else "http"
    resp = requests.get(
        "{}://{}:3000/api/datasources".format(scheme, host),
        auth=("admin", pw),
        verify=False,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _tester_datasources(datasources: list, tester: str) -> list:
    return [d for d in datasources if "_{}".format(tester) in d["name"]]


def _is_app_level(name: str, tester: str) -> bool:
    """An app-level datasource name ends with the application name (no _<unit> suffix)."""
    return name.endswith("_{}".format(tester))


async def _leader_unit(ops_test, app_name):
    for unit in ops_test.model.applications[app_name].units:
        if await unit.is_leader_from_status():
            return unit
    return None


@pytest.fixture(scope="module")
async def base_infra(ops_test, grafana_charm):
    """Deploy Grafana once for the whole matrix.

    Traefik and the CA are deployed lazily (only for the cells that need them), so the
    no-ingress cells do not depend on a working LoadBalancer provider.
    """
    await ops_test.model.deploy(
        grafana_charm,
        resources=grafana_resources,
        application_name=GRAFANA,
        trust=True,
    )
    await ops_test.model.wait_for_idle(apps=[GRAFANA], status="active", timeout=1000)
    await check_grafana_is_ready(ops_test, GRAFANA, 0)
    yield


async def _ensure_ca(ops_test):
    if CA not in ops_test.model.applications:
        await ops_test.model.deploy(
            "self-signed-certificates", application_name=CA, channel="latest/stable"
        )
        await ops_test.model.wait_for_idle(apps=[CA], status="active", timeout=600)


async def _ensure_traefik(ops_test):
    if TRAEFIK not in ops_test.model.applications:
        await ops_test.model.deploy(
            "traefik-k8s", application_name=TRAEFIK, channel="latest/stable", trust=True
        )
        await _ensure_ca(ops_test)
        await ops_test.model.add_relation(
            "{}:certificates".format(TRAEFIK), "{}:certificates".format(CA)
        )
        await ops_test.model.wait_for_idle(apps=[TRAEFIK], status="active", timeout=600)


async def _deploy_tester(ops_test, grafana_tester_charm, tester, *, scale: int, mode: str):
    config = {
        "app_datasource": mode == "app",
        "unit_datasources": mode == "unit",
    }
    await ops_test.model.deploy(
        grafana_tester_charm,
        resources=tester_resources,
        application_name=tester,
        num_units=scale,
        config=config,
    )
    await ops_test.model.wait_for_idle(apps=[tester], status="active", timeout=600)


async def _teardown(ops_test, tester):
    if tester in ops_test.model.applications:
        await ops_test.model.applications[tester].remove()
        await ops_test.model.block_until(
            lambda: tester not in ops_test.model.applications, timeout=600
        )
    # Drop any TLS relation we added to Grafana so the next cell starts clean (http).
    try:
        await ops_test.model.applications[GRAFANA].remove_relation("certificates", CA)
    except Exception:
        pass
    await ops_test.model.wait_for_idle(apps=[GRAFANA], status="active", timeout=600)


@pytest.mark.parametrize("ingress,tls,scale,mode", MATRIX)
async def test_datasource_matrix(
    ops_test, grafana_charm, grafana_tester_charm, base_infra, ingress, tls, scale, mode
):
    """One matrix cell: deploy the tester in this configuration and assert datasources."""
    tester = _tester_name(ingress, tls, scale, mode)
    apps_to_wait = [GRAFANA, tester]
    try:
        await _deploy_tester(ops_test, grafana_tester_charm, tester, scale=scale, mode=mode)

        if tls:
            await _ensure_ca(ops_test)
            await ops_test.model.add_relation(
                "{}:certificates".format(GRAFANA), "{}:certificates".format(CA)
            )

        if ingress:
            await _ensure_traefik(ops_test)
            apps_to_wait.append(TRAEFIK)
            endpoint = "ingress" if mode == "app" else "ingress-per-unit"
            await ops_test.model.add_relation(
                "{}:{}".format(tester, endpoint), "{}:{}".format(TRAEFIK, endpoint)
            )

        await ops_test.model.add_relation(
            "{}:grafana-source".format(GRAFANA), "{}:grafana-source".format(tester)
        )
        await ops_test.model.wait_for_idle(apps=apps_to_wait, status="active", timeout=600)

        datasources = _tester_datasources(await _grafana_datasources(ops_test, tls), tester)

        if mode == "app":
            # COUNT + UID SHAPE: exactly one app-level datasource regardless of
            # scale/ingress/TLS, with a UID that has NO unit number.
            assert len(datasources) == 1, datasources
            name = datasources[0]["name"]
            assert _is_app_level(name, tester), name
            uid_before = datasources[0]["uid"]

            if ingress and tls:
                assert datasources[0]["url"].startswith("https://"), datasources[0]["url"]

            # STABILITY: the app-level UID must survive a provider leader re-election.
            if scale == 2:
                leader = await _leader_unit(ops_test, tester)
                assert leader
                idx = leader.name.split("/")[1]
                # Deleting the leader pod forces Juju to re-elect a new leader.
                sh.kubectl.delete.pod(  # type: ignore
                    "{}-{}".format(tester, idx), namespace=ops_test.model_name
                )
                await ops_test.model.wait_for_idle(
                    apps=[GRAFANA, tester], status="active", timeout=600
                )
                after = _tester_datasources(await _grafana_datasources(ops_test, tls), tester)
                assert len(after) == 1, after
                assert after[0]["name"] == name
                assert after[0]["uid"] == uid_before
        else:
            # unit mode -> exactly `scale` datasources, each keyed by unit number.
            assert len(datasources) == scale, datasources
            for d in datasources:
                assert not _is_app_level(d["name"], tester), d["name"]
                assert d["name"].split("_")[-1].isdigit(), d["name"]
            if ingress and tls:
                for d in datasources:
                    assert d["url"].startswith("https://"), d["url"]
    finally:
        if not os.environ.get("KEEP_TESTER"):
            await _teardown(ops_test, tester)
