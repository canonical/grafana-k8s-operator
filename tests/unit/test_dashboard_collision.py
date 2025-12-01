# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import json
from typing import Any, Dict

from cosl import LZMABase64
from ops.testing import Context, PeerRelation, State


def read_dashboards_from_fs(container, ctx: Context, glob_pattern: str = "juju_*.json") -> Dict[str, str]:
    """Read dashboard files from the simulated filesystem.

    Args:
        container: The container to read from
        ctx: The test context
        glob_pattern: Pattern to match dashboard files

    Returns:
        A mapping from relative filename to the contents of the file
    """
    fs = container.get_filesystem(ctx)
    dashboards_dir = fs / "etc" / "grafana" / "provisioning" / "dashboards"

    dashboard_files = list(dashboards_dir.glob(glob_pattern))
    return {f.name: f.read_text() for f in dashboard_files}


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
        "title": f"Test Dashboard {uid} - {content}",  # Use title for uniqueness
        "panels": [],
    }

    dashboard_json = json.dumps(dashboard_dict)
    compressed_content = LZMABase64.compress(dashboard_json)

    # Return the structure as stored in peer data by GrafanaDashboardConsumer
    # This matches the structure created in _render_dashboards_and_signal_changed
    return {
        "id": f"grafana-dashboard:{relation_id}/dashboard-{uid}",
        "original_id": f"dashboard-{uid}",
        "content": compressed_content,
        "template": {
            "charm": "test-charm",
            "content": compressed_content,
        },
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

    # WHEN the charm processes the dashboards
    out = ctx.run(ctx.on.update_status(), state)

    # THEN both dashboards should be written to the filesystem
    container = out.get_container("grafana")
    dashboards = read_dashboards_from_fs(container, ctx)

    assert len(dashboards) == 2

    # Verify the dashboards have the correct UIDs
    dashboard_contents = [json.loads(content) for content in dashboards.values()]
    dashboard_uids = {d["uid"] for d in dashboard_contents}
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

    # WHEN the charm processes the dashboards
    out = ctx.run(ctx.on.update_status(), state)

    # THEN both dashboards should be written to the filesystem
    container = out.get_container("grafana")
    dashboards = read_dashboards_from_fs(container, ctx)

    assert len(dashboards) == 2

    # Verify the dashboards have the correct UIDs
    dashboard_contents = [json.loads(content) for content in dashboards.values()]
    dashboard_uids = {d["uid"] for d in dashboard_contents}
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

    # WHEN the charm processes the dashboards
    out = ctx.run(ctx.on.update_status(), state)

    # THEN only one dashboard should be written to the filesystem - the one with higher version
    container = out.get_container("grafana")
    dashboards = read_dashboards_from_fs(container, ctx)

    assert len(dashboards) == 1

    # Verify the dashboard has the correct UID and version
    dashboard_content = json.loads(list(dashboards.values())[0])
    assert dashboard_content["uid"] == "dash1"
    assert dashboard_content["version"] == 2


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

    # WHEN the charm processes the dashboards
    out = ctx.run(ctx.on.update_status(), state)

    # THEN only one dashboard should be written to the filesystem
    # Selected deterministically based on (version, relation_id, content) lexicographic order
    container = out.get_container("grafana")
    dashboards = read_dashboards_from_fs(container, ctx)

    assert len(dashboards) == 1

    # Verify the dashboard has the correct UID and version
    dashboard_content = json.loads(list(dashboards.values())[0])
    assert dashboard_content["uid"] == "dash1"
    assert dashboard_content["version"] == 1
    # The one with higher relation_id (and different content) should win
    assert "content_b" in dashboard_content["title"]


