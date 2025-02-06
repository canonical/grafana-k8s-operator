"""Tests for the grafana-metadata lib requirer and provider classes, excluding their usage in GrafanaCharm."""

from contextlib import nullcontext as does_not_raise
from typing import Union

import pytest
from ops import CharmBase
from ops.testing import Context, Relation, State

from charms.grafana_k8s.v0.grafana_metadata import GrafanaMetadataProvider, GrafanaMetadataRequirer, DataChangedEvent, \
    GrafanaMetadataAppData

RELATION_NAME = "app-data-relation"
INTERFACE_NAME = "app-data-interface"

# Note: if this is changed, the GrafanaMetadataAppData concrete classes below need to change their constructors to match
SAMPLE_APP_DATA = {
    "grafana_uid": "grafana-uid",
    "ingress_url": "ingress-url",
    "internal_url": "internal-url",
}
SAMPLE_APP_DATA_2 = {
    "grafana_uid": "grafana-uid2",
    "ingress_url": "ingress-url2",
    "internal_url": "internal-url2",
}


class GrafanaMetadataProviderCharm(CharmBase):
    META = {
        "name": "provider",
        "provides": {RELATION_NAME: {"interface": RELATION_NAME}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.relation_provider = GrafanaMetadataProvider(
            self, **SAMPLE_APP_DATA, relation_name=RELATION_NAME
        )


@pytest.fixture()
def grafana_metadata_provider_context():
    return Context(charm_type=GrafanaMetadataProviderCharm, meta=GrafanaMetadataProviderCharm.META)


class GrafanaMetadataRequirerCharm(CharmBase):
    META = {
        "name": "requirer",
        "requires": {RELATION_NAME: {"interface": "istio-info"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.relation_requirer = GrafanaMetadataRequirer(self, relation_name=RELATION_NAME)


@pytest.fixture()
def grafana_metadata_requirer_context():
    return Context(charm_type=GrafanaMetadataRequirerCharm, meta=GrafanaMetadataRequirerCharm.META)


def local_app_data_relation_state(leader: bool, local_app_data: dict = None) -> (Relation, State):
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


def test_provider_sender_sends_data_on_relation_joined(grafana_metadata_provider_context):
    """Tests that a charm using ProviderSender sends the correct data to the relation on a relation joined event."""
    # Arrange
    relation, state = local_app_data_relation_state(leader=True)

    # Act
    grafana_metadata_provider_context.run(grafana_metadata_provider_context.on.relation_joined(relation), state=state)

    # Assert
    assert relation.local_app_data == SAMPLE_APP_DATA


def test_provider_sends_data_on_leader_elected(grafana_metadata_provider_context):
    """Tests that a charm using IstioInfoProvider sends the correct data to the relation on a leader elected event."""
    # Arrange
    relation, state = local_app_data_relation_state(leader=True)

    # Act
    grafana_metadata_provider_context.run(grafana_metadata_provider_context.on.leader_elected(), state=state)

    # Assert
    assert relation.local_app_data == SAMPLE_APP_DATA


def test_provider_doesnt_send_data_when_not_leader(grafana_metadata_provider_context):
    """Tests that a charm using the IstioInfoProvider does not send data if not the leader."""
    # Arrange
    relation, state = local_app_data_relation_state(leader=False)

    events = [
        grafana_metadata_provider_context.on.relation_joined(relation),
        grafana_metadata_provider_context.on.leader_elected(),
        grafana_metadata_provider_context.on.config_changed(),  # just to have some other event
    ]
    for event in events:
        # Act
        grafana_metadata_provider_context.run(event, state=state)

        # Assert
        assert relation.local_app_data == {}


@pytest.mark.parametrize(
    "local_app_data",
    [
        {},  # relation starts with empty data
        SAMPLE_APP_DATA_2,  # relation starts with stale data
    ],
)
def test_provider_is_ready(local_app_data, grafana_metadata_provider_context):
    """Tests that a charm using the IstioInfoProvider correctly assesses whether the data sent is up to date."""
    # Arrange
    relation, state = local_app_data_relation_state(leader=True, local_app_data=local_app_data)

    with grafana_metadata_provider_context(
        grafana_metadata_provider_context.on.relation_joined(relation), state=state
    ) as manager:
        charm = manager.charm

        # Before executing the event that causes data to be emitted, the relation handler should not be ready
        assert not charm.relation_provider.is_ready()

        # After the data is sent, the provider should indicate ready
        manager.run()
        assert charm.relation_provider.is_ready()


def test_requirer_emits_info_changed_on_relation_data_changes(grafana_metadata_requirer_context):
    """Tests that a charm using IstioInfoRequirer emits a DataChangedEvent when the relation data changes."""
    # Arrange
    relation, state = local_app_data_relation_state(leader=False)

    # Act
    grafana_metadata_requirer_context.run(
        grafana_metadata_requirer_context.on.relation_changed(relation), state=state
    )

    # Assert we emitted the info changed event
    # Note: emitted_events also includes the event we executed above in .run()
    assert len(grafana_metadata_requirer_context.emitted_events) == 2
    assert isinstance(grafana_metadata_requirer_context.emitted_events[1], DataChangedEvent)


@pytest.mark.parametrize(
    "relations, expected_data, context_raised",
    [
        ([], None, does_not_raise()),  # no relations
        (
            [Relation(RELATION_NAME, INTERFACE_NAME, remote_app_data={})],
            None,
            does_not_raise(),
        ),  # one empty relation
        (
            [
                Relation(
                    RELATION_NAME,
                    INTERFACE_NAME,
                    remote_app_data=SAMPLE_APP_DATA,
                )
            ],
            GrafanaMetadataAppData(**SAMPLE_APP_DATA),
            does_not_raise(),
        ),  # one populated relation
        (
            [
                Relation(
                    RELATION_NAME,
                    INTERFACE_NAME,
                    remote_app_data=SAMPLE_APP_DATA,
                ),
                Relation(
                    RELATION_NAME,
                    INTERFACE_NAME,
                    remote_app_data=SAMPLE_APP_DATA,
                ),
            ],
            None,
            pytest.raises(ValueError),
        ),  # stale data
    ],
)
def test_requirer_get_data(relations, expected_data, context_raised, grafana_metadata_requirer_context):
    """Tests that IstioInfoRequirer.get_data() returns correctly."""
    state = State(
        relations=relations,
        leader=False,
    )

    with grafana_metadata_requirer_context(
        grafana_metadata_requirer_context.on.update_status(), state=state
    ) as manager:
        charm = manager.charm

        with context_raised:
            data = charm.relation_requirer.get_data()
            assert are_app_data_equal(data, expected_data)


@pytest.mark.parametrize(
    "relations, expected_data, context_raised",
    [
        # no relations
        ([], [], does_not_raise()),
        # one empty relation
        (
            [Relation(RELATION_NAME, INTERFACE_NAME, remote_app_data={})],
            [None],
            does_not_raise(),
        ),
        # one populated relation
        (
            [
                Relation(
                    RELATION_NAME,
                    INTERFACE_NAME,
                    remote_app_data=SAMPLE_APP_DATA,
                )
            ],
            [GrafanaMetadataAppData(**SAMPLE_APP_DATA)],
            does_not_raise(),
        ),
        # many related applications, some with missing data
        (
            [
                Relation(
                    RELATION_NAME,
                    INTERFACE_NAME,
                    remote_app_data=SAMPLE_APP_DATA,
                ),
                Relation(RELATION_NAME, INTERFACE_NAME, remote_app_data={}),
                Relation(
                    RELATION_NAME,
                    INTERFACE_NAME,
                    remote_app_data=SAMPLE_APP_DATA_2,
                ),
            ],
            [
                GrafanaMetadataAppData(**SAMPLE_APP_DATA),
                None,
                GrafanaMetadataAppData(**SAMPLE_APP_DATA_2),
            ],
            does_not_raise(),
        ),
    ],
)
def test_requirer_get_data_from_all_relations(
    relations, expected_data, context_raised, grafana_metadata_requirer_context
):
    """Tests that IstioInfoRequirer.get_data_from_all_relations() returns correctly."""
    state = State(
        relations=relations,
        leader=False,
    )

    with grafana_metadata_requirer_context(
        grafana_metadata_requirer_context.on.update_status(), state=state
    ) as manager:
        charm = manager.charm

        with context_raised:
            data = sort_app_data(charm.relation_requirer.get_data_from_all_relations())
            expected_data = sort_app_data(expected_data)
            for actual, expected in zip(data, expected_data):
                assert are_app_data_equal(actual, expected)


def sort_app_data(data):
    """Return sorted version of the list of relation data objects."""
    return sorted(data, key=lambda x: x.grafana_uid if x else "")


def are_app_data_equal(data1: Union[GrafanaMetadataAppData, None], data2: Union[GrafanaMetadataAppData, None]):
    """Compare two GrafanaMetadataAppData objects, tolerating when one or both is None."""
    if data1 is None and data2 is None:
        return True
    if data1 is None or data2 is None:
        return False
    return data1.model_dump() == data2.model_dump()
