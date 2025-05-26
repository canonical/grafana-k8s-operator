# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

from dataclasses import replace
import json
from unittest.mock import patch

from pytest import mark
import yaml
from ops.testing import (Relation,
                        Context,
                        Model,
                        Network,
                        BindAddress,
                        Address,
                        CharmEvents,
                        PeerRelation,
                        State)

import src.grafana_client as grafana_client
from src.constants import CONFIG_PATH, DATASOURCES_PATH, PROVISIONING_PATH

MINIMAL_DATASOURCES_CONFIG = {
    "apiVersion": 1,
    "datasources": [],
    "deleteDatasources": [],
}

BASIC_DATASOURCES = [
    {
        "access": "proxy",
        "isDefault": "false",
        "name": "juju_test-model_abcdef_prometheus_0",
        "orgId": "1",
        "type": "prometheus",
        "url": "http://1.2.3.4:1234",
        "jsonData": {"timeout": 300},
    }
]

SOURCE_DATA = {
    "model": "test-model",
    "model_uuid": "abcdef",
    "application": "prometheus",
    "type": "prometheus",
}

DASHBOARD_CONFIG = {
    "apiVersion": 1,
    "providers": [
        {
            "name": "Default",
            "updateIntervalSeconds": "5",
            "type": "file",
            "options": {"path": "/etc/grafana/provisioning/dashboards"},
        }
    ],
}


DB_CONFIG = {
    "type": "mysql",
    "host": "1.1.1.1:3306",
    "name": "mysqldb",
    "user": "grafana",
    "password": "grafana",
}


DATABASE_CONFIG_INI = """[database]
type = mysql
host = 1.1.1.1:3306
name = mysqldb
user = grafana
password = grafana
url = mysql://grafana:grafana@1.1.1.1:3306/mysqldb

"""

@mark.parametrize("leader", (False, True))
def test_peer_relation_guards(ctx:Context, leader, containers):
    # GIVEN no peer relation
    state = State(leader=leader, containers=containers)

    # WHEN an install event is fired
    with ctx(ctx.on.install(), state) as mgr:
        # THEN no exceptions are raised
        mgr.run()
        charm = mgr.charm
        # AND there is no peer data
        assert charm.peers.data is None


def test_datasource_config_is_updated_by_raw_grafana_source_relation(ctx:Context, base_state, peer_relation: PeerRelation):
    # GIVEN a datasource relation with 1 unit
    datasource = Relation(
        "grafana-source",
        remote_app_name="prometheus",
        remote_units_data={
            0: {"grafana_source_host": "1.2.3.4:1234"},
        },
        remote_app_data={
            "grafana_source_data": json.dumps(
                SOURCE_DATA
            )
        },
    )

    state = replace(base_state, relations={datasource, peer_relation})

    # WHEN running a relation_changed event
    with ctx(ctx.on.relation_changed(datasource), state) as mgr:
        out = mgr.run()
        charm = mgr.charm
        config = charm.unit.get_container("grafana").pull(DATASOURCES_PATH)
        # THEN grafana shares back over the same relation a mapping of datasource uids
        assert yaml.safe_load(config).get("datasources") == BASIC_DATASOURCES

    updated_peer_relation = out.get_relation(peer_relation.id)
    # WHEN running a relation_broken event
    updated_peer_relation = PeerRelation("grafana", local_app_data=updated_peer_relation.local_app_data)
    state = replace(state, relations={updated_peer_relation, datasource})
    with ctx(ctx.on.relation_departed(datasource), state) as mgr:
        mgr.run()
        charm = mgr.charm
        config = yaml.safe_load(charm.unit.get_container("grafana").pull(DATASOURCES_PATH))
        # THEN datasources config is empty AND datasources to delete is not empty
        assert config.get("datasources") == []
        assert config.get("deleteDatasources") == [{"name": "juju_test-model_abcdef_prometheus_0", "orgId": 1}]



def test_config_is_updated_with_database_relation(ctx, base_state, peer_relation):
    # GIVEN a database relation with app data
    database_rel = Relation("database", remote_app_name="mysql", remote_app_data=DB_CONFIG)
    state = replace(base_state, relations={peer_relation, database_rel})

    # WHEN running a relation_changed event
    with ctx(ctx.on.relation_changed(database_rel), state) as mgr:
        mgr.run()
        charm = mgr.charm
        config = charm.unit.get_container("grafana").pull(CONFIG_PATH)
        # THEN we get grafana-config.ini updated with config
        assert config.read() == DATABASE_CONFIG_INI

