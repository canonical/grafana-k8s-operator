#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.


import logging
import sh
import pytest
from helpers import check_grafana_is_ready, get_config_values, oci_image

# pyright: reportAttributeAccessIssue = false

logger = logging.getLogger(__name__)

app_name = "grafana-k8s"
grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
    "litestream-image": oci_image("./charmcraft.yaml", "litestream-image"),
}


@pytest.mark.abort_on_fail
async def test_config_values_are_retained_after_pod_upgraded(ops_test, grafana_charm):
    """Deploy from charmhub and then upgrade with the charm-under-test."""
    logger.info("deploy charm from charmhub")
    sh.juju.deploy(app_name, model=ops_test.model.name, channel="2/edge", trust=True)

    # set some custom configs to later check they persisted across the test
    config = {"log_level": "error", "admin_user": "jimmy"}
    await ops_test.model.applications[app_name].set_config(config)
    await ops_test.model.wait_for_idle(apps=[app_name], status="active", timeout=1000)

    logger.info("upgrade deployed charm with local charm %s", grafana_charm)
    sh.juju.refresh(
        app_name,
        model=ops_test.model.name,
        path=grafana_charm,
        resource=[f"{k}={v}" for k, v in grafana_resources.items()],
    )
    await ops_test.model.wait_for_idle(apps=[app_name], status="active", timeout=1000)
    await check_grafana_is_ready(ops_test, app_name, 0)
    assert (await get_config_values(ops_test, app_name)).items() >= config.items()
