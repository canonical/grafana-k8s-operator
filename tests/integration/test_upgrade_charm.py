#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.


import logging

import pytest
from helpers import check_grafana_is_ready, get_config_values, oci_image

logger = logging.getLogger(__name__)

app_name = "grafana-k8s"
grafana_resources = {
    "grafana-image": oci_image("./metadata.yaml", "grafana-image"),
    "litestream-image": oci_image("./metadata.yaml", "litestream-image"),
}


@pytest.mark.abort_on_fail
async def test_config_values_are_retained_after_pod_upgraded(ops_test, grafana_charm):
    """Deploy from charmhub and then upgrade with the charm-under-test."""
    logger.info("deploy charm from charmhub")
    await ops_test.model.deploy(
        f"ch:{app_name}", application_name=app_name, channel="edge", trust=True
    )

    # set some custom configs to later check they persisted across the test
    config = {"log_level": "error", "admin_user": "jimmy"}
    await ops_test.model.applications[app_name].set_config(config)
    await ops_test.model.wait_for_idle(apps=[app_name], status="active", timeout=1000)

    logger.info("upgrade deployed charm with local charm %s", grafana_charm)
    await ops_test.model.applications[app_name].refresh(
        path=grafana_charm, resources=grafana_resources
    )
    await ops_test.model.wait_for_idle(apps=[app_name], status="active", timeout=1000)
    await check_grafana_is_ready(ops_test, app_name, 0)
    assert (await get_config_values(ops_test, app_name)).items() >= config.items()