def test_dashboard_path_is_initialized(ctx, base_state, peer_relation):
    # GIVEN grafana source and metrics relations
    grafana_source_rel = Relation("grafana-source", remote_app_name="prometheus")
    metrics_rel = Relation("metrics-endpoint", remote_app_name="prometheus")
    state = replace(base_state, relations={peer_relation, grafana_source_rel, metrics_rel})

    # WHEN running a relation changed event
    with ctx(ctx.on.relation_changed(metrics_rel), state) as mgr:
        mgr.run()
        charm = mgr.charm
        # THEN dashboards config file is created
        dashboards_dir_path = PROVISIONING_PATH + "/dashboards/default.yaml"
        config = charm.unit.get_container("grafana").pull(dashboards_dir_path)
        assert yaml.safe_load(config) == DASHBOARD_CONFIG

def test_datasource_timeout_value_overrides_config_if_larger(ctx, base_state, peer_relation):
    # GIVEN a datasource relation
    source_data = SOURCE_DATA.copy()
    # set relation data with timeout value larger than default
    source_data["extra_fields"] = {"timeout": 600}  # type: ignore
    datasource_rel = Relation("grafana-source",
                            remote_app_name="prometheus",
                            remote_app_data={"grafana_source_data": json.dumps(source_data)},
                            remote_units_data={
                                0: {"grafana_source_host": "1.2.3.4:1234"},
                            },
                            )
    state = replace(base_state, relations={datasource_rel, peer_relation})
    # WHEN running a relation_changed event
    with ctx(ctx.on.relation_changed(datasource_rel), state) as mgr:
        mgr.run()
        charm = mgr.charm
        config = charm.unit.get_container("grafana").pull(DATASOURCES_PATH)
        expected_source_data = BASIC_DATASOURCES.copy()
        expected_source_data[0]["jsonData"]["timeout"] = 600
        # THEN datasources config gets updated with the timeout value
        assert yaml.safe_load(config).get("datasources") == expected_source_data


def test_datasource_timeout_value_is_overridden_by_config_if_smaller(ctx, base_state, peer_relation):
    # GIVEN a datasource relation
    source_data = SOURCE_DATA.copy()
    # set relation data with timeout value smaller than default
    source_data["extra_fields"] = {"timeout": 200}  # type: ignore
    datasource_rel = Relation("grafana-source",
                            remote_app_name="prometheus",
                            remote_app_data={"grafana_source_data": json.dumps(source_data)},
                            remote_units_data={
                                0: {"grafana_source_host": "1.2.3.4:1234"},
                            },
                            )
    state = replace(base_state, relations={datasource_rel, peer_relation})
    # WHEN running a relation_changed event
    with ctx(ctx.on.relation_changed(datasource_rel), state) as mgr:
        mgr.run()
        charm = mgr.charm
        config = charm.unit.get_container("grafana").pull(DATASOURCES_PATH)
        expected_source_data = BASIC_DATASOURCES.copy()
        # THEN datasources config keep the default timeout value
        expected_source_data[0]["jsonData"]["timeout"] = 300
        assert yaml.safe_load(config).get("datasources") == expected_source_data

@mark.parametrize(
    "event",
    (
        CharmEvents.update_status(),
        CharmEvents.start(),
        CharmEvents.install(),
        CharmEvents.config_changed(),
    ),
)
def test_workload_version_is_set(ctx:Context, base_state, event):
    # GIVEN a running workload container
    # WHEN running any event
    out = ctx.run(event, base_state)
    # THEN we get the workload version set
    assert out.workload_version == "0.1.0"

@mark.parametrize(
    "event",
    (
        CharmEvents.update_status(),
        CharmEvents.start(),
        CharmEvents.install(),
        CharmEvents.config_changed(),
    ),
)
@patch.object(grafana_client.GrafanaClient, "build_info", new={"version": "1.0.0"})
def test_bare_charm_has_no_subpath_set_in_layer(ctx, base_state, event):
    # GIVEN a running workload container
    # WHEN running any event
    with ctx(event, base_state) as mgr:
        mgr.run()
        charm = mgr.charm
        # THEN in the grafana pebble layer, GF_SERVER_ROOT_URL is set
        pebble_layer = charm._grafana_service._layer
        assert pebble_layer.to_dict()["services"]["grafana"]["environment"]["GF_SERVER_ROOT_URL"] == "http://grafana-k8s-0.testmodel.svc.cluster.local:3000"

