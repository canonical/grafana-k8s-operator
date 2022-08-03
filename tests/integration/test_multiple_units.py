#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import itertools
import logging

import pytest
from helpers import (
    check_grafana_is_ready,
    get_dashboard_by_search,
    get_datasource_for,
    get_grafana_dashboards,
    get_grafana_datasources,
    oci_image,
)

logger = logging.getLogger(__name__)

tester_resources = {
    "grafana-tester-image": oci_image(
        "./tests/integration/grafana-tester/metadata.yaml", "grafana-tester-image"
    )
}
grafana_resources = {"grafana-image": oci_image("./metadata.yaml", "grafana-image")}


@pytest.mark.abort_on_fail
async def test_grafana_dashboard_relation_data_with_grafana_tester(
    ops_test, grafana_charm, grafana_tester_charm
):
    """Test basic functionality of grafana-dashboard relation interface."""
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
    await asyncio.gather(
        ops_test.model.wait_for_idle(apps=[grafana_app_name, tester_app_name], status="active"),
    )
    logging.info("scaling up to 2 units")
    await ops_test.model.applications[grafana_app_name].scale(scale=2)
    await asyncio.gather(
        ops_test.model.wait_for_idle(
            apps=[grafana_app_name], status="active", wait_for_exact_units=2, timeout=300
        ),
        ops_test.model.wait_for_idle(
            apps=[tester_app_name], status="active", wait_for_units=1, timeout=300
        ),
    )

    logging.info("waiting for idle to ensure the second unit has an address")
    await ops_test.model.wait_for_idle(
        apps=[grafana_app_name], status="active", wait_for_units=2, timeout=300
    )

    assert ops_test.model.applications[grafana_app_name].units[0].workload_status == "active"
    assert ops_test.model.applications[grafana_app_name].units[1].workload_status == "active"
    assert ops_test.model.applications[tester_app_name].units[0].workload_status == "active"

    await check_grafana_is_ready(ops_test, grafana_app_name, 0)
    await check_grafana_is_ready(ops_test, grafana_app_name, 1)

    initial_dashboards = await asyncio.gather(
        get_grafana_dashboards(ops_test, grafana_app_name, 0),
        get_grafana_dashboards(ops_test, grafana_app_name, 1),
    )
    initial_datasources = await asyncio.gather(
        get_grafana_datasources(ops_test, grafana_app_name, 0),
        get_grafana_datasources(ops_test, grafana_app_name, 1),
    )

    initial_dashboards = list(itertools.chain.from_iterable(initial_dashboards))
    initial_datasources = list(itertools.chain.from_iterable(initial_datasources))

    assert initial_dashboards == []
    assert initial_datasources == []

    logging.info("adding relations and waiting for units to settle")
    await asyncio.gather(
        ops_test.model.add_relation(
            "{}:grafana-source".format(grafana_app_name),
            "{}:grafana-source".format(tester_app_name),
        ),
        ops_test.model.add_relation(
            "{}:grafana-dashboard".format(grafana_app_name),
            "{}:grafana-dashboard".format(tester_app_name),
        ),
    )
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active")
    tester_dashboards = await asyncio.gather(
        get_dashboard_by_search(ops_test, grafana_app_name, 0, "Grafana Tester"),
        get_dashboard_by_search(ops_test, grafana_app_name, 1, "Grafana Tester"),
    )
    assert tester_dashboards[0] != {}

    # Dashboard provisioning randomizes the UID, as well as datetime fields
    # based on processing time
    update_dynamic_fields = {
        "uid": "deadbeef",
        "meta": {
            "created": "irrelevant",
            "updated": "irrelevant",
            "url": "/d/deadbeef/grafana/tester",
        },
    }
    tester_dashboards = [d.update(update_dynamic_fields) for d in tester_dashboards]
    assert tester_dashboards[0] == tester_dashboards[1]

    datasource_suffix = "{}_0".format(tester_app_name)
    datasources_with_relation = await asyncio.gather(
        get_grafana_datasources(ops_test, grafana_app_name, 0),
        get_grafana_datasources(ops_test, grafana_app_name, 1),
    )
    tester_datasources = [
        get_datasource_for(datasource_suffix, datasources_with_relation[0]),
        get_datasource_for(datasource_suffix, datasources_with_relation[1]),
    ]
    tester_datasources = [d.update({"uid": "deadbeef"}) for d in tester_datasources]
    assert tester_datasources[0] != {}
    assert tester_datasources[0] == tester_datasources[1]

    logging.info("removing tester and waiting for units to settle")
    await ops_test.model.applications[tester_app_name].remove()
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active")

    relation_removed_dashboards = await asyncio.gather(
        get_grafana_dashboards(ops_test, grafana_app_name, 0),
        get_grafana_dashboards(ops_test, grafana_app_name, 1),
    )
    relation_removed_datasources = await asyncio.gather(
        get_grafana_datasources(ops_test, grafana_app_name, 0),
        get_grafana_datasources(ops_test, grafana_app_name, 1),
    )
    relation_removed_dashboards = list(itertools.chain.from_iterable(relation_removed_dashboards))
    relation_removed_datasources = list(
        itertools.chain.from_iterable(relation_removed_datasources)
    )
    assert initial_dashboards == relation_removed_dashboards
    assert initial_datasources == relation_removed_datasources

    await ops_test.model.applications[grafana_app_name].remove()
    await ops_test.model.reset()
