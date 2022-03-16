# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import configparser
import hashlib
import json
import re
import unittest

import yaml
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


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(GrafanaCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.harness.add_relation("grafana", "grafana")

        self.minimal_datasource_hash = hashlib.sha256(
            str(yaml.dump(MINIMAL_DATASOURCES_CONFIG)).encode("utf-8")
        ).hexdigest()

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

        config = self.harness.charm.container.pull(DATASOURCES_PATH)
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

        config = self.harness.charm.container.pull(DATASOURCES_PATH)
        self.assertEqual(yaml.safe_load(config).get("datasources"), BASIC_DATASOURCES)

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)  # type: ignore
        self.harness.charm.on["grafana-source"].relation_departed.emit(rel)

        config = yaml.safe_load(self.harness.charm.container.pull(DATASOURCES_PATH))
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

        config = self.harness.charm.container.pull(CONFIG_PATH)
        self.assertEqual(config.read(), DATABASE_CONFIG_INI)

    def test_dashboard_path_is_initialized(self):
        self.harness.set_leader(True)

        self.harness.charm.init_dashboard_provisioning(PROVISIONING_PATH + "/dashboards")

        dashboards_dir_path = PROVISIONING_PATH + "/dashboards/default.yaml"
        config = self.harness.charm.container.pull(dashboards_dir_path)
        self.assertEqual(yaml.safe_load(config), DASHBOARD_CONFIG)

    def can_get_password(self):
        self.harness.set_leader(True)

        # Harness doesn't quite support actions yet...
        self.assertTrue(re.match(r"[A-Za-z0-9]{12}", self.harness.charm._get_admin_password()))

    def test_config_is_updated_with_subpath(self):
        self.harness.set_leader(True)

        self.harness.update_config({"web_external_url": "/grafana"})

        services = self.harness.charm.container.get_plan().services["grafana"].to_dict()
        self.assertIn("GF_SERVER_SERVE_FROM_SUB_PATH", services["environment"].keys())
        self.assertTrue(services["environment"]["GF_SERVER_ROOT_URL"].endswith("/grafana"))

    def test_given_no_config_when_update_config_then_grafana_config_file_is_empty(self):
        self.harness.set_leader(True)

        self.harness.update_config()

        config = self.harness.charm.container.pull(CONFIG_PATH)
        config_parser = configparser.ConfigParser()
        config_parser.read_file(config)  # type: ignore[arg-type]
        assert len(config_parser.sections()) == 0

    def test_given_auth_proxy_config_is_enabled_when_update_config_then_grafana_config_file_contains_auth_proxy_data(
        self,
    ):
        self.harness.set_leader(True)

        self.harness.update_config({"enable_auth_proxy": True})  # type: ignore[dict-item]

        config = self.harness.charm.container.pull(CONFIG_PATH)
        config_parser = configparser.ConfigParser()
        config_parser.read_file(config)  # type: ignore[arg-type]
        assert "auth.proxy" in config_parser
        assert config_parser["auth.proxy"]["enabled"] == "true"
        assert config_parser["auth.proxy"]["header_name"] == "X-WEBAUTH-USER"
        assert config_parser["auth.proxy"]["header_property"] == "username"
        assert config_parser["auth.proxy"]["auto_sign_up"] == "false"

    def test_given_auth_proxy_config_is_disabled_when_update_config_then_grafana_config_file_doesnt_contain_auth_proxy_data(
        self,
    ):
        self.harness.set_leader(True)

        self.harness.update_config({"enable_auth_proxy": False})  # type: ignore[dict-item]

        config = self.harness.charm.container.pull(CONFIG_PATH)
        config_parser = configparser.ConfigParser()
        config_parser.read_file(config)  # type: ignore[arg-type]
        assert "auth.proxy" not in config_parser
