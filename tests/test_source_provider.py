# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import pytest
import unittest

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness
from lib.charms.grafana_k8s.v1.grafana_source import (
    GrafanaSourceProvider,
)


class GrafanaCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._stored.set_default(source_events=0)  # available data sources
        self._stored.set_default(source_delete_events=0)

        self.grafana_provider = GrafanaSourceProvider(
            self, "grafana-source", "grafana", self.version
        )
        self.framework.observe(
            self.grafana_provider.on.sources_changed, self.source_events
        )
        self.framework.observe(
            self.grafana_provider.on.sources_to_delete_changed,
            self.source_delete_events,
        )

    def source_events(self, _):
        self._stored.source_events += 1

    def source_delete_events(self, _):
        self._stored.source_delete_events += 1

    @property
    def version(self):
        return "2.0.0"


class TestProvider(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def setUp(self):
        self.harness = Harness(GrafanaCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    def test_provider_notifies_on_new_sources(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        source_data = {
            "address": "1.1.1.1",
            "port": 1234,
            "source-type": "prometheus",
            "source-name": f"prometheus_{rel_id}",
            "isDefault": "true",
        }
        self.harness.update_relation_data(
            rel_id, "prometheus", {"sources": json.dumps(source_data)}
        )

        completed_data = {
            "address": "1.1.1.1",
            "port": 1234,
            "source-type": "prometheus",
            "source-name": f"prometheus_{rel_id}",
            "isDefault": "true",
        }
        sources = self.harness.charm.grafana_provider._stored.sources[rel_id]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 1)

    def test_provider_noop_if_not_leader_on_new_sources(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(False)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        source_data = {
            "address": "1.1.1.1",
            "port": 1234,
            "source-type": "prometheus",
        }
        self.harness.update_relation_data(
            rel_id, "prometheus", {"sources": json.dumps(source_data)}
        )

        with pytest.raises(KeyError):
            self.harness.charm.grafana_provider._stored.sources[rel_id]
        self.assertEqual(self.harness.charm._stored.source_events, 0)

    def test_provider_noop_if_data_is_empty_sources(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)

        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(rel_id, "prometheus", {"sources": "{}"})

        with pytest.raises(KeyError):
            self.harness.charm.grafana_provider._stored.sources[rel_id]
        self.assertEqual(self.harness.charm._stored.source_events, 0)

    def test_provider_sets_with_explicit_name(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        rel_id = self.harness.add_relation("grafana-source", "tester")
        source_data = {
            "address": "1.1.1.1",
            "port": 1234,
            "source-type": "tester",
            "source-name": "test-source",
        }
        self.harness.update_relation_data(
            rel_id, "tester", {"sources": json.dumps(source_data)}
        )

        completed_data = {
            "address": "1.1.1.1",
            "port": 1234,
            "source-type": "tester",
            "source-name": "test-source",
            "isDefault": "true",
        }
        sources = self.harness.charm.grafana_provider._stored.sources[rel_id]
        self.assertIsNotNone(sources)
        self.assertEqual(sources, completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 1)

    def test_provider_handles_multiple_relations(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        source_data = {
            "address": "1.1.1.1",
            "port": 1234,
            "source-type": "prometheus",
            "source-name": f"prometheus_{rel_id}",
            "isDefault": "true",
        }
        self.harness.update_relation_data(
            rel_id, "prometheus", {"sources": json.dumps(source_data)}
        )

        completed_data = {
            "address": "1.1.1.1",
            "port": 1234,
            "source-type": "prometheus",
            "source-name": f"prometheus_{rel_id}",
            "isDefault": "true",
        }
        sources = self.harness.charm.grafana_provider._stored.sources[rel_id]
        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 1)
        self.assertEqual(self.harness.charm._stored.source_events, 1)

        rel_id = self.harness.add_relation("grafana-source", "other-source")
        source_data = {
            "address": "2.2.2.2",
            "port": 1234,
            "source-type": "other-source",
            "source-name": f"other-source_{rel_id}",
            "isDefault": "false",
        }
        self.harness.update_relation_data(
            rel_id, "other-source", {"sources": json.dumps(source_data)}
        )

        completed_data = {
            "address": "2.2.2.2",
            "port": 1234,
            "source-type": "other-source",
            "source-name": f"other-source_{rel_id}",
            "isDefault": "false",
        }
        sources = self.harness.charm.grafana_provider._stored.sources[rel_id]
        self.assertIsNotNone(sources)
        self.assertEqual(sources, completed_data)
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 2)
        self.assertEqual(self.harness.charm._stored.source_events, 2)
        self.assertEqual(len(self.harness.charm.grafana_provider.sources), 2)

    def test_provider_handles_source_removal(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        source_data = {
            "address": "1.1.1.1",
            "port": 1234,
            "source-type": "prometheus",
            "source-name": f"prometheus_{rel_id}",
            "isDefault": "true",
        }
        self.harness.update_relation_data(
            rel_id, "prometheus", {"sources": json.dumps(source_data)}
        )

        completed_data = {
            "address": "1.1.1.1",
            "port": 1234,
            "source-type": "prometheus",
            "source-name": f"prometheus_{rel_id}",
            "isDefault": "true",
        }
        sources = dict(self.harness.charm.grafana_provider._stored.sources[rel_id])
        self.assertIsNotNone(sources)
        self.assertEqual(sources, completed_data)
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 1)
        self.assertEqual(self.harness.charm._stored.source_events, 1)

        rel_id = self.harness.add_relation("grafana-source", "other-source")
        source_data = {
            "address": "2.2.2.2",
            "port": 1234,
            "source-type": "other-source",
            "source-name": f"other-source_{rel_id}",
            "isDefault": "false",
        }
        self.harness.update_relation_data(
            rel_id, "other-source", {"sources": json.dumps(source_data)}
        )

        completed_data = {
            "address": "2.2.2.2",
            "port": 1234,
            "source-type": "other-source",
            "source-name": f"other-source_{rel_id}",
            "isDefault": "false",
        }

        sources = self.harness.charm.grafana_provider._stored.sources[rel_id]
        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.sources), 2)
        self.assertEqual(self.harness.charm._stored.source_events, 2)

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)

        self.harness.charm.on["grafana-source"].relation_broken.emit(rel)
        self.assertEqual(self.harness.charm._stored.source_delete_events, 1)
        self.assertEqual(len(self.harness.charm.grafana_provider.sources_to_delete), 1)

    def test_provider_noop_on_source_removal_if_not_leader(self):
        self.harness.set_leader(False)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)

        self.harness.charm.on["grafana-source"].relation_broken.emit(rel)
        self.assertEqual(self.harness.charm._stored.source_delete_events, 0)
        self.assertEqual(len(self.harness.charm.grafana_provider.sources_to_delete), 0)

    def test_provider_noop_on_source_removal_if_bad_rel_id(self):
        self.harness.set_leader(False)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)

        self.harness.charm.on["grafana-source"].relation_broken.emit(rel)
        self.assertEqual(self.harness.charm._stored.source_delete_events, 0)
        self.assertEqual(len(self.harness.charm.grafana_provider.sources_to_delete), 0)
