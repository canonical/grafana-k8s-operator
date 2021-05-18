# Copyright 2020 Ryan Barry
# See LICENSE file for licensing details.

import hashlib
import unittest
import yaml
import json

from unittest.mock import patch
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
        "isDefault": "true",
        "name": "prometheus_0",
        "orgId": "1",
        "type": "prometheus",
        "url": "http://1.1.1.1:1234",
    }
]


def datasource_config(config):
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

        self.minimal_datasource_hash = hashlib.md5(
            str(yaml.dump(MINIMAL_DATASOURCES_CONFIG)).encode("utf-8")
        ).hexdigest()

    @patch("ops.testing._TestingPebbleClient.push")
    def test_datasource_config_is_updated_by_grafana_source_relation(self, push):
        self.harness.set_leader(True)

        # check datasource config is empty without relation
        self.harness.update_config(MINIMAL_CONFIG)
        self.assertEqual(
            self.harness.charm._stored.grafana_datasources_hash,
            self.minimal_datasource_hash,
        )

        # check datasource config is updated when a grafana-source joins
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        source_data = {
            "private-address": "1.1.1.1",
            "port": 1234,
            "source-type": "prometheus",
            "source-name": "prometheus_0",
        }
        self.harness.update_relation_data(
            rel_id, "prometheus", {"sources": json.dumps(source_data)}
        )

        config = push.call_args[0]
        self.assertEqual(
            datasource_config(config).get("datasources"), BASIC_DATASOURCES
        )

    @patch("ops.testing._TestingPebbleClient.push")
    def test_datasource_config_is_updated_by_grafana_source_removal(self, push):
        self.harness.set_leader(True)

        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        source_data = {
            "private-address": "1.1.1.1",
            "port": 1234,
            "source-type": "prometheus",
            "source-name": "prometheus_0",
        }
        self.harness.update_relation_data(
            rel_id, "prometheus", {"sources": json.dumps(source_data)}
        )

        config = push.call_args[0]
        self.assertEqual(
            datasource_config(config).get("datasources"), BASIC_DATASOURCES
        )

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)
        self.harness.charm.on["grafana-source"].relation_broken.emit(rel)

        config = push.call_args[0]
        self.assertEqual(datasource_config(config).get("datasources"), [])
        self.assertEqual(
            datasource_config(config).get("deleteDatasources"),
            [{"name": "prometheus_0", "orgId": 1}],
        )
