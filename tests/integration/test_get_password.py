#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
from pathlib import Path

import pytest
import yaml
from helpers import oci_image

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
app_name = "grafana"
grafana_resources = {
    "grafana-image": oci_image("./metadata.yaml", "grafana-image"),
    "litestream-image": oci_image("./metadata.yaml", "litestream-image"),
}


async def test_setup_env(ops_test):
    await ops_test.model.set_config({"logging-config": "<root>=WARNING; unit=DEBUG"})


@pytest.mark.abort_on_fail
async def test_password_returns_correct_value_after_upgrading(ops_test, grafana_charm):
    """Deploy from charmhub and then upgrade with the charm-under-test."""
    logger.info("deploying local charm")
    await ops_test.model.deploy(
        grafana_charm, resources=grafana_resources, application_name=app_name
    )
    await ops_test.model.wait_for_idle(
        apps=[app_name], status="active", timeout=300, wait_for_exact_units=1
    )

    # set some custom configs to later check they persisted across the test
    action = await ops_test.model.applications[app_name].units[0].run_action("get-admin-password")
    pw = (await action.wait()).results["admin-password"]

    logger.info("Upgrading charm")
    await ops_test.model.applications[app_name].refresh(
        path=grafana_charm, resources=grafana_resources
    )
    await ops_test.model.wait_for_idle(
        apps=[app_name], status="active", timeout=300, wait_for_exact_units=1, idle_period=30
    )

    # libjuju doesn't actually allow waiting for idle with zero units with any argument combintation
    # block_until() to do it ourselves. The scale also blows it away so fast that the health check
    # fails, and the unit never finalizes.
    # FIXME: stop destroying when https://bugs.launchpad.net/juju/+bug/1951415 is resolved

    # await ops_test.model.block_until(lambda: len(ops_test.model.applications[app_name].units) == 0, timeout=300)
    # logger.info("scaling local charm %s to 1 units", grafana_charm)
    # await ops_test.model.applications[app_name].scale(scale=1)

    # await ops_test.model.wait_for_idle(
    #     apps=[app_name], status="active", timeout=300, wait_for_exact_units=1, idle_period=30
    # )

    action = await ops_test.model.applications[app_name].units[0].run_action("get-admin-password")
    msg = (await action.wait()).results["admin-password"]
    assert pw == msg
