# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for dashboard relation stability fix.

These tests verify that the grafana_dashboard library only updates the relation
databag (and generates a new UUID) when dashboard templates have actually changed.

See: https://github.com/canonical/opentelemetry-collector-operator/issues/331
"""

import json

from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from ops import CharmBase, Framework
from ops.testing import Context, Relation, State


class DashboardProviderCharm(CharmBase):
    """Test charm that provides dashboards."""

    META = {
        "name": "dashboard-provider",
        "provides": {"grafana-dashboard": {"interface": "grafana_dashboard"}},
    }

    def __init__(self, framework: Framework):
        super().__init__(framework)
        self.dashboard_provider = GrafanaDashboardProvider(
            self,
            relation_name="grafana-dashboard",
            dashboards_path="./tests/unit/dashboard_templates",
        )


SAMPLE_TEMPLATES = {
    "file:test-dashboard": {
        "charm": "dashboard-provider",
        "content": "eyJ0ZXN0IjogImRhc2hib2FyZCJ9",  # base64 of {"test": "dashboard"}
        "juju_topology": {
            "model": "testing",
            "model_uuid": "test-uuid",
            "application": "dashboard-provider",
            "unit": "dashboard-provider/0",
        },
        "inject_dropdowns": True,
        "dashboard_alt_uid": "abc123",
    }
}


def test_uuid_stable_when_templates_unchanged():
    """Test that the UUID doesn't change when templates haven't changed.

    This is the core fix for issue #331. When _upset_dashboards_on_relation()
    is called but templates haven't changed, the databag should not be updated.
    """
    # GIVEN an existing relation with dashboard data including a UUID
    original_uuid = "original-uuid-12345"
    existing_dashboards = {
        "templates": SAMPLE_TEMPLATES,
        "uuid": original_uuid,
    }
    dashboard_relation = Relation(
        "grafana-dashboard",
        remote_app_name="grafana",
        local_app_data={"dashboards": json.dumps(existing_dashboards)},
    )
    state = State(leader=True, relations={dashboard_relation})

    ctx = Context(DashboardProviderCharm, DashboardProviderCharm.META)

    # WHEN we trigger an event that calls _upset_dashboards_on_relation
    # with the same templates already in stored state
    with ctx(ctx.on.relation_changed(dashboard_relation), state) as mgr:
        charm = mgr.charm
        # Manually set stored templates to match what's in the databag
        charm.dashboard_provider._stored.dashboard_templates = SAMPLE_TEMPLATES

        # Get the relation and call _upset_dashboards_on_relation
        relation = charm.model.get_relation("grafana-dashboard")
        assert relation is not None
        charm.dashboard_provider._upset_dashboards_on_relation(relation)

        # THEN the databag should NOT have been updated (UUID unchanged)
        databag_str = relation.data[charm.app].get("dashboards", "{}")
        databag = json.loads(databag_str)

        assert databag.get("uuid") == original_uuid, (
            f"UUID changed from '{original_uuid}' to '{databag.get('uuid')}' "
            "even though templates haven't changed"
        )


def test_uuid_changes_when_templates_change():
    """Test that the UUID does change when templates have changed.

    This ensures the fix doesn't break the case where templates actually change
    and we need to notify the consumer.
    """
    # GIVEN an existing relation with dashboard data
    original_uuid = "original-uuid-12345"
    existing_dashboards = {
        "templates": SAMPLE_TEMPLATES,
        "uuid": original_uuid,
    }
    dashboard_relation = Relation(
        "grafana-dashboard",
        remote_app_name="grafana",
        local_app_data={"dashboards": json.dumps(existing_dashboards)},
    )
    state = State(leader=True, relations={dashboard_relation})

    ctx = Context(DashboardProviderCharm, DashboardProviderCharm.META)

    # WHEN we trigger an event with DIFFERENT templates in stored state
    with ctx(ctx.on.relation_changed(dashboard_relation), state) as mgr:
        charm = mgr.charm

        # Set stored templates to something different
        new_templates = {
            "file:new-dashboard": {
                "charm": "dashboard-provider",
                "content": "eyJuZXciOiAiZGFzaGJvYXJkIn0=",  # different content
                "juju_topology": {
                    "model": "testing",
                    "model_uuid": "test-uuid",
                    "application": "dashboard-provider",
                    "unit": "dashboard-provider/0",
                },
                "inject_dropdowns": True,
                "dashboard_alt_uid": "xyz789",
            }
        }
        charm.dashboard_provider._stored.dashboard_templates = new_templates

        # Get the relation and call _upset_dashboards_on_relation
        relation = charm.model.get_relation("grafana-dashboard")
        assert relation is not None
        charm.dashboard_provider._upset_dashboards_on_relation(relation)

        # THEN the databag should have been updated (UUID changed, templates updated)
        databag_str = relation.data[charm.app].get("dashboards", "{}")
        databag = json.loads(databag_str)

        assert databag.get("uuid") != original_uuid, (
            "UUID should have changed because templates changed"
        )
        assert databag.get("templates") == new_templates, (
            "Templates in databag should match the new templates"
        )


def test_uuid_generated_on_first_update():
    """Test that UUID is generated when databag is empty (first update)."""
    # GIVEN an empty relation (no existing dashboard data)
    dashboard_relation = Relation(
        "grafana-dashboard",
        remote_app_name="grafana",
        local_app_data={},  # Empty databag
    )
    state = State(leader=True, relations={dashboard_relation})

    ctx = Context(DashboardProviderCharm, DashboardProviderCharm.META)

    # WHEN we trigger an event that calls _upset_dashboards_on_relation
    with ctx(ctx.on.relation_changed(dashboard_relation), state) as mgr:
        charm = mgr.charm
        charm.dashboard_provider._stored.dashboard_templates = SAMPLE_TEMPLATES

        relation = charm.model.get_relation("grafana-dashboard")
        assert relation is not None
        charm.dashboard_provider._upset_dashboards_on_relation(relation)

        # THEN the databag should be populated with templates and a new UUID
        databag_str = relation.data[charm.app].get("dashboards", "{}")
        databag = json.loads(databag_str)

        assert databag.get("uuid"), "UUID should be generated on first update"
        assert databag.get("templates") == SAMPLE_TEMPLATES, (
            "Templates should be set in databag"
        )


def test_uuid_generated_when_existing_databag_invalid_json():
    """Test that UUID is generated when existing databag contains invalid JSON."""
    # GIVEN a relation with invalid JSON in the databag
    dashboard_relation = Relation(
        "grafana-dashboard",
        remote_app_name="grafana",
        local_app_data={"dashboards": "not valid json {{{"},
    )
    state = State(leader=True, relations={dashboard_relation})

    ctx = Context(DashboardProviderCharm, DashboardProviderCharm.META)

    # WHEN we trigger an event that calls _upset_dashboards_on_relation
    with ctx(ctx.on.relation_changed(dashboard_relation), state) as mgr:
        charm = mgr.charm
        charm.dashboard_provider._stored.dashboard_templates = SAMPLE_TEMPLATES

        relation = charm.model.get_relation("grafana-dashboard")
        assert relation is not None
        charm.dashboard_provider._upset_dashboards_on_relation(relation)

        # THEN the databag should be updated with valid data
        databag_str = relation.data[charm.app].get("dashboards", "{}")
        databag = json.loads(databag_str)

        assert databag.get("uuid"), "UUID should be generated"
        assert databag.get("templates") == SAMPLE_TEMPLATES
