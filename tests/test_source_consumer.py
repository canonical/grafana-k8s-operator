# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest

from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness
from lib.charms.grafana_k8s.v1.grafana_source import GrafanaSourceConsumer

SOURCE_DATA = {
    "source-name": "test-source",
    "source-type": "test-type",
    "address": "1.2.3.4",
    "port": 1234,
}

EXTRA_SOURCE_DATA = {
    "source-name": "extra-source",
    "source-type": "test-type",
    "address": "4.3.2.1",
    "port": 4321,
}


class ConsumerCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.consumer = GrafanaSourceConsumer(
            self, "grafana-source", {"grafana": ">=1.v0"}
        )

    def add_source(self, data, rel_id=None):
        self.consumer.add_source(
            data["address"],
            data["port"],
            source_type=data["source-type"],
            source_name=data["source-name"],
            rel_id=rel_id,
        )

    def list_sources(self):
        return self.consumer.list_sources()

    @property
    def removed_source_names(self):
        return self.consumer.removed_source_names

    def remove_source(self, rel_id=None):
        self.consumer.remove_source(rel_id)


class TestConsumer(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(ConsumerCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    def test_consumer_can_add_source(self):
        rel_id = self.harness.add_relation("grafana-source", "consumer")
        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertFalse(data)
        self.harness.charm.add_source(SOURCE_DATA)

        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertIn("sources", data)
        source = json.loads(data["sources"])
        self.assertEqual(source, SOURCE_DATA)

    def test_consumer_can_add_source_with_relid(self):
        rel_id = self.harness.add_relation("grafana-source", "consumer")
        self.harness.charm.add_source(SOURCE_DATA, rel_id)

        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        source = json.loads(data["sources"])
        self.assertEqual(source, SOURCE_DATA)

    def test_consumer_can_list_sources(self):
        rel_id = self.harness.add_relation("grafana-source", "consumer")
        self.harness.charm.add_source(SOURCE_DATA, rel_id)

        other_rel = self.harness.add_relation("grafana-source", "consumer")
        self.harness.charm.add_source(EXTRA_SOURCE_DATA, other_rel)

        sources = self.harness.charm.list_sources()
        self.assertEqual(sources, [SOURCE_DATA, EXTRA_SOURCE_DATA])

    def test_consumer_can_remove_source(self):
        rel_id = self.harness.add_relation("grafana-source", "consumer")
        self.harness.charm.add_source(SOURCE_DATA, rel_id)

        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        source = json.loads(data["sources"])
        self.assertEqual(source, SOURCE_DATA)

        self.harness.charm.remove_source()

        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        source = json.loads(data["sources"])
        self.assertFalse(source)

    def test_consumer_can_remove_source_with_id(self):
        rel_id = self.harness.add_relation("grafana-source", "consumer")
        self.harness.charm.add_source(SOURCE_DATA, rel_id)

        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        source = json.loads(data["sources"])
        self.assertEqual(source, SOURCE_DATA)

        self.harness.charm.remove_source(rel_id)

        data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        source = json.loads(data["sources"])
        self.assertFalse(source)
