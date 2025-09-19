"""Tests that assert GrafanaCharm is wired up correctly to be a grafana-metadata provider."""
from dataclasses import replace
from unittest.mock import patch, PropertyMock

from ops.testing import Relation

from tests.unit.conftest import GRAFANA_FQDN
from src.constants import WORKLOAD_PORT

RELATION_NAME = "grafana-metadata"
INTERFACE_NAME = "grafana_metadata"

# Note: if this is changed, the GrafanaMetadataAppData concrete classes below need to change their constructors to match
SAMPLE_APP_DATA = {
    "grafana_uid": "grafana-uid",
    "ingress_url": "http://www.ingress-url.com/",
    "direct_url": "http://www.internal-url.com/",
}

GRAFANA_URL = f"http://{GRAFANA_FQDN}:{WORKLOAD_PORT}/"
GRAFANA_INGRESS_URL = "http://www.ingress-url.com/"


def test_provider_sender_sends_data_on_relation_joined(ctx, base_state, peer_relation, database_relation):
    """Tests that a charm using GrafanaMetadataProvider sends the correct data on a relation joined event."""
    # Arrange
    relation = Relation(RELATION_NAME, INTERFACE_NAME)
    state = replace(base_state, relations={relation, peer_relation, database_relation})

    # Act
    with ctx(
            ctx.on.relation_joined(relation),
            state=state
    ) as manager:
        charm = manager.charm
        state_out = manager.run()
        expected = {
            "grafana_uid": charm.unique_name,
            "direct_url": GRAFANA_URL,
        }

    # Assert
    assert state_out.get_relation(relation.id).local_app_data == expected


@patch("charm.GrafanaCharm.external_url", PropertyMock(return_value=GRAFANA_INGRESS_URL))
def test_provider_sender_sends_data_with_ingress_url_on_relation_joined(ctx, base_state, peer_relation, database_relation):
    """Tests that a charm using GrafanaMetadataProvider with an external url sends the correct data."""
    # Arrange
    relation = Relation(RELATION_NAME, INTERFACE_NAME)
    state = replace(base_state, relations={relation, peer_relation, database_relation})

    # Act
    with ctx(
            ctx.on.relation_joined(relation),
            state=state
    ) as manager:
        charm = manager.charm
        state_out = manager.run()
        expected = {
            "grafana_uid": charm.unique_name,
            "direct_url": GRAFANA_URL,
            "ingress_url": GRAFANA_INGRESS_URL,
        }

    # Assert
    assert state_out.get_relation(relation.id).local_app_data == expected


def test_provider_sends_data_on_leader_elected(ctx, base_state, peer_relation, database_relation):
    """Tests that a charm using GrafanaMetadataProvider sends data on a leader elected event."""
    # Arrange
    relation = Relation(RELATION_NAME, INTERFACE_NAME)
    state = replace(base_state, relations={relation, peer_relation, database_relation})

    # Act
    with ctx(
            ctx.on.leader_elected(),
            state=state
    ) as manager:
        charm = manager.charm
        state_out = manager.run()
        expected = {
            "grafana_uid": charm.unique_name,
            "direct_url": GRAFANA_URL,
        }

    # Assert
    assert state_out.get_relation(relation.id).local_app_data == expected
