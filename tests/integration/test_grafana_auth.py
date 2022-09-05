#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests the library using dummy requirer and provider charms.

It tests that the charms are able to relate and to exchange data.
"""

import asyncio
import logging

import pytest
from helpers import check_grafana_is_ready, oci_image

logger = logging.getLogger(__name__)

tester_resources = {
    "grafana-tester-image": oci_image(
        "./tests/integration/grafana-tester/metadata.yaml", "grafana-tester-image"
    )
}
grafana_resources = {"grafana-image": oci_image("./metadata.yaml", "grafana-image")}


@pytest.mark.abort_on_fail
async def test_deploy_and_relate_auth_provider_and_requirer(
    ops_test, grafana_charm, grafana_tester_charm
):
    grafana_app_name = "grafana"
    tester_app_name = "grafana-tester"

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
    await ops_test.model.add_relation(
        "{}:grafana-auth".format(grafana_app_name), "{}:grafana-auth".format(tester_app_name)
    )
    await ops_test.model.wait_for_idle(apps=[grafana_app_name], status="active")
