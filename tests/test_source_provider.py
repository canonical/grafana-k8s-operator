# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from unittest.mock import patch

from charms.grafana_k8s.v0.grafana_source import GrafanaSourceProvider
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness

SOURCE_DATA = {
    "model": "test-model",
    "model_uuid": "abcdef",
    "application": "prometheus",
    "type": "prometheus",
}

CONSUMER_META = """
name: provider-tester
containers:
  grafana-tester:
provides:
  grafana-source:
    interface: grafana_datasource
"""


class ProviderCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaSourceProvider(
            self,
            refresh_event=self.on.grafana_tester_pebble_ready,
        )


class TestSourceProvider(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(ProviderCharm, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    @patch("ops.testing._TestingModelBackend.network_get")
    def test_provider_sets_scrape_data(self, _):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertIn("grafana_source_data", data)
        scrape_data = data["grafana_source_data"]
        self.assertIn("model", scrape_data)
        self.assertIn("model_uuid", scrape_data)
        self.assertIn("application", scrape_data)

    @patch("ops.testing._TestingModelBackend.network_get")
    def test_provider_unit_sets_bind_address_on_pebble_ready(self, mock_net_get):
        bind_address = "1.2.3.4"
        fake_network = {
            "bind-addresses": [
                {
                    "interface-name": "eth0",
                    "addresses": [{"hostname": "grafana-tester-0", "value": bind_address}],
                }
            ]
        }
        mock_net_get.return_value = fake_network
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.container_pebble_ready("grafana-tester")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertIn("grafana_source_host", data)
        self.assertEqual(data["grafana_source_host"], f"{bind_address}:9090")

    @patch("ops.testing._TestingModelBackend.network_get")
    def test_provider_unit_sets_bind_address_on_relation_joined(self, mock_net_get):
        bind_address = "1.2.3.4"
        fake_network = {
            "bind-addresses": [
                {
                    "interface-name": "eth0",
                    "addresses": [{"hostname": "grafana-tester-0", "value": bind_address}],
                }
            ]
        }
        mock_net_get.return_value = fake_network
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertIn("grafana_source_host", data)
        self.assertEqual(data["grafana_source_host"], f"{bind_address}:9090")
