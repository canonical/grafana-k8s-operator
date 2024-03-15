#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from helpers import (
    check_grafana_is_ready,
    get_datasource_for,
    get_grafana_datasources,
    oci_image,
)

logger = logging.getLogger(__name__)

tester_resources = {
    "grafana-tester-image": oci_image(
        "./tests/integration/grafana-tester/metadata.yaml", "grafana-tester-image"
    )
}
grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
    "litestream-image": oci_image("./charmcraft.yaml", "litestream-image"),
}


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
