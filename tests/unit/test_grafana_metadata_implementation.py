"""Tests that assert GrafanaCharm is wired up correctly to be a grafana-metadata provider."""
from typing import Optional, Tuple

from ops.testing import Relation, State

from charm import PORT
from tests.unit.conftest import GRAFANA_FQDN

RELATION_NAME = "grafana-metadata"
INTERFACE_NAME = "grafana_metadata"

# Note: if this is changed, the GrafanaMetadataAppData concrete classes below need to change their constructors to match
SAMPLE_APP_DATA = {
    "grafana_uid": "grafana-uid",
    "ingress_url": "ingress-url",
    "internal_url": "internal-url",
}

GRAFANA_URL = f"http://{GRAFANA_FQDN}:{PORT}"


def local_app_data_relation_state(leader: bool, local_app_data: Optional[dict] = None) -> Tuple[Relation, State]:
    """Return a testing State that has a single relation with the given local_app_data."""
    if local_app_data is None:
        local_app_data = {}
    else:
        # Scenario might edit this dict, and it could be used elsewhere
        local_app_data = dict(local_app_data)

    relation = Relation(RELATION_NAME, INTERFACE_NAME, local_app_data=local_app_data)
    relations = [relation]

    state = State(
        relations=relations,
        leader=leader,
    )

    return relation, state


def test_provider_sender_sends_data_on_relation_joined(ctx):
    """Tests that a charm using ProviderSender sends the correct data to the relation on a relation joined event."""
    # Arrange
    relation, state = local_app_data_relation_state(leader=True)

    # Act
    with ctx(
            ctx.on.relation_joined(relation),
            state=state
    ) as manager:
        charm = manager.charm
        manager.run()
        expected = {
            "grafana_uid": charm.unique_name,
            "internal_url": GRAFANA_URL,
            "ingress_url": GRAFANA_URL,
        }

    # Assert
    assert relation.local_app_data == expected


def test_provider_sends_data_on_leader_elected(ctx):
    """Tests that a charm using GrafanaMetadataProvider sends data on a leader elected event."""
    # Arrange
    relation, state = local_app_data_relation_state(leader=True)

    # Act
    with ctx(
            ctx.on.leader_elected(),
            state=state
    ) as manager:
        charm = manager.charm
        manager.run()
        expected = {
            "grafana_uid": charm.unique_name,
            "internal_url": GRAFANA_URL,
            "ingress_url": GRAFANA_URL,
        }

    # Assert
    assert relation.local_app_data == expected
