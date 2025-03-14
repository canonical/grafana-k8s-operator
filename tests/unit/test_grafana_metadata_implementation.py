"""Tests that assert GrafanaCharm is wired up correctly to be a grafana-metadata provider."""
from typing import Optional, Tuple
from unittest.mock import patch, PropertyMock

from ops.testing import Relation, State

from charm import PORT
from tests.unit.conftest import GRAFANA_FQDN

RELATION_NAME = "grafana-metadata"
INTERFACE_NAME = "grafana_metadata"

# Note: if this is changed, the GrafanaMetadataAppData concrete classes below need to change their constructors to match
SAMPLE_APP_DATA = {
    "grafana_uid": "grafana-uid",
    "ingress_url": "http://www.ingress-url.com/",
    "direct_url": "http://www.internal-url.com/",
}

GRAFANA_URL = f"http://{GRAFANA_FQDN}:{PORT}/"
GRAFANA_INGRESS_URL = "http://www.ingress-url.com/"


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
    """Tests that a charm using GrafanaMetadataProvider sends the correct data on a relation joined event."""
    # Arrange
    relation, state = local_app_data_relation_state(leader=True)

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
def test_provider_sender_sends_data_with_ingress_url_on_relation_joined(ctx):
    """Tests that a charm using GrafanaMetadataProvider with an external url sends the correct data."""
    # Arrange
    relation, state = local_app_data_relation_state(leader=True)

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
        state_out = manager.run()
        expected = {
            "grafana_uid": charm.unique_name,
            "direct_url": GRAFANA_URL,
        }

    # Assert
    assert state_out.get_relation(relation.id).local_app_data == expected
