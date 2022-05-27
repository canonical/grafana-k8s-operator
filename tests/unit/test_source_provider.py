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
            source_type="foobar",
            source_port="9090",
            refresh_event=self.on.grafana_tester_pebble_ready,
        )


class TestSourceProvider(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(ProviderCharm, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    def test_provider_sets_scrape_data(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertIn("grafana_source_data", data)
        scrape_data = data["grafana_source_data"]
        self.assertIn("model", scrape_data)
        self.assertIn("model_uuid", scrape_data)
        self.assertIn("application", scrape_data)

    @patch("socket.getfqdn", new=lambda *args: "fqdn1")
    def test_provider_unit_sets_address_on_pebble_ready(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.container_pebble_ready("grafana-tester")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertIn("grafana_source_host", data)
        self.assertEqual(data["grafana_source_host"], "fqdn1:9090")

    @patch("socket.getfqdn", new=lambda *args: "fqdn2")
    def test_provider_unit_sets_address_on_relation_joined(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertIn("grafana_source_host", data)
        self.assertEqual(data["grafana_source_host"], "fqdn2:9090")


class ProviderCharmWithIngress(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = None


class TestSourceProviderWithIngress(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(ProviderCharmWithIngress, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    def test_provider_unit_sets_source_uri_if_provided(self):
        self.harness.charm.provider = GrafanaSourceProvider(
            self.harness.charm,
            source_type="foobar",
            source_url="http://1.2.3.4/v1",
            refresh_event=self.harness.charm.on.grafana_tester_pebble_ready,
        )
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertIn("grafana_source_host", data)
        self.assertEqual(data["grafana_source_host"], "http://1.2.3.4/v1")

    def test_provider_unit_sets_scheme_if_not_provided(self):
        self.harness.charm.provider = GrafanaSourceProvider(
            self.harness.charm,
            source_type="foobar",
            source_url="1.2.3.4/v1",
            refresh_event=self.harness.charm.on.grafana_tester_pebble_ready,
        )
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertIn("grafana_source_host", data)
        self.assertEqual(data["grafana_source_host"], "http://1.2.3.4/v1")


class ProviderCharmNoRefreshEvent(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaSourceProvider(self, source_type="foobar")

        self._stored.set_default(valid_events=0)  # available data sources
        self._stored.set_default(invalid_events=0)


class TestDashboardProviderNoRefreshEvent(unittest.TestCase):
    def test_provider_instantiates_correctly(self):
        self.harness = Harness(ProviderCharmNoRefreshEvent, meta=CONSUMER_META)
        self.harness.begin_with_initial_hooks()

        self.harness.container_pebble_ready("grafana-tester")
