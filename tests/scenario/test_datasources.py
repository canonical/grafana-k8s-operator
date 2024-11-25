import json

from ops import CharmBase, Framework
from ops.testing import Container, State
from scenario import Relation, PeerRelation, Context

from charms.grafana_k8s.v0.grafana_source import GrafanaSourceProvider

containers = [
    Container(name="grafana", can_connect=True),
    Container(name="litestream", can_connect=True),
]


def test_datasource_sharing(ctx):
    # GIVEN a datasource relation with two remote units
    datasource = Relation(
        "grafana-source",
        remote_app_name="remote_host",
        remote_units_data={
            0: {"grafana_source_host": "remote_host.0"},
            1: {"grafana_source_host": "remote_host.1"},
        },
        remote_app_data={
            "grafana_source_data": json.dumps(
                {"model": "foo", "model_uuid": "bar", "application": "baz", "type": "tempo"}
            )
        },
    )
    state = State(
        leader=True, containers=containers, relations={datasource, PeerRelation("grafana")}
    )

    # WHEN relation-changed fires for a datasource relation
    out = ctx.run(ctx.on.relation_changed(datasource), state)

    # THEN grafana shares back over the same relation a mapping of datasource uids
    datasource_out = out.get_relation(datasource.id)
    local_app_data = datasource_out.local_app_data
    ds_uids = json.loads(local_app_data["datasource_uids"])
    assert ds_uids == {
        "remote_host/0": "juju_foo_bar_baz_0",
        "remote_host/1": "juju_foo_bar_baz_1",
    }


def test_datasource_get():
    # GIVEN a datasource relation with two remote units
    local_ds_uids = {
        "prometheus/0": "some-datasource-uid",
        "prometheus/1": "some-datasource-uid",
    }
    datasource = Relation(
        "grafana-source",
        remote_app_name="remote_host",
        local_unit_data={"grafana_source_host": "somehost:80"},
        local_app_data={
            "grafana_source_data": json.dumps(
                {"model": "foo", "model_uuid": "bar", "application": "baz", "type": "tempo"}
            )
        },
        remote_app_data={"datasource_uids": json.dumps(local_ds_uids)},
    )
    state = State(leader=True, relations={datasource})

    # WHEN relation-changed fires for a datasource relation
    class MyProviderCharm(CharmBase):
        META = {
            "name": "edgar",
            "provides": {"grafana-source": {"interface": "grafana_datasource"}},
        }

        def __init__(self, framework: Framework):
            super().__init__(framework)
            self.source_provider = GrafanaSourceProvider(
                self, "tempo", source_url="somehost", source_port="80"
            )

    ctx = Context(MyProviderCharm, MyProviderCharm.META)
    with ctx(ctx.on.relation_changed(datasource), state) as mgr:
        charm = mgr.charm
        # THEN we can see our datasource uids via the provider
        assert list(charm.source_provider.get_source_uids().values())[0] == local_ds_uids
