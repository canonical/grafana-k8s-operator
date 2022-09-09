# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import hashlib
import json
import re
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

import yaml
from helpers import FakeProcessVersionCheck
from ops.model import Container
from ops.testing import Harness

from charm import CONFIG_PATH, DATASOURCES_PATH, PROVISIONING_PATH, GrafanaCharm

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


class TestCharm(unittest.TestCase):
    @k8s_resource_multipatch
    @patch("lightkube.core.client.GenericSyncClient")
    def setUp(self, *unused):
        patch_exec = patch("ops.testing._TestingPebbleClient.exec", MagicMock())
        self.patch_exec = patch_exec.start()
        self.harness = Harness(GrafanaCharm)
        self.addCleanup(self.harness.cleanup)
        self.addCleanup(self.patch_exec)
        self.harness.begin()
        self.grafana_auth_rel_id = self.harness.add_relation(
            "grafana-auth", AUTH_PROVIDER_APPLICATION
        )
        self.harness.add_relation("grafana", "grafana-k8s")

        self.minimal_datasource_hash = hashlib.sha256(
            str(yaml.dump(MINIMAL_DATASOURCES_CONFIG)).encode("utf-8")
        ).hexdigest()

    @k8s_resource_multipatch
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

    @k8s_resource_multipatch
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

    @k8s_resource_multipatch
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

    def test_can_get_password(self):
        self.harness.set_leader(True)

        # Harness doesn't quite support actions yet...
        self.assertTrue(re.match(r"[A-Za-z0-9]{12}", self.harness.charm._get_admin_password()))

    @patch("grafana_server.Grafana.is_ready", new_callable=PropertyMock)
    def test_sane_message_for_password_when_grafana_down(self, mock_ready):
        mock_ready.return_value = False
        event = MagicMock()
        self.harness.charm._on_get_admin_password(event)
        event.fail.assert_called_with(
            "Grafana is not reachable yet. Please try again in a few minutes"
        )

    @patch("grafana_server.Grafana.password_has_been_changed")
    @patch("grafana_server.Grafana.is_ready", new_callable=PropertyMock)
    def test_returns_password_changed_message(self, mock_ready, mock_pw_changed):
        mock_ready.return_value = True
        mock_pw_changed.return_value = True
        event = MagicMock()
        self.harness.charm._on_get_admin_password(event)
        event.set_results.assert_called_with(
            {"admin-password": "Admin password has been changed by an administrator"}
        )

    @k8s_resource_multipatch
    def test_config_is_updated_with_subpath(self):
        self.harness.set_leader(True)

        self.harness.update_config({"web_external_url": "/grafana"})

        services = (
            self.harness.charm.containers["workload"].get_plan().services["grafana"].to_dict()
        )
        self.assertIn("GF_SERVER_SERVE_FROM_SUB_PATH", services["environment"].keys())
        self.assertTrue(services["environment"]["GF_SERVER_ROOT_URL"].endswith("/grafana"))

    @k8s_resource_multipatch
    def test_datasource_timeout_value_overrides_config_if_larger(self):
        self.harness.set_leader(True)

        # set relation data with timeout value larger than default
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        source_data = SOURCE_DATA.copy()
        source_data["extra_fields"] = {"timeout": 600}
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

    @k8s_resource_multipatch
    def test_datasource_timeout_value_is_overridden_by_config_if_smaller(self):
        self.harness.set_leader(True)

        # set relation data with timeout value smaller than default
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        source_data = SOURCE_DATA.copy()
        source_data["extra_fields"] = {"timeout": 200}
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

    @k8s_resource_multipatch
    @patch.object(Container, "exec", new=FakeProcessVersionCheck)
    def test_workload_version_is_set(self):
        self.harness.container_pebble_ready("grafana")
        self.assertEqual(self.harness.get_workload_version(), "0.1.0")

    @k8s_resource_multipatch
    def test_config_is_updated_with_authentication_config(self):
        self.harness.set_leader(True)
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
        self.assertIn("GF_AUTH_PROXY_ENABLED", services["environment"].keys())
        self.assertEquals(services["environment"]["GF_AUTH_PROXY_ENABLED"], "True")


class TestCharmReplication(unittest.TestCase):
    @k8s_resource_multipatch
    @patch("lightkube.core.client.GenericSyncClient")
    def setUp(self, *unused):
        patch_exec = patch("ops.testing._TestingPebbleClient.exec", MagicMock())
        self.patch_exec = patch_exec.start()
        self.harness = Harness(GrafanaCharm)
        self.addCleanup(self.harness.cleanup)
        self.addCleanup(self.patch_exec)
        self.harness.add_relation("grafana-auth", AUTH_PROVIDER_APPLICATION)
        self.harness.add_relation("grafana", "grafana-k8s")
        self.harness.set_leader(True)
        self.harness.begin()

        self.minimal_datasource_hash = hashlib.sha256(
            str(yaml.dump(MINIMAL_DATASOURCES_CONFIG)).encode("utf-8")
        ).hexdigest()

    @patch("socket.getfqdn", lambda: "1.2.3.4")
    @patch("ops.testing._TestingModelBackend.network_get")
    def test_primary_sets_correct_peer_data(self, mock_unit_ip):
        fake_network = {
            "bind-addresses": [
                {
                    "interface-name": "eth0",
                    "addresses": [{"hostname": "grafana-0", "value": "1.2.3.4"}],
                }
            ]
        }
        mock_unit_ip.return_value = fake_network
        self.harness.set_leader(True)
        self.harness.charm.on.config_changed.emit()
        rel = self.harness.model.get_relation("grafana")
        self.harness.add_relation_unit(rel.id, "grafana-k8s/1")

        unit_ip = str(self.harness.charm.model.get_binding("grafana").network.bind_address)
        replica_address = self.harness.charm.get_peer_data("replica_primary")

        self.assertEqual(unit_ip, replica_address)

    @patch("socket.getfqdn", lambda: "2.3.4.5")
    @patch("ops.testing._TestingModelBackend.network_get")
    def test_replicas_get_correct_environment_variables(self, mock_unit_ip):
        fake_network = {
            "bind-addresses": [
                {
                    "interface-name": "eth0",
                    "addresses": [{"hostname": "grafana-0", "value": "2.3.4.5"}],
                }
            ]
        }
        mock_unit_ip.return_value = fake_network
        self.harness.set_leader(False)
        rel = self.harness.model.get_relation("grafana")
        self.harness.add_relation_unit(rel.id, "grafana-k8s/1")
        self.harness.update_relation_data(
            rel.id, "grafana-k8s", {"replica_primary": json.dumps("1.2.3.4")}
        )
        primary = self.harness.charm._build_replication(False).to_dict()["services"]["litestream"][
            "environment"
        ]["LITESTREAM_UPSTREAM_URL"]

        self.assertEqual(primary, "1.2.3.4:9876")
