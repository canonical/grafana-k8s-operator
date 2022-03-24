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
grafana_resources = {"grafana-image": oci_image("./metadata.yaml", "grafana-image")}


@pytest.mark.abort_on_fail
async def test_password_returns_correct_value_after_scaling(ops_test, grafana_charm):
    """Deploy from charmhub and then upgrade with the charm-under-test."""
    logger.info("deploying local charm")
    await ops_test.model.deploy(
        grafana_charm, resources=grafana_resources, application_name=app_name
    )

    # set some custom configs to later check they persisted across the test

    action = await ops_test.model.applications[app_name].units[0].run_action("get-admin-password")
    pw = (await action.wait()).results["admin-password"]

    logger.info("scaling local charm %s to 0 units", grafana_charm)
    await ops_test.model.applications[app_name].scale(scale=0)
    await ops_test.model.block_until(lambda: len(ops_test.model.applications[app_name].units) == 0)

    logger.info("scaling local charm %s to 1 units", grafana_charm)
    await ops_test.model.applications[app_name].scale(scale=1)
    await ops_test.model.block_until(lambda: len(ops_test.model.applications[app_name].units) > 0)
    action = await ops_test.model.applications[app_name].units[0].run_action("get-admin-password")
    msg = (await action.wait()).results["admin-password"]
    assert pw != msg
    assert msg == "Admin password has been changed by an administrator"
