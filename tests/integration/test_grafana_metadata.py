#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging


from helpers import (
    check_grafana_is_ready,
    oci_image,
)

logger = logging.getLogger(__name__)

grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
    "litestream-image": oci_image("./charmcraft.yaml", "litestream-image"),
}


APP_NAME = "grafana"
TESTER_APP_NAME = "metadata-requirer"

async def test_deploy_grafana(
    ops_test, grafana_charm
):
    """Test basic functionality of grafana-source relation interface."""
    grafana_app_name = "grafana"

    await ops_test.model.deploy(
            grafana_charm,
            resources=grafana_resources,
            application_name=grafana_app_name,
            trust=True,
    )
    await ops_test.model.wait_for_idle(
        status="active",
        wait_for_at_least_units=1,
        timeout=300,
    )

    await check_grafana_is_ready(ops_test, grafana_app_name, 0)


async def test_grafana_metadata_relation(ops_test, grafana_metadata_requirer_tester_charm):
    """Test the metadata relation works as expected in attachment."""
    tester_charm = grafana_metadata_requirer_tester_charm

    await ops_test.model.deploy(
        tester_charm, application_name=TESTER_APP_NAME
    )

    tester_application = ops_test.model.applications[TESTER_APP_NAME]
    await ops_test.model.add_relation(APP_NAME, TESTER_APP_NAME)

    # Wait for the relation to be established
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME], status="active", raise_on_blocked=True, timeout=60
    )

    actual = await get_tester_data(tester_application)
    assert actual.get("grafana_uid", None)
    assert actual.get("ingress_url", None)
    assert actual.get("internal_url", None)


async def test_grafana_metadata_relation_removal(ops_test, grafana_metadata_requirer_tester_charm):
    """Test the metadata relation works as expected in removal."""
    # Remove the relation and confirm the data is gone
    await ops_test.model.applications[APP_NAME].remove_relation(
        f"{APP_NAME}:grafana-metadata", TESTER_APP_NAME
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME], status="active", raise_on_blocked=True, timeout=60
    )

    tester_application = ops_test.model.applications[TESTER_APP_NAME]
    actual = await get_tester_data(tester_application)
    assert actual == {}


async def get_tester_data(tester_application):
    # Check the relation data
    action = await tester_application.units[0].run_action(
        "get-metadata",
    )
    action_result = await action.wait()
    assert action_result.status == "completed"
    return json.loads(action_result.results["relation-data"])
