#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from helpers import (
    check_grafana_is_ready,
    get_config_values,
    get_dashboard_by_search,
    get_datasource_for,
    get_grafana_datasources,
    oci_image,
)

logger = logging.getLogger(__name__)

grafana_app_name = "grafana"
tester_app_name = "grafana-tester"
config = {"log_level": "error", "datasource_query_timeout": "600"}
grafana_resources = {
    "grafana-image": oci_image("./metadata.yaml", "grafana-image"),
    "litestream-image": oci_image("./metadata.yaml", "litestream-image"),
}
tester_resources = {
    "grafana-tester-image": oci_image(
        "./tests/integration/grafana-tester/metadata.yaml", "grafana-tester-image"
    )
}


@pytest.mark.abort_on_fail
async def test_deploy_from_local_path(ops_test, grafana_charm, grafana_tester_charm):
    """Deploy the charm-under-test."""
    logger.debug("deploy local charm")

    await asyncio.gather(
        ops_test.model.deploy(
            grafana_charm,
            resources=grafana_resources,
            application_name=grafana_app_name,
            trust=True,
        ),
        ops_test.model.deploy(
            grafana_tester_charm,
            application_name=tester_app_name,
            resources=tester_resources,
        ),
    )

    # set some custom configs to later check they persisted across the test
    await ops_test.model.applications[grafana_app_name].set_config(config)
    await ops_test.model.wait_for_idle(
        apps=[grafana_app_name, tester_app_name], status="active", timeout=1000
    )


async def test_create_and_check_datasource_and_dashboard_before_delete(ops_test):
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
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active", idle_period=30)
    await check_grafana_is_ready(ops_test, grafana_app_name, 0)

    tester_dashboard = await get_dashboard_by_search(
        ops_test, grafana_app_name, 0, "Grafana Tester"
    )
    assert tester_dashboard != {}

    datasource_suffix = "{}_0".format(tester_app_name)
    datasources_with_relation = await get_grafana_datasources(ops_test, grafana_app_name, 0)
    tester_datasource = get_datasource_for(datasource_suffix, datasources_with_relation)
    assert tester_datasource != {}


async def test_config_values_are_retained_after_pod_deleted_and_restarted(ops_test):
    pod_name = f"{grafana_app_name}-0"

    cmd = [
        "sg",
        "microk8s",
        "-c",
        " ".join(["microk8s.kubectl", "delete", "pod", "-n", ops_test.model_name, pod_name]),
    ]

    logger.debug(
        "Removing pod '%s' from model '%s' with cmd: %s", pod_name, ops_test.model_name, cmd
    )

    retcode, stdout, stderr = await ops_test.run(*cmd)
    assert retcode == 0, f"kubectl failed: {(stderr or stdout).strip()}"
    logger.debug(stdout)

    await ops_test.model.wait_for_idle(
        apps=[grafana_app_name], status="active", wait_for_units=1, timeout=1000
    )

    await check_grafana_is_ready(ops_test, grafana_app_name, 0)
    assert (await get_config_values(ops_test, grafana_app_name)).items() >= config.items()


async def test_dashboards_and_datasources_are_retained_after_pod_deleted_and_restarted(ops_test):
    await check_grafana_is_ready(ops_test, grafana_app_name, 0)
    tester_dashboard = await get_dashboard_by_search(
        ops_test, grafana_app_name, 0, "Grafana Tester"
    )
    assert tester_dashboard != {}

    datasource_suffix = "{}_0".format(tester_app_name)
    datasources_with_relation = await get_grafana_datasources(ops_test, grafana_app_name, 0)
    tester_datasource = get_datasource_for(datasource_suffix, datasources_with_relation)
    assert tester_datasource != {}
