import json

from ops.testing import Container, State
from scenario import Relation, PeerRelation

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
