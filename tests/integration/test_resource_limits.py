#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.


import json
import logging
import subprocess

import pytest
from helpers import oci_image

logger = logging.getLogger(__name__)

app_name = "grafana"
grafana_resources = {
    "grafana-image": oci_image("./metadata.yaml", "grafana-image"),
    "litestream-image": oci_image("./metadata.yaml", "litestream-image"),
}


@pytest.mark.abort_on_fail
async def test_resource_limits_apply(ops_test, grafana_charm):
    """Set resource limits and make sure they are applied."""
    logger.info("deploying local charm")
    await ops_test.model.deploy(
        grafana_charm,
        resources=grafana_resources,
        application_name=app_name,
        trust=True,
        config={"cpu": "300m", "memory": "300M"},
    )
    await ops_test.model.wait_for_idle(
        apps=[app_name],
        status="active",
        timeout=300,
        wait_for_exact_units=1,
        idle_period=10,
        raise_on_error=False,
    )
    await ops_test.model.wait_for_idle(
        apps=[app_name],
        status="active",
        wait_for_exact_units=1,
        idle_period=10,
        raise_on_error=True,
    )
    pod = json.loads(
        subprocess.check_output(
            [
                "kubectl",
                "--namespace",
                ops_test.model_name,
                "get",
                "pod",
                "-o",
                "json",
                f"{app_name}-0",
            ],
            text=True,
        )
    )
    container = list(filter(lambda x: x["name"] == "grafana", pod["spec"]["containers"]))
    assert container[0]["resources"]["limits"]["cpu"] == "300m"
    assert container[0]["resources"]["limits"]["memory"] == "300M"
