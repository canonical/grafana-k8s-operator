#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test to verify that dashboard relation doesn't cause continuous databag updates.

This test reproduces the issue documented in:
https://github.com/canonical/opentelemetry-collector-operator/issues/331

The problem: The grafana_dashboard library generates a new UUID every time
_upset_dashboards_on_relation() is called, which happens on every config-changed
event. This causes continuous databag updates even when dashboard content hasn't
changed, leading to unnecessary relation-changed events on the consumer side.
"""

import json
import logging
import time

import jubilant
import pytest
from helpers import oci_image
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

GRAFANA_APP = "grafana"
OTELCOL_APP = "otelcol"
RESOURCES = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
}


def get_databag_uuid(juju: jubilant.Juju, consumer_unit: str) -> str:
    """Get the current UUID from the dashboard relation databag.

    The dashboard data is written by the provider (otelcol) to the relation.
    We query it from the consumer side (Grafana) where we can see the provider's
    application-data.

    Args:
        juju: Jubilant Juju instance
        consumer_unit: Consumer unit name (e.g., "grafana/0")

    Returns:
        The UUID string from the databag, or empty string if not found
    """
    output = juju.cli("show-unit", consumer_unit, "--format", "json")
    unit_info = json.loads(output)
    unit_data = unit_info.get(consumer_unit, {})

    # Find the grafana-dashboard relation data from the consumer side
    for rel_info in unit_data.get("relation-info", []):
        endpoint = rel_info.get("endpoint", "")
        if endpoint == "grafana-dashboard":
            # The application-data here is from the provider (otelcol)
            app_data = rel_info.get("application-data", {})
            dashboards_str = app_data.get("dashboards", "{}")
            try:
                dashboards = json.loads(dashboards_str)
                return dashboards.get("uuid", "")
            except json.JSONDecodeError:
                pass

    return ""


def count_relation_changed_events(juju: jubilant.Juju, app: str, relation: str) -> int:
    """Count relation-changed events for an app in the debug log.

    Args:
        juju: Jubilant Juju instance
        app: Application name to filter logs for
        relation: Relation name to look for

    Returns:
        Number of relation-changed events found
    """
    log = juju.debug_log(limit=5000)
    count = 0
    search_term = f"{relation}-relation-changed"
    for line in log.splitlines():
        if app in line and search_term in line:
            count += 1
    return count


def get_status_log_executing_count(juju: jubilant.Juju, unit: str) -> int:
    """Count 'executing' status entries for a unit.

    Uses `juju show-status-log` to retrieve status history.

    Args:
        juju: Jubilant Juju instance
        unit: The unit name (e.g., "grafana/0")

    Returns:
        Number of 'executing' status entries
    """
    output = juju.cli("show-status-log", unit, "--format", "json", "-n", "100")
    entries = json.loads(output)
    return sum(1 for e in entries if e.get("status") == "executing")


@pytest.mark.abort_on_fail
async def test_deploy_grafana_and_otelcol(ops_test: OpsTest, grafana_charm: str):
    """Deploy Grafana and OpenTelemetry Collector K8s."""
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)

    juju.deploy(
        charm=grafana_charm,
        app=GRAFANA_APP,
        resources=RESOURCES,
        trust=True,
    )
    juju.deploy(
        charm="opentelemetry-collector-k8s",
        app=OTELCOL_APP,
        channel="dev/edge",
        trust=True,
    )
    juju.wait(jubilant.all_active, timeout=600)


@pytest.mark.abort_on_fail
async def test_relate_grafana_dashboard(ops_test: OpsTest):
    """Establish grafana-dashboard relation between Grafana and otelcol."""
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)

    juju.integrate(
        f"{GRAFANA_APP}:grafana-dashboard",
        f"{OTELCOL_APP}:grafana-dashboards-provider",
    )
    juju.wait(jubilant.all_active, timeout=300)

    # Verify dashboards are provisioned by checking Grafana API
    # Give Grafana time to provision dashboards
    time.sleep(10)

    status = juju.status()
    grafana_unit = status.apps[GRAFANA_APP].units[f"{GRAFANA_APP}/0"]
    assert grafana_unit.workload_status.current == "active"
    logger.info("Grafana is active after dashboard relation")


@pytest.mark.abort_on_fail
async def test_no_continuous_databag_updates(ops_test: OpsTest):
    """Verify that the dashboard relation doesn't continuously update the databag.

    This test checks that after the initial relation setup, subsequent events
    (like config changes) don't cause new UUID generation and databag updates
    when dashboard content hasn't changed.

    The test:
    1. Records the current UUID after relation is established
    2. Triggers a config-changed event on the provider
    3. Verifies that the databag UUID hasn't changed (it should be stable)
    """
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)

    # Wait for things to settle after relation setup
    time.sleep(10)

    # Get the initial databag UUID (query from Grafana side to see provider's data)
    initial_uuid = get_databag_uuid(juju, f"{GRAFANA_APP}/0")
    logger.info("Initial dashboard UUID: %s", initial_uuid)
    assert initial_uuid, "Expected to find a UUID in the dashboard databag"

    # Trigger an update-status event on otelcol by running JUJU_DISPATCH_PATH
    # This simulates the regular update-status hook and triggers _reconcile()
    # which calls forward_dashboards() in otelcol
    logger.info("Triggering update-status hook on %s", OTELCOL_APP)
    juju.cli("exec", "--unit", f"{OTELCOL_APP}/0", "--", "JUJU_DISPATCH_PATH=hooks/update-status", "./dispatch")
    juju.wait(jubilant.all_active, timeout=120)

    # Wait for any cascading events to settle
    time.sleep(5)

    # Get the databag UUID after update-status
    uuid_after_update = get_databag_uuid(juju, f"{GRAFANA_APP}/0")
    logger.info("UUID after update-status: %s", uuid_after_update)

    # Trigger another update-status event
    logger.info("Triggering second update-status hook on %s", OTELCOL_APP)
    juju.cli("exec", "--unit", f"{OTELCOL_APP}/0", "--", "JUJU_DISPATCH_PATH=hooks/update-status", "./dispatch")
    juju.wait(jubilant.all_active, timeout=120)

    # Wait again
    time.sleep(5)

    # Get the final databag UUID
    final_uuid = get_databag_uuid(juju, f"{GRAFANA_APP}/0")
    logger.info("Final dashboard UUID: %s", final_uuid)

    # THE KEY ASSERTION: UUID should remain stable after update-status events
    # if the dashboard content hasn't changed
    #
    # Note: This test will FAIL with the current implementation, demonstrating the bug.
    # Once fixed, the UUID should only change when actual dashboard content changes.
    assert initial_uuid == uuid_after_update, (
        f"Dashboard UUID changed from '{initial_uuid}' to '{uuid_after_update}' "
        "after an update-status event. This indicates the grafana_dashboard "
        "library is generating new UUIDs on every event, causing continuous "
        "databag updates and unnecessary relation-changed events on the consumer."
    )
    assert initial_uuid == final_uuid, (
        f"Dashboard UUID changed from '{initial_uuid}' to '{final_uuid}' "
        "after update-status events. The UUID should remain stable when dashboard "
        "content hasn't changed."
    )


@pytest.mark.abort_on_fail
async def test_grafana_status_stable_after_provider_events(ops_test: OpsTest):
    """Verify Grafana's status log doesn't show excessive activity from relation events.

    After the initial dashboard provisioning, triggering events on the provider
    (otelcol) should not cause Grafana to continuously process relation-changed events.

    This test uses `juju show-status-log` to verify Grafana isn't being disrupted.
    """
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)

    # Get initial executing count
    initial_executing = get_status_log_executing_count(juju, f"{GRAFANA_APP}/0")
    logger.info("Initial 'executing' status count: %d", initial_executing)

    # Trigger multiple update-status events on otelcol to simulate real-world activity
    for i in range(3):
        logger.info("Triggering update-status hook %d on %s", i + 1, OTELCOL_APP)
        juju.cli("exec", "--unit", f"{OTELCOL_APP}/0", "--", "JUJU_DISPATCH_PATH=hooks/update-status", "./dispatch")
        juju.wait(jubilant.all_active, timeout=60)
        time.sleep(2)

    # Wait for any cascading events
    time.sleep(10)

    # Verify Grafana is still healthy
    status = juju.status()
    grafana_unit = status.apps[GRAFANA_APP].units[f"{GRAFANA_APP}/0"]
    assert grafana_unit.workload_status.current == "active"

    # Check Grafana's status log for excessive activity
    final_executing = get_status_log_executing_count(juju, f"{GRAFANA_APP}/0")
    new_executing = final_executing - initial_executing
    logger.info(
        "New 'executing' status entries: %d (was %d, now %d)",
        new_executing,
        initial_executing,
        final_executing,
    )

    # With the bug, we'd see many "executing" entries as Grafana processes
    # each relation-changed event. With the fix, we should see very few.
    # Allow some tolerance for normal operation (e.g., 2 per update-status event).
    assert new_executing <= 6, (
        f"Grafana entered 'executing' state {new_executing} additional times during "
        f"provider update-status events. This suggests excessive relation-changed "
        f"events are being triggered. Expected <= 6 for 3 update-status events."
    )

    logger.info("Grafana remained stable during provider event activity")


async def test_cleanup(ops_test: OpsTest):
    """Clean up test resources."""
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)

    logger.info("Removing %s", OTELCOL_APP)
    juju.remove_application(OTELCOL_APP)
    juju.wait(
        lambda status: OTELCOL_APP not in status.apps,
        timeout=300,
    )

    # Verify Grafana is still healthy
    status = juju.status()
    grafana_unit = status.apps[GRAFANA_APP].units[f"{GRAFANA_APP}/0"]
    assert grafana_unit.workload_status.current == "active"
    logger.info("Grafana healthy after otelcol removal")