@patch.object(grafana_client.GrafanaClient, "build_info", new={"version": "1.0.0"})
@patch.multiple("charm.TraefikRouteRequirer", external_host="1.2.3.4", scheme="http")
def test_ingress_relation_sets_options_and_rel_data(ctx:Context, base_state, peer_relation):
    # GIVEN an ingress relation
    ingress_rel = Relation("ingress",
                            remote_app_name="traefik",
                              )
    state = replace(base_state, relations={ingress_rel, peer_relation}, model=Model(name="testmodel"))

    expected_rel_data = {
        "http": {
            "middlewares": {
                "juju-sidecar-noprefix-testmodel-grafana-k8s": {
                    "stripPrefix": {
                        "forceSlash": False,
                        "prefixes": ["/testmodel-grafana-k8s"],
                    }
                }
            },
            "routers": {
                "juju-testmodel-grafana-k8s-router": {
                    "entryPoints": ["web"],
                    "middlewares": ["juju-sidecar-noprefix-testmodel-grafana-k8s"],
                    "rule": "PathPrefix(`/testmodel-grafana-k8s`)",
                    "service": "juju-testmodel-grafana-k8s-service",
                },
                "juju-testmodel-grafana-k8s-router-tls": {
                    "entryPoints": ["websecure"],
                    "middlewares": ["juju-sidecar-noprefix-testmodel-grafana-k8s"],
                    "rule": "PathPrefix(`/testmodel-grafana-k8s`)",
                    "service": "juju-testmodel-grafana-k8s-service",
                    "tls": {"domains": [{"main": "1.2.3.4", "sans": ["*.1.2.3.4"]}]},
                },
            },
            "services": {
                "juju-testmodel-grafana-k8s-service": {
                    "loadBalancer": {
                        "servers": [
                            {"url": "http://grafana-k8s-0.testmodel.svc.cluster.local:3000"}
                        ]
                    }
                }
            },
        }
    }

    # WHEN relation_changed event is fired
    with ctx(ctx.on.relation_changed(ingress_rel), state) as mgr:
        out = mgr.run()
        charm = mgr.charm
        # THEN GF_SERVER_ROOT_URL & GF_SERVER_SERVE_FROM_SUB_PATH are set in the pebble layer
        plan = charm.unit.get_container("grafana").get_plan().services["grafana"].to_dict()
        assert "GF_SERVER_SERVE_FROM_SUB_PATH" in plan["environment"].keys()
        assert "GF_SERVER_ROOT_URL" in plan["environment"].keys()
        # AND traefik_route config is set in local app data
        rel_data = out.get_relation(ingress_rel.id).local_app_data
        assert yaml.safe_load(rel_data["config"]) == expected_rel_data
        assert charm.external_url == "http://1.2.3.4/testmodel-grafana-k8s"

def test_config_is_updated_with_authentication_config(ctx, base_state, peer_relation):
    # GIVEN a grafana-auth relation
    example_auth_conf = {
        "proxy": {
            "enabled": True,
            "header_name": "X-WEBAUTH-USER",
            "header_property": "email",
            "auto_sign_up": False,
            "sync_ttl": 10,
        }
    }
    auth_rel = Relation("grafana-auth", remote_app_name="auth_provider", remote_app_data={"auth": json.dumps(example_auth_conf)})

    state = replace(base_state, relations={auth_rel, peer_relation})
    # WHEN a relation_changed event is fired
    with ctx(ctx.on.relation_changed(auth_rel), state) as mgr:
        mgr.run()
        charm = mgr.charm
        # THEN auth env vars are set in the pebble layer
        plan = charm.unit.get_container("grafana").get_plan().services["grafana"].to_dict()
        assert "GF_AUTH_PROXY_ENABLED" in plan["environment"].keys()
        assert plan["environment"]["GF_AUTH_PROXY_ENABLED"] == "True"


@patch("socket.getfqdn", lambda: "1.2.3.4")
def test_primary_sets_correct_peer_data(ctx, base_state):
    # GIVEN a grafana app with 2 units
    state = replace(base_state, planned_units=2, networks={Network("grafana", bind_addresses=[BindAddress([Address("1.2.3.4")])])})
    # WHEN a config_changed event is fired on the leader unit
    with ctx(ctx.on.config_changed(), state) as mgr:
        mgr.run()
        charm = mgr.charm
        unit_binding = charm.model.get_binding("grafana")
        assert unit_binding
        unit_ip = str(unit_binding.network.bind_address)
        # THEN the leader unit set peer data replica_primary
        replica_address = charm.peers.get_peer_data("replica_primary")
        assert unit_ip == replica_address

@mark.parametrize(
    "event",
    (
        CharmEvents.update_status(),
        CharmEvents.start(),
        CharmEvents.install(),
        CharmEvents.config_changed(),
    ),
)
@patch("socket.getfqdn", lambda: "2.3.4.5")
def test_replicas_get_correct_environment_variables(ctx, base_state, event):
    # GIVEN a grafana app with 2 units
    updated_peer_relation = PeerRelation("grafana", local_app_data={"replica_primary": json.dumps("1.2.3.4")})
    state = replace(base_state, planned_units=2, leader=False, relations={updated_peer_relation})
    # WHEN any event is fired on the non-leader unit
    with ctx(event, state) as mgr:
        mgr.run()
        charm = mgr.charm
        # THEN LITESTREAM_UPSTREAM_URL gets set in litestream pebble service
        primary = charm._litestream.layer.to_dict()["services"]["litestream"][  # type: ignore
        "environment"
        ]["LITESTREAM_UPSTREAM_URL"]
        assert primary  == "1.2.3.4:9876"
