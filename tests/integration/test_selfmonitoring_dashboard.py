#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging
import sh
import pytest
from helpers import (
    ModelConfigChange,
    check_grafana_is_ready,
    get_dashboard_by_search,
    get_grafana_dashboards,
    oci_image,
)

# pyright: reportAttributeAccessIssue=false

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
grafana_app_name = "grafana"
prometheus_app_name = "prometheus"


@pytest.mark.abort_on_fail
async def test_deploy(ops_test, grafana_charm):
    sh.juju.deploy(
        grafana_charm,
        grafana_app_name,
        model=ops_test.model.name,
        trust=True,
        resource=[f"{k}={v}" for k, v in grafana_resources.items()],
    )
    sh.juju.deploy(
        "prometheus-k8s",
        prometheus_app_name,
        channel="edge",
        trust=True,
        model=ops_test.model.name,
    )
    await ops_test.model.wait_for_idle(
        apps=[grafana_app_name, prometheus_app_name],
        status="active",
        timeout=300,
    )

    await check_grafana_is_ready(ops_test, grafana_app_name, 0)
    initial_dashboards = await get_grafana_dashboards(ops_test, grafana_app_name, 0)
    assert initial_dashboards == []


@pytest.mark.xfail
async def test_grafana_self_monitoring_dashboard_is_present(ops_test):
    """Relate and ensure the dashboard is present."""
    await asyncio.gather(
        ops_test.model.add_relation(
            "{}:metrics-endpoint".format(grafana_app_name),
            "{}".format(prometheus_app_name),
        ),
        ops_test.model.add_relation(
            "{}:grafana-source".format(prometheus_app_name),
            "{}".format(grafana_app_name),
        ),
    )
    await ops_test.model.wait_for_idle(
        apps=[grafana_app_name, prometheus_app_name], status="active", idle_period=60
    )

    self_dashboard = await get_dashboard_by_search(ops_test, grafana_app_name, 0, "Grafana")
    assert self_dashboard != {}


@pytest.mark.xfail
async def test_remove(ops_test):
    logger.info("Removing %s", prometheus_app_name)
    await ops_test.model.applications[prometheus_app_name].remove()

    # Workaround to make sure everything is up-to-date: update-status
    async with ModelConfigChange(ops_test, {"update-status-hook-interval": "10s"}):
        await asyncio.sleep(11)

    await ops_test.model.wait_for_idle(
        apps=[grafana_app_name], status="active", timeout=300, idle_period=60
    )

    relation_removed_dashboards = await get_grafana_dashboards(ops_test, grafana_app_name, 0)
    assert relation_removed_dashboards == []
