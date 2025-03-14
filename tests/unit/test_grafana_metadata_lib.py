"""Tests for the grafana-metadata lib requirer and provider classes, excluding their usage in GrafanaCharm."""

from typing import Union

import pytest
from ops import CharmBase
from ops.testing import Context, Relation, State

from charms.grafana_k8s.v0.grafana_metadata import GrafanaMetadataProvider, GrafanaMetadataRequirer, \
    GrafanaMetadataAppData

RELATION_NAME = "app-data-relation"
INTERFACE_NAME = "app-data-interface"

# Note: if this is changed, the GrafanaMetadataAppData concrete classes below need to change their constructors to match
SAMPLE_APP_DATA = GrafanaMetadataAppData(
    grafana_uid="grafana-uid",
    ingress_url="http://www.ingress-url.com/",
    direct_url="http://www.internal-url.com/",
)
SAMPLE_APP_DATA_2 = GrafanaMetadataAppData(
    grafana_uid="grafana-uid2",
    ingress_url="http://www.ingress-url2.com/",
    direct_url="http://www.internal-url2.com/",
)
SAMPLE_APP_DATA_NO_INGRESS_URL = GrafanaMetadataAppData(
    grafana_uid="grafana-uid",
    ingress_url="http://www.ingress-url.com/",
    direct_url="http://www.internal-url.com/",
)


class GrafanaMetadataProviderCharm(CharmBase):
    META = {
        "name": "provider",
        "provides": {RELATION_NAME: {"interface": RELATION_NAME}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.relation_provider = GrafanaMetadataProvider(
            self.model.relations, app=self.app, relation_name=RELATION_NAME
        )


@pytest.fixture()
def grafana_metadata_provider_context():
    return Context(charm_type=GrafanaMetadataProviderCharm, meta=GrafanaMetadataProviderCharm.META)


class GrafanaMetadataRequirerCharm(CharmBase):
    META = {
        "name": "requirer",
        "requires": {RELATION_NAME: {"interface": "grafana-metadata"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.relation_requirer = GrafanaMetadataRequirer(self.model.relations, relation_name=RELATION_NAME)


@pytest.fixture()
def grafana_metadata_requirer_context():
    return Context(charm_type=GrafanaMetadataRequirerCharm, meta=GrafanaMetadataRequirerCharm.META)


@pytest.mark.parametrize("data", [SAMPLE_APP_DATA, SAMPLE_APP_DATA_NO_INGRESS_URL])
def test_grafana_metadata_provider_sends_data_correctly(data, grafana_metadata_provider_context):
    """Tests that a charm using GrafanaMetadataProvider sends the correct data during publish."""
    # Arrange
    grafana_metadata_relation = Relation(RELATION_NAME, INTERFACE_NAME, local_app_data={})
    relations = [grafana_metadata_relation]
    state = State(relations=relations, leader=True)

    # Act
    with grafana_metadata_provider_context(
        # construct a charm using an event that won't trigger anything here
        grafana_metadata_provider_context.on.update_status(), state=state
    ) as manager:
        manager.charm.relation_provider.publish(**data.model_dump())

        # Assert
        # Convert local_app_data to TempoApiAppData for comparison
        grafana_metadata_relation_out = manager.ops.state.get_relation(grafana_metadata_relation.id)
        actual = GrafanaMetadataAppData.model_validate(dict(grafana_metadata_relation_out.local_app_data))
        assert actual == data


@pytest.mark.parametrize(
    "relations, expected_data",
    [
        # no relations
        ([], None),
        # one empty relation
        (
            [Relation(RELATION_NAME, INTERFACE_NAME, remote_app_data={})],
            None,
        ),
        # one populated relation
        (
            [
                Relation(
                    RELATION_NAME,
                    INTERFACE_NAME,
                    remote_app_data=SAMPLE_APP_DATA.model_dump(mode="json"),
                )
            ],
            SAMPLE_APP_DATA,
        ),
        # one populated relation without ingress_url
        (
            [
                Relation(
                    RELATION_NAME,
                    INTERFACE_NAME,
                    remote_app_data=SAMPLE_APP_DATA_NO_INGRESS_URL.model_dump(mode="json"),
                )
            ],
            SAMPLE_APP_DATA_NO_INGRESS_URL,
        ),
    ],
)
def test_grafana_metadata_requirer_get_data(relations, expected_data, grafana_metadata_requirer_context):
    """Tests that GrafanaMetadataRequirer.get_data() returns correctly."""
    state = State(
        relations=relations,
        leader=False,
    )

    with grafana_metadata_requirer_context(
        grafana_metadata_requirer_context.on.update_status(), state=state
    ) as manager:
        charm = manager.charm

        data = charm.relation_requirer.get_data()
        assert are_app_data_equal(data, expected_data)


def are_app_data_equal(data1: Union[GrafanaMetadataAppData, None], data2: Union[GrafanaMetadataAppData, None]):
    """Compare two GrafanaMetadataRequirer objects, tolerating when one or both is None."""
    if data1 is None and data2 is None:
        return True
    if data1 is None or data2 is None:
        return False
    return data1.model_dump() == data2.model_dump()
