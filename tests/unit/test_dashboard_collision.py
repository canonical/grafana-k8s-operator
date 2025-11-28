# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import json
from typing import Any, Dict

from cosl import LZMABase64
from ops.testing import Context, PeerRelation, State



def dashboard_factory(
    uid: str,
    version: int,
    relation_id: str,
    content: str = "test content"
) -> Dict[str, Any]:
    """Factory function for generating dashboard stand-in dictionaries.

    Args:
        uid: Dashboard UID
        version: Dashboard version number
        relation_id: Relation ID this dashboard belongs to (as string)
        content: Dashboard content (default: "test content")

    Returns:
        A dictionary structure representing stored dashboard data in peer relation
    """
    dashboard_dict = {
        "uid": uid,
        "version": version,
        "title": f"Test Dashboard {uid}",
        "panels": [],
        "content_extra": content  # To make content unique when needed
    }

    dashboard_json = json.dumps(dashboard_dict)
    compressed_content = LZMABase64.compress(dashboard_json)

    # Return the structure as stored in peer data by GrafanaDashboardConsumer
    return {
        "id": f"grafana-dashboard:{relation_id}/dashboard-{uid}",
        "original_id": f"dashboard-{uid}",
        "content": compressed_content,
        "template": {
            "charm": "test-charm",
            "content": compressed_content,
        },
        "valid": True,
        "error": None,
    }


def test_distinct_uid_and_version_both_on_disk(ctx: Context, base_state: State, peer_relation: PeerRelation):
    """Test that two dashboards with distinct uid and version are both provisioned."""
    # GIVEN reldata with two dashboard "objects" with distinct 'uid' and 'version'
    dashboard1 = dashboard_factory(uid="dash1", version=1, relation_id="1")
    dashboard2 = dashboard_factory(uid="dash2", version=2, relation_id="1")

    # Set up peer relation with dashboards
    peer_data = {
        "dashboards": json.dumps({
            "1": [dashboard1, dashboard2]
        })
    }
    peer_relation_with_data = PeerRelation(
        "grafana",
        local_app_data=peer_data
    )

    state = State(
        leader=True,
        containers=base_state.containers,
        relations={peer_relation_with_data}
    )

    # WHEN accessing the dashboards property
    with ctx(ctx.on.config_changed(), state) as mgr:
        charm = mgr.charm
        dashboards = charm.dashboard_consumer.dashboards

        # THEN both dashboards should be returned
        assert len(dashboards) == 2
        dashboard_uids = {d["dashboard_uid"] for d in dashboards}
        assert dashboard_uids == {"dash1", "dash2"}


def test_distinct_uid_same_version_both_on_disk(ctx: Context, base_state: State, peer_relation: PeerRelation):
    """Test that two dashboards with distinct uid but same version are both provisioned."""
    # GIVEN reldata with two dashboard "objects" with distinct 'uid' but same 'version'
    dashboard1 = dashboard_factory(uid="dash1", version=1, relation_id="1")
    dashboard2 = dashboard_factory(uid="dash2", version=1, relation_id="1")

    # Set up peer relation with dashboards
    peer_data = {
        "dashboards": json.dumps({
            "1": [dashboard1, dashboard2]
        })
    }
    peer_relation_with_data = PeerRelation(
        "grafana",
        local_app_data=peer_data
    )

    state = State(
        leader=True,
        containers=base_state.containers,
        relations={peer_relation_with_data}
    )

    # WHEN accessing the dashboards property
    with ctx(ctx.on.config_changed(), state) as mgr:
        charm = mgr.charm
        dashboards = charm.dashboard_consumer.dashboards

        # THEN both dashboards should be returned
        assert len(dashboards) == 2
        dashboard_uids = {d["dashboard_uid"] for d in dashboards}
        assert dashboard_uids == {"dash1", "dash2"}


def test_same_uid_different_version_only_higher_on_disk(ctx: Context, base_state: State, peer_relation: PeerRelation):
    """Test that only the dashboard with higher version is provisioned when uid matches."""
    # GIVEN reldata with two dashboard "objects" with the same 'uid' but different 'version'
    dashboard1 = dashboard_factory(uid="dash1", version=1, relation_id="1")
    dashboard2 = dashboard_factory(uid="dash1", version=2, relation_id="1")

    # Set up peer relation with dashboards
    peer_data = {
        "dashboards": json.dumps({
            "1": [dashboard1, dashboard2]
        })
    }
    peer_relation_with_data = PeerRelation(
        "grafana",
        local_app_data=peer_data
    )

    state = State(
        leader=True,
        containers=base_state.containers,
        relations={peer_relation_with_data}
    )

    # WHEN accessing the dashboards property
    with ctx(ctx.on.config_changed(), state) as mgr:
        charm = mgr.charm
        dashboards = charm.dashboard_consumer.dashboards

        # THEN only one dashboard is returned - the one with the higher version
        assert len(dashboards) == 1
        assert dashboards[0]["dashboard_uid"] == "dash1"
        assert dashboards[0]["dashboard_version"] == 2


def test_same_uid_same_version_deterministic_selection(ctx: Context, base_state: State, peer_relation: PeerRelation):
    """Test deterministic selection when uid and version are the same."""
    # GIVEN reldata with two dashboard "objects" with the same 'uid' and same 'version'
    # from different relations
    dashboard1 = dashboard_factory(uid="dash1", version=1, relation_id="1", content="content_a")
    dashboard2 = dashboard_factory(uid="dash1", version=1, relation_id="2", content="content_b")

    # Set up peer relation with dashboards from different relations
    peer_data = {
        "dashboards": json.dumps({
            "1": [dashboard1],
            "2": [dashboard2]
        })
    }
    peer_relation_with_data = PeerRelation(
        "grafana",
        local_app_data=peer_data
    )

    state = State(
        leader=True,
        containers=base_state.containers,
        relations={peer_relation_with_data}
    )

    # WHEN accessing the dashboards property
    with ctx(ctx.on.config_changed(), state) as mgr:
        charm = mgr.charm
        dashboards = charm.dashboard_consumer.dashboards

        # THEN only one dashboard is returned - selected deterministically
        # based on (version, relation_id, content) lexicographic order
        # The one with higher relation_id should win
        assert len(dashboards) == 1
        assert dashboards[0]["dashboard_uid"] == "dash1"
        assert dashboards[0]["dashboard_version"] == 1
        assert dashboards[0]["relation_id"] == "2"  # Higher relation_id wins


