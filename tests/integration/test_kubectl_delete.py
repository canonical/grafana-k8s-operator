#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.


import logging

import pytest
from helpers import check_grafana_is_ready, get_config_values, oci_image

logger = logging.getLogger(__name__)

app_name = "grafana"
config = {"log_level": "error", "admin_user": "jimmy"}
grafana_resources = {
    "grafana-image": oci_image("./metadata.yaml", "grafana-image"),
    "litestream-image": oci_image("./metadata.yaml", "litestream-image"),
}


@pytest.mark.abort_on_fail
async def test_deploy_from_local_path(ops_test, grafana_charm):
    """Deploy the charm-under-test."""
    logger.debug("deploy local charm")

    await ops_test.model.deploy(
        grafana_charm, application_name=app_name, resources=grafana_resources
    )

    # set some custom configs to later check they persisted across the test
    await ops_test.model.applications[app_name].set_config(config)
    await ops_test.model.wait_for_idle(apps=[app_name], status="active", timeout=1000)


async def test_config_values_are_retained_after_pod_deleted_and_restarted(ops_test):
    pod_name = f"{app_name}-0"

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
        apps=[app_name], status="active", wait_for_units=1, timeout=1000
    )

    await check_grafana_is_ready(ops_test, app_name, 0)
    assert (await get_config_values(ops_test, app_name)).items() >= config.items()
