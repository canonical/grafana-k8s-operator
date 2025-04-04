# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import hashlib
import json
import unittest
from unittest.mock import patch

import ops
import yaml
from ops.testing import Harness

import src.grafana_client as grafana_client
from src.charm import CONFIG_PATH, DATASOURCES_PATH, PROVISIONING_PATH, GrafanaCharm

ops.testing.SIMULATE_CAN_CONNECT = True  # pyright: ignore

MINIMAL_CONFIG = {"grafana-image-path": "grafana/grafana", "port": 3000}

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


AUTH_PROVIDER_APPLICATION = "auth_provider"


def datasource_config(config):
    config_dict = yaml.safe_load(config)
    return config_dict


def dashboard_config(config):
    config_dict = yaml.safe_load(config)
    return config_dict


def global_config(config):
    config_dict = yaml.safe_load(config)
    return config_dict["global"]


def cli_arg(plan, cli_opt):
    plan_dict = plan.to_dict()
    args = plan_dict["services"]["grafana"]["command"].split()
    for arg in args:
        opt_list = arg.split("=")
        if len(opt_list) == 2 and opt_list[0] == cli_opt:
            return opt_list[1]
        if len(opt_list) == 1 and opt_list[0] == cli_opt:
            return opt_list[0]
    return None


k8s_resource_multipatch = patch.multiple(
    "charm.KubernetesComputeResourcesPatch",
    _namespace="test-namespace",
    _patch=lambda *a, **kw: True,
    is_ready=lambda *a, **kw: True,
)


class BaseTestCharm(unittest.TestCase):
    def setUp(self, *unused):
        self.harness = Harness(GrafanaCharm)
        self.harness.handle_exec("grafana", [], result=0)
        self.addCleanup(self.harness.cleanup)

        for p in [
            patch("lightkube.core.client.GenericSyncClient"),
            patch("socket.getfqdn", new=lambda *args: "grafana-k8s-0.testmodel.svc.cluster.local"),
            patch("socket.gethostbyname", new=lambda *args: "1.2.3.4"),
            k8s_resource_multipatch,
            patch.object(GrafanaCharm, "grafana_version", "0.1.0"),
        ]:
            p.start()
            self.addCleanup(p.stop)

        self.harness.set_model_name("testmodel")
        self.harness.add_relation("grafana", "grafana-k8s")

        self.grafana_auth_rel_id = self.harness.add_relation(
            "grafana-auth", AUTH_PROVIDER_APPLICATION
        )

        self.harness.begin_with_initial_hooks()
        self.harness.container_pebble_ready("grafana")

        self.minimal_datasource_hash = hashlib.sha256(
            str(yaml.dump(MINIMAL_DATASOURCES_CONFIG)).encode("utf-8")
        ).hexdigest()


