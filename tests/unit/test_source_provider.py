# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
from unittest.mock import patch

from charms.grafana_k8s.v1.grafana_source import GrafanaSourceProvider
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
    """Defaults: app_datasource=True, unit_datasources=False."""

    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaSourceProvider(
            self,
            source_type="foobar",
            source_port="9090",
            refresh_event=self.on.grafana_tester_pebble_ready,
        )


class UnitProviderCharm(CharmBase):
    """Per-unit datasources only."""

    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaSourceProvider(
            self,
            source_type="foobar",
            source_port="9090",
            app_datasource=False,
            unit_datasources=True,
            refresh_event=self.on.grafana_tester_pebble_ready,
        )


class BothModesProviderCharm(CharmBase):
    """Both app-level and per-unit datasources."""

    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaSourceProvider(
            self,
            source_type="foobar",
            source_port="9090",
            app_datasource=True,
            unit_datasources=True,
            refresh_event=self.on.grafana_tester_pebble_ready,
        )


class NoDatasourceProviderCharm(CharmBase):
    """Neither app-level nor per-unit datasources."""

    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaSourceProvider(
            self,
            source_type="foobar",
            source_port="9090",
            app_datasource=False,
            unit_datasources=False,
            refresh_event=self.on.grafana_tester_pebble_ready,
        )


class AlertManagerProviderCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaSourceProvider(
            self,
            source_type="alertmanager",
            source_port="9093",
            refresh_event=self.on.grafana_tester_pebble_ready,
        )


class MimirProviderCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaSourceProvider(
            self,
            source_type="mimir",
            source_port="9009",
            app_datasource=True,
            unit_datasources=True,
            refresh_event=self.on.grafana_tester_pebble_ready,
        )


class TestAppDatasourceProvider(unittest.TestCase):
    """Default mode: a single, load-balanced application-level datasource."""

    def setUp(self):
        self.harness = Harness(ProviderCharm, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    def _expected_app_host(self, port="9090", suffix=""):
        app = self.harness.model.app.name
        model = self.harness.model.name
        return "http://{}.{}.svc.cluster.local:{}{}".format(app, model, port, suffix)

    def test_provider_sets_scrape_data(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertIn("grafana_source_data", data)
        scrape_data = data["grafana_source_data"]
        self.assertIn("model", scrape_data)
        self.assertIn("model_uuid", scrape_data)
        self.assertIn("application", scrape_data)

    def test_leader_publishes_app_host_in_app_databag(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        app_data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertEqual(app_data["grafana_source_app_host"], self._expected_app_host())

    def test_unit_databag_host_is_empty_in_app_mode(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        unit_data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertEqual(unit_data.get("grafana_source_host", ""), "")

    def test_app_host_refreshed_on_pebble_ready(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.container_pebble_ready("grafana-tester")
        self.harness.add_relation_unit(rel_id, "provider/0")
        app_data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertEqual(app_data["grafana_source_app_host"], self._expected_app_host())

    def test_app_datasource_url_override(self):
        self.harness.charm.provider.update_app_source("http://1.2.3.4/v1")
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        app_data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertEqual(app_data["grafana_source_app_host"], "http://1.2.3.4/v1")


class TestNonLeaderAppDatasourceProvider(unittest.TestCase):
    """Followers must never write to the application databag."""

    def setUp(self):
        self.harness = Harness(ProviderCharm, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        # no leadership!
        self.harness.begin()

    def test_follower_does_not_publish_app_host(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        app_data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertNotIn("grafana_source_app_host", app_data)


class TestUnitDatasourceProvider(unittest.TestCase):
    """Per-unit datasources: each unit advertises its own address."""

    def setUp(self):
        self.harness = Harness(UnitProviderCharm, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    @patch("socket.getfqdn", new=lambda *args: "fqdn1")
    def test_unit_sets_address_on_relation_joined(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        unit_data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertEqual(unit_data["grafana_source_host"], "http://fqdn1:9090")

    @patch("socket.getfqdn", new=lambda *args: "fqdn2")
    def test_unit_sets_address_on_pebble_ready(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.container_pebble_ready("grafana-tester")
        self.harness.add_relation_unit(rel_id, "provider/0")
        unit_data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertEqual(unit_data["grafana_source_host"], "http://fqdn2:9090")

    def test_app_databag_host_is_empty_in_unit_mode(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        app_data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertEqual(app_data.get("grafana_source_app_host", ""), "")

    def test_unit_datasource_url_override(self):
        self.harness.charm.provider.update_unit_source("http://1.2.3.4/v1")
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        unit_data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertEqual(unit_data["grafana_source_host"], "http://1.2.3.4/v1")

    def test_unit_datasource_url_scheme_added_if_missing(self):
        self.harness.charm.provider.update_unit_source("1.2.3.4/v1")
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        unit_data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertEqual(unit_data["grafana_source_host"], "http://1.2.3.4/v1")


class TestBothModesProvider(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(BothModesProviderCharm, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    @patch("socket.getfqdn", new=lambda *args: "fqdn")
    def test_both_app_and_unit_hosts_published(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        app_data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        unit_data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        app = self.harness.model.app.name
        model = self.harness.model.name
        self.assertEqual(
            app_data["grafana_source_app_host"],
            "http://{}.{}.svc.cluster.local:9090".format(app, model),
        )
        self.assertEqual(unit_data["grafana_source_host"], "http://fqdn:9090")


class TestNoDatasourceProvider(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(NoDatasourceProviderCharm, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)

    def test_warns_when_both_modes_disabled(self):
        with self.assertLogs(
            "charms.grafana_k8s.v1.grafana_source", level="WARNING"
        ) as cm:
            self.harness.begin()
        self.assertTrue(any("No datasource address will be published" in m for m in cm.output))

    def test_publishes_no_host_when_both_modes_disabled(self):
        self.harness.begin()
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        app_data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        unit_data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertEqual(app_data.get("grafana_source_app_host", ""), "")
        self.assertEqual(unit_data.get("grafana_source_host", ""), "")


class TestAlertManagerProvider(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(AlertManagerProviderCharm, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    def test_provider_sets_scrape_data(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertIn("grafana_source_data", data)
        scrape_data = json.loads(data["grafana_source_data"])
        self.assertIn("model", scrape_data)
        self.assertIn("model_uuid", scrape_data)
        self.assertIn("application", scrape_data)
        self.assertEqual(scrape_data["extra_fields"], {"implementation": "prometheus"})


class TestMimirProvider(unittest.TestCase):
    """The `/prometheus` suffix must be applied to BOTH the app and unit URLs."""

    def setUp(self):
        self.harness = Harness(MimirProviderCharm, meta=CONSUMER_META)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    @patch("socket.getfqdn", new=lambda *args: "mimir")
    def test_prometheus_suffix_applied_to_unit_url(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        unit_data = self.harness.get_relation_data(rel_id, self.harness.charm.unit.name)
        self.assertEqual(unit_data["grafana_source_host"], "http://mimir:9009/prometheus")

    @patch("socket.getfqdn", new=lambda *args: "mimir")
    def test_prometheus_suffix_applied_to_app_url(self):
        rel_id = self.harness.add_relation("grafana-source", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        app_data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        app = self.harness.model.app.name
        model = self.harness.model.name
        self.assertEqual(
            app_data["grafana_source_app_host"],
            "http://{}.{}.svc.cluster.local:9009/prometheus".format(app, model),
        )


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
