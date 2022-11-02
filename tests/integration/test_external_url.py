#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import aiohttp
import pytest
from helpers import ModelConfigChange, grafana_password, oci_image, reenable_metallb
from pytest_operator.plugin import OpsTest
from workload import Grafana

logger = logging.getLogger(__name__)

grafana_resources = {
    "grafana-image": oci_image("./metadata.yaml", "grafana-image"),
    "litestream-image": oci_image("./metadata.yaml", "litestream-image"),
}
grafana_app_name = "grafana"

idle_period = 90


@pytest.mark.abort_on_fail
async def test_deploy(ops_test, grafana_charm):
    await asyncio.gather(
        ops_test.model.deploy(
            grafana_charm,
            resources=grafana_resources,
            application_name=grafana_app_name,
            num_units=2,
            trust=True,
        ),
        ops_test.model.deploy(
            "ch:traefik-k8s",
            application_name="traefik",
            channel="edge",
        ),
    )

    await asyncio.gather(
        ops_test.model.wait_for_idle(
            apps=[grafana_app_name],
            wait_for_units=2,
            timeout=600,
        ),
        ops_test.model.wait_for_idle(
            apps=["traefik"],
            wait_for_units=1,
            timeout=600,
        ),
    )


async def test_grafana_is_reachable_via_traefik(ops_test: OpsTest):
    # GIVEN metallb is ready
    ip = await reenable_metallb()

    # WHEN grafana is related to traefik
    await ops_test.model.add_relation(f"{grafana_app_name}:ingress", "traefik")

    # Workaround to make sure everything is up-to-date: update-status
    async with ModelConfigChange(ops_test, {"update-status-hook-interval": "10s"}):
        await asyncio.sleep(11)

    logger.info("At this point, after re-enabling metallb, traefik should become active")
    await ops_test.model.wait_for_idle(
        apps=[grafana_app_name, "traefik"],
        status="active",
        timeout=600,
        idle_period=idle_period,
    )

    # THEN the grafana API is served on metallb's IP
    pw = await grafana_password(ops_test, grafana_app_name)
    grafana = Grafana(host=ip, path=f"{ops_test.model_name}-{grafana_app_name}", port=80, pw=pw)

    # Temporary workaround
    for _ in range(3):
        try:
            # is_ready raises when ingress is not yet ready and the response is not json (plain string 404 error)
            await grafana.is_ready()
            break
        except aiohttp.client_exceptions.ContentTypeError:
            await asyncio.sleep(30)

    is_ready = await grafana.is_ready()
    assert is_ready
