import json

from ops import CharmBase, Framework
from ops.testing import State, Relation, Context
from unittest.mock import patch

from charms.grafana_k8s.v1.grafana_source import GrafanaSourceProvider


@patch("socket.getfqdn", new=lambda *args: "fqdn")
def test_datasource_sharing(ctx, peer_relation, containers):
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
        leader=True, containers=containers, relations={datasource, peer_relation}
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
    assert local_app_data["grafana_uid"]
    # AND its base URL
    assert local_app_data["grafana_base_url"] == "http://fqdn:3000"
    # AND no app-level datasource uid (none was advertised)
    assert local_app_data.get("app_datasource_uid", "") == ""


@patch("socket.getfqdn", new=lambda *args: "fqdn")
def test_app_datasource_sharing(ctx, peer_relation, containers):
    # GIVEN a datasource relation where the provider advertises an app-level host
    datasource = Relation(
        "grafana-source",
        remote_app_name="remote_host",
        remote_units_data={
            0: {"grafana_source_host": ""},
            1: {"grafana_source_host": ""},
        },
        remote_app_data={
            "grafana_source_data": json.dumps(
                {"model": "foo", "model_uuid": "bar", "application": "baz", "type": "mimir"}
            ),
            "grafana_source_app_host": "http://baz.foo.svc.cluster.local:9009/prometheus",
        },
    )
    state = State(leader=True, containers=containers, relations={datasource, peer_relation})

    # WHEN relation-changed fires
    out = ctx.run(ctx.on.relation_changed(datasource), state)

    # THEN the app-level datasource uid (no unit number) is shared back
    local_app_data = out.get_relation(datasource.id).local_app_data
    assert local_app_data["app_datasource_uid"] == "juju_foo_bar_baz"
    # AND no per-unit datasource uids are produced (units advertised nothing)
    assert json.loads(local_app_data["datasource_uids"]) == {}


@patch("socket.getfqdn", new=lambda *args: "fqdn")
def test_app_and_unit_datasource_sharing(ctx, peer_relation, containers):
    # GIVEN a datasource relation advertising BOTH app-level and per-unit hosts
    datasource = Relation(
        "grafana-source",
        remote_app_name="remote_host",
        remote_units_data={
            0: {"grafana_source_host": "remote_host.0"},
            1: {"grafana_source_host": "remote_host.1"},
        },
        remote_app_data={
            "grafana_source_data": json.dumps(
                {"model": "foo", "model_uuid": "bar", "application": "baz", "type": "prometheus"}
            ),
            "grafana_source_app_host": "http://baz.foo.svc.cluster.local:9090",
        },
    )
    state = State(leader=True, containers=containers, relations={datasource, peer_relation})

    # WHEN relation-changed fires
    out = ctx.run(ctx.on.relation_changed(datasource), state)

    # THEN both the app-level uid and the per-unit uids are shared back
    local_app_data = out.get_relation(datasource.id).local_app_data
    assert local_app_data["app_datasource_uid"] == "juju_foo_bar_baz"
    assert json.loads(local_app_data["datasource_uids"]) == {
        "remote_host/0": "juju_foo_bar_baz_0",
        "remote_host/1": "juju_foo_bar_baz_1",
    }


def test_datasource_get():
    # GIVEN a datasource relation with two remote units
    local_ds_uids = {
        "prometheus/0": "some-datasource-uid",
        "prometheus/1": "some-datasource-uid",
    }
    grafana_uid = "foo-grafana-1"
    grafana_base_url = "http://ingress"
    datasource = Relation(
        "grafana-source",
        remote_app_name="remote_host",
        local_unit_data={"grafana_source_host": "somehost:80"},
        local_app_data={
            "grafana_source_data": json.dumps(
                {"model": "foo", "model_uuid": "bar", "application": "baz", "type": "tempo"}
            )
        },
        remote_app_data={
            "grafana_uid": grafana_uid,
            "datasource_uids": json.dumps(local_ds_uids),
            "grafana_base_url": grafana_base_url,
        },
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
                self, "tempo", source_port="80"
            )

    ctx = Context(MyProviderCharm, MyProviderCharm.META)
    with ctx(ctx.on.relation_changed(datasource), state) as mgr:
        charm = mgr.charm
        # THEN we can see our datasource uids via the provider
        ds_uids = list(charm.source_provider.get_source_uids().values())[0]  # type: ignore
        assert ds_uids == local_ds_uids
        # AND `get_source_data.datasource_uids` is equivalent to `get_source_uids`
        source_data = list(charm.source_provider.get_source_data().values())[0]
        assert ds_uids == source_data.datasource_uids
        # AND we can see the Grafana external URL via the provider
        assert source_data.external_url == grafana_base_url
        # AND there is no app-level datasource uid assigned
        assert source_data.get_app_uid() is None


def test_datasource_get_app_uid():
    # GIVEN a datasource relation where Grafana assigned an app-level datasource uid
    grafana_uid = "foo-grafana-1"
    app_uid = "juju_foo_bar_baz"
    datasource = Relation(
        "grafana-source",
        remote_app_name="remote_host",
        local_app_data={
            "grafana_source_data": json.dumps(
                {"model": "foo", "model_uuid": "bar", "application": "baz", "type": "mimir"}
            ),
            "grafana_source_app_host": "http://baz.foo.svc.cluster.local:9009/prometheus",
        },
        remote_app_data={
            "grafana_uid": grafana_uid,
            "datasource_uids": json.dumps({}),
            "grafana_base_url": "http://ingress",
            "app_datasource_uid": app_uid,
        },
    )
    state = State(leader=True, relations={datasource})

    class MyProviderCharm(CharmBase):
        META = {
            "name": "edgar",
            "provides": {"grafana-source": {"interface": "grafana_datasource"}},
        }

        def __init__(self, framework: Framework):
            super().__init__(framework)
            self.source_provider = GrafanaSourceProvider(self, "mimir", source_port="9009")

    ctx = Context(MyProviderCharm, MyProviderCharm.META)
    with ctx(ctx.on.relation_changed(datasource), state) as mgr:
        charm = mgr.charm
        # THEN we can read the app-level datasource uid via the provider
        source_data = list(charm.source_provider.get_source_data().values())[0]
        assert source_data.get_app_uid() == app_uid


def test_datasource_get_nodata():
    # GIVEN a datasource relation with two remote units, but which hasn't shared any datasource uids
    #  for example because the remote end is using an older charm lib
    datasource = Relation(
        "grafana-source",
        remote_app_name="remote_host",
        local_unit_data={"grafana_source_host": "somehost:80"},
        local_app_data={
            "grafana_source_data": json.dumps(
                {"model": "foo", "model_uuid": "bar", "application": "baz", "type": "tempo"}
            )
        },
        # no remote app data:
        # {"datasource_uids": json.dumps(local_ds_uids)},
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
                self, "tempo", source_port="80"
            )

    ctx = Context(MyProviderCharm, MyProviderCharm.META)
    with ctx(ctx.on.relation_changed(datasource), state) as mgr:
        charm = mgr.charm
        # THEN we can see no datasource uids via the provider
        assert not charm.source_provider.get_source_uids()  # type: ignore
        # AND `get_source_data.datasource_uids` is equivalent to `get_source_uids`
        assert charm.source_provider.get_source_uids() == charm.source_provider.get_source_data()
