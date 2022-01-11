#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from helpers import check_grafana_is_ready, oci_image

grafana_resources = {"grafana-image": oci_image("./metadata.yaml", "grafana-image")}


@pytest.mark.abort_on_fail
async def test_build_and_deploy_with_alternative_images(ops_test, grafana_charm):
    """Test that the Prometheus charm can be deployed successfully."""
    app_name = "prometheus-ubuntu"

    await ops_test.model.deploy(
        grafana_charm, resources=grafana_resources, application_name=app_name
    )
    await ops_test.model.wait_for_idle(apps=[app_name], status="active")
    await ops_test.model.block_until(lambda: len(ops_test.model.applications[app_name].units) > 0)

    assert ops_test.model.applications[app_name].units[0].workload_status == "active"

    await check_grafana_is_ready(ops_test, app_name, 0)

    await ops_test.model.applications[app_name].remove()
    await ops_test.model.block_until(lambda: app_name not in ops_test.model.applications)
    await ops_test.model.reset()
