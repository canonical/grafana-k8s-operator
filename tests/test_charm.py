# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import hashlib
import json
import unittest
from unittest.mock import patch

import yaml
from ops.testing import Harness

from charm import GrafanaCharm

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
            "options": {"path": "dashboards"},
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
    config_yaml = config[1]
    config_dict = yaml.safe_load(config_yaml)
    return config_dict


def dashboard_config(config):
    config_yaml = config[1]
    config_dict = yaml.safe_load(config_yaml)
    return config_dict


def global_config(config):
    config_yaml = config[1]
    config_dict = yaml.safe_load(config_yaml)
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

        self.minimal_datasource_hash = hashlib.sha256(
            str(yaml.dump(MINIMAL_DATASOURCES_CONFIG)).encode("utf-8")
        ).hexdigest()

    @patch("ops.testing._TestingPebbleClient.push")
    def test_datasource_config_is_updated_by_raw_grafana_source_relation(self, push):
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

        config = push.call_args[0]
        self.assertEqual(datasource_config(config).get("datasources"), BASIC_DATASOURCES)

    @patch("ops.testing._TestingPebbleClient.push")
    def test_datasource_config_is_updated_by_grafana_source_removal(self, push):
        self.harness.set_leader(True)

        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:1234"}
        )

        config = push.call_args[0]
        self.assertEqual(datasource_config(config).get("datasources"), BASIC_DATASOURCES)

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)  # type: ignore[arg-type]
        self.harness.charm.on["grafana-source"].relation_departed.emit(rel)

        config = push.call_args[0]
        self.assertEqual(datasource_config(config).get("datasources"), [])
        self.assertEqual(
            datasource_config(config).get("deleteDatasources"),
            [{"name": "juju_test-model_abcdef_prometheus_0", "orgId": 1}],
        )

    @patch("ops.testing._TestingPebbleClient.push")
    def test_config_is_updated_with_database_relation(self, push):
        self.harness.set_leader(True)

        rel_id = self.harness.add_relation("database", "mysql")
        self.harness.add_relation_unit(rel_id, "mysql/0")
        self.harness.update_relation_data(
            rel_id,
            "mysql",
            DB_CONFIG,
        )

        config = push.call_args_list[0][0][1]
        self.assertEqual(config, DATABASE_CONFIG_INI)

    @patch("ops.testing._TestingPebbleClient.push")
    def test_dashboard_path_is_initialized(self, push):
        self.harness.set_leader(True)

        self.harness.charm.init_dashboard_provisioning("dashboards")

        config = push.call_args[0]
        self.assertEqual(dashboard_config(config), DASHBOARD_CONFIG)
