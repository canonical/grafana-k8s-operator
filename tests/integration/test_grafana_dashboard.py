#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import logging

import pytest
from helpers import (
    check_grafana_is_ready,
    get_dashboard_by_search,
    get_grafana_dashboards,
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

    await ops_test.model.deploy(
        grafana_charm, resources=grafana_resources, application_name=grafana_app_name
    )
    await ops_test.model.deploy(
        grafana_tester_charm, resources=tester_resources, application_name=tester_app_name
    )
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active")
    await ops_test.model.wait_for_idle(apps=[tester_app_name], status="active")
    await ops_test.model.block_until(
        lambda: len(ops_test.model.applications[grafana_app_name].units) > 0
    )
    await ops_test.model.block_until(
        lambda: len(ops_test.model.applications[tester_app_name].units) > 0
    )

    assert ops_test.model.applications[grafana_app_name].units[0].workload_status == "active"
    assert ops_test.model.applications[tester_app_name].units[0].workload_status == "active"

    await check_grafana_is_ready(ops_test, grafana_app_name, 0)
    initial_dashboards = await get_grafana_dashboards(ops_test, grafana_app_name, 0)
    assert initial_dashboards == []

    await ops_test.model.add_relation(
        "{}:grafana-dashboard".format(grafana_app_name),
        "{}:grafana-dashboard".format(tester_app_name),
    )
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active")

    tester_dashboard = await get_dashboard_by_search(
        ops_test, grafana_app_name, 0, "Grafana Tester"
    )
    assert tester_dashboard != {}

    await ops_test.model.applications[tester_app_name].remove()
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active")

    relation_removed_dashboards = await get_grafana_dashboards(ops_test, grafana_app_name, 0)
    assert initial_dashboards == relation_removed_dashboards

    await ops_test.model.applications[grafana_app_name].remove()
    await ops_test.model.reset()
