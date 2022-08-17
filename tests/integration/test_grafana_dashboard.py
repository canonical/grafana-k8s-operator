#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
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
grafana_resources = {
    "grafana-image": oci_image("./metadata.yaml", "grafana-image"),
    "litestream-image": oci_image("./metadata.yaml", "litestream-image"),
}
grafana_app_name = "grafana"
tester_app_name = "grafana-tester"


@pytest.mark.abort_on_fail
async def test_deploy(ops_test, grafana_charm, grafana_tester_charm):
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
        apps=[grafana_app_name, tester_app_name], status="active", wait_for_units=1, timeout=300
    )

    await check_grafana_is_ready(ops_test, grafana_app_name, 0)
    initial_dashboards = await get_grafana_dashboards(ops_test, grafana_app_name, 0)
    assert initial_dashboards == []


@pytest.mark.abort_on_fail
async def test_grafana_dashboard_relation_data_with_grafana_tester(ops_test):
    """Test basic functionality of grafana-dashboard relation interface."""
    await ops_test.model.add_relation(
        "{}:grafana-dashboard".format(grafana_app_name),
        "{}:grafana-dashboard".format(tester_app_name),
    )
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active")

    tester_dashboard = await get_dashboard_by_search(
        ops_test, grafana_app_name, 0, "Grafana Tester"
    )
    assert tester_dashboard != {}


@pytest.mark.abort_on_fail
async def test_remove(ops_test):
    logger.info("Removing %s", tester_app_name)
    await ops_test.model.applications[tester_app_name].remove()
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active", timeout=300)

    relation_removed_dashboards = await get_grafana_dashboards(ops_test, grafana_app_name, 0)
    assert relation_removed_dashboards == []