class TestCharm(BaseTestCharm):
    def test_datasource_config_is_updated_by_raw_grafana_source_relation(self):
        self.harness.set_leader(True)

        # check datasource config is updated when a grafana-source joins
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:1234"}
        )

        config = self.harness.charm.containers["workload"].pull(DATASOURCES_PATH)
        self.assertEqual(yaml.safe_load(config).get("datasources"), BASIC_DATASOURCES)

    def test_datasource_config_is_updated_by_grafana_source_removal(self):
        self.harness.set_leader(True)

        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:1234"}
        )

        config = self.harness.charm.containers["workload"].pull(DATASOURCES_PATH)
        self.assertEqual(yaml.safe_load(config).get("datasources"), BASIC_DATASOURCES)

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)  # type: ignore
        self.harness.charm.on["grafana-source"].relation_departed.emit(rel)

        config = yaml.safe_load(self.harness.charm.containers["workload"].pull(DATASOURCES_PATH))
        self.assertEqual(config.get("datasources"), [])
        self.assertEqual(
            config.get("deleteDatasources"),
            [{"name": "juju_test-model_abcdef_prometheus_0", "orgId": 1}],
        )

    def test_config_is_updated_with_database_relation(self):
        self.harness.set_leader(True)

        rel_id = self.harness.add_relation("database", "mysql")
        self.harness.add_relation_unit(rel_id, "mysql/0")
        self.harness.update_relation_data(
            rel_id,
            "mysql",
            DB_CONFIG,
        )

        config = self.harness.charm.containers["workload"].pull(CONFIG_PATH)
        self.assertEqual(config.read(), DATABASE_CONFIG_INI)

    def test_dashboard_path_is_initialized(self):
        self.harness.set_leader(True)

        self.harness.charm.init_dashboard_provisioning(PROVISIONING_PATH + "/dashboards")

        dashboards_dir_path = PROVISIONING_PATH + "/dashboards/default.yaml"
        config = self.harness.charm.containers["workload"].pull(dashboards_dir_path)
        self.assertEqual(yaml.safe_load(config), DASHBOARD_CONFIG)

    def test_datasource_timeout_value_overrides_config_if_larger(self):
        self.harness.set_leader(True)

        # set relation data with timeout value larger than default
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        source_data = SOURCE_DATA.copy()
        source_data["extra_fields"] = {"timeout": 600}  # type: ignore
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(source_data)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:1234"}
        )

        config = self.harness.charm.containers["workload"].pull(DATASOURCES_PATH)
        expected_source_data = BASIC_DATASOURCES.copy()
        expected_source_data[0]["jsonData"]["timeout"] = 600
        self.assertEqual(yaml.safe_load(config).get("datasources"), expected_source_data)

    def test_datasource_timeout_value_is_overridden_by_config_if_smaller(self):
        self.harness.set_leader(True)

        # set relation data with timeout value smaller than default
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        source_data = SOURCE_DATA.copy()
        source_data["extra_fields"] = {"timeout": 200}  # type: ignore
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(source_data)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:1234"}
        )

        config = self.harness.charm.containers["workload"].pull(DATASOURCES_PATH)
        expected_source_data = BASIC_DATASOURCES.copy()
        expected_source_data[0]["jsonData"]["timeout"] = 300
        self.assertEqual(yaml.safe_load(config).get("datasources"), expected_source_data)

    def test_workload_version_is_set(self):
        self.harness.container_pebble_ready("grafana")
        self.assertEqual(self.harness.get_workload_version(), "0.1.0")

    @patch.object(grafana_client.Grafana, "build_info", new={"version": "1.0.0"})
    def test_bare_charm_has_no_subpath_set_in_layer(self):
        self.harness.set_leader(True)
        layer = self.harness.charm._build_layer()
        self.assertEqual(
            layer.to_dict()["services"]["grafana"]["environment"]["GF_SERVER_ROOT_URL"],  # type: ignore
            "http://grafana-k8s-0.testmodel.svc.cluster.local:3000",
        )

    @patch.object(grafana_client.Grafana, "build_info", new={"version": "1.0.0"})
    @patch.multiple("charm.TraefikRouteRequirer", external_host="1.2.3.4", scheme="http")
    def test_ingress_relation_sets_options_and_rel_data(self):
        self.harness.set_leader(True)
        self.harness.container_pebble_ready("grafana")
        rel_id = self.harness.add_relation("ingress", "traefik")
        self.harness.add_relation_unit(rel_id, "traefik/0")

        services = (
            self.harness.charm.containers["workload"].get_plan().services["grafana"].to_dict()
        )
        self.assertIn("GF_SERVER_SERVE_FROM_SUB_PATH", services["environment"].keys())  # type: ignore
        self.assertIn("GF_SERVER_ROOT_URL", services["environment"].keys())  # type: ignore

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
        rel_data = self.harness.get_relation_data(rel_id, self.harness.charm.app.name)

        # The insanity of YAML here. It works for the lib, but a single load just strips off
        # the extra quoting and leaves regular YAML. Double parse it for the tests
        self.maxDiff = None
        self.assertEqual(yaml.safe_load(rel_data["config"]), expected_rel_data)

        self.assertEqual(self.harness.charm.external_url, "http://1.2.3.4/testmodel-grafana-k8s")

    def test_config_is_updated_with_authentication_config(self):
        self.harness.set_leader(True)
        self.harness.container_pebble_ready("grafana")
        example_auth_conf = {
            "proxy": {
                "enabled": True,
                "header_name": "X-WEBAUTH-USER",
                "header_property": "email",
                "auto_sign_up": False,
                "sync_ttl": 10,
            }
        }
        self.harness.update_relation_data(
            self.grafana_auth_rel_id,
            AUTH_PROVIDER_APPLICATION,
            {"auth": json.dumps(example_auth_conf)},
        )
        services = (
            self.harness.charm.containers["workload"].get_plan().services["grafana"].to_dict()
        )
        self.assertIn("GF_AUTH_PROXY_ENABLED", services["environment"].keys())  # type: ignore
        self.assertEqual(services["environment"]["GF_AUTH_PROXY_ENABLED"], "True")  # type: ignore


class TestCharmReplication(unittest.TestCase):
    def setUp(self, *unused):
        self.harness = Harness(GrafanaCharm)
        self.harness.handle_exec("grafana", [], result=0)
        self.addCleanup(self.harness.cleanup)

        for p in [
            patch("lightkube.core.client.GenericSyncClient"),
            k8s_resource_multipatch,
            patch.object(GrafanaCharm, "grafana_version", "0.1.0"),
        ]:
            p.start()
            self.addCleanup(p.stop)

        self.harness.add_relation("grafana-auth", AUTH_PROVIDER_APPLICATION)
        self.harness.add_relation("grafana", "grafana-k8s")
        self.harness.set_leader(True)

        self.minimal_datasource_hash = hashlib.sha256(
            str(yaml.dump(MINIMAL_DATASOURCES_CONFIG)).encode("utf-8")
        ).hexdigest()

    @patch("socket.getfqdn", lambda: "1.2.3.4")
    def test_primary_sets_correct_peer_data(self):
        self.harness.begin_with_initial_hooks()
        self.harness.container_pebble_ready("grafana")
        self.harness.container_pebble_ready("litestream")

        self.harness.charm.on.config_changed.emit()
        rel = self.harness.model.get_relation("grafana")
        assert rel
        self.harness.add_relation_unit(rel.id, "grafana-k8s/1")

        self.harness.add_network("1.2.3.4", endpoint="grafana")
        unit_binding = self.harness.charm.model.get_binding("grafana")
        assert unit_binding
        unit_ip = str(unit_binding.network.bind_address)
        replica_address = self.harness.charm.get_peer_data("replica_primary")

        self.assertEqual(unit_ip, replica_address)

    @patch("socket.getfqdn", lambda: "2.3.4.5")
    def test_replicas_get_correct_environment_variables(self):
        self.harness.begin_with_initial_hooks()
        self.harness.container_pebble_ready("grafana")
        self.harness.container_pebble_ready("litestream")

        rel = self.harness.model.get_relation("grafana")
        assert rel
        self.harness.add_relation_unit(rel.id, "grafana-k8s/1")
        self.harness.update_relation_data(
            rel.id, "grafana-k8s", {"replica_primary": json.dumps("1.2.3.4")}
        )
        primary = self.harness.charm._build_replication(False).to_dict()["services"]["litestream"][  # type: ignore
            "environment"
        ]["LITESTREAM_UPSTREAM_URL"]

        self.assertEqual(primary, "1.2.3.4:9876")
