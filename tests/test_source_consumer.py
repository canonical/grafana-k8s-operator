# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest

import pytest
from charms.grafana_k8s.v0.grafana_source import GrafanaSourceConsumer
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness

SOURCE_DATA = {
    "model": "test-model",
    "model_uuid": "abcdef",
    "application": "prometheus",
    "type": "prometheus",
}

OTHER_SOURCE_DATA = {
    "model": "test-model",
    "model_uuid": "abcdef",
    "application": "other",
    "type": "prometheus",
}


def generate_source_name(source_data):
    return "juju_{}_{}_{}".format(
        source_data["model"], source_data["model_uuid"], source_data["application"]
    )


class GrafanaCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._stored.set_default(source_events=0)  # available data sources
        self._stored.set_default(source_delete_events=0)

        self.grafana_consumer = GrafanaSourceConsumer(self, "grafana-source")
        self.framework.observe(self.grafana_consumer.on.sources_changed, self.source_events)
        self.framework.observe(
            self.grafana_consumer.on.sources_to_delete_changed,
            self.source_delete_events,
        )

    def source_events(self, _):
        self._stored.source_events += 1

    def source_delete_events(self, _):
        self._stored.source_delete_events += 1

    @property
    def version(self):
        return "2.0.0"


class TestSourceConsumer(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def setUp(self):
        self.harness = Harness(GrafanaCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    def setup_charm_relations(self, multi=False):
        """Create relations used by test cases.

        Args:
            multi: a boolean indicating if multiple relations must be
            created.
        """
        rel_ids = []
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        rel_id = self.harness.add_relation("grafana-source", "provider")
        rel_ids.append(rel_id)
        self.harness.update_relation_data(
            rel_id,
            "provider",
            {
                "grafana_source_data": json.dumps(SOURCE_DATA),
            },
        )
        self.harness.add_relation_unit(rel_id, "provider/0")
        self.harness.update_relation_data(
            rel_id, "provider/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        self.assertEqual(self.harness.charm._stored.source_events, 2)

        if multi:
            rel_id = self.harness.add_relation("grafana-source", "other-provider")
            rel_ids.append(rel_id)
            self.harness.update_relation_data(
                rel_id,
                "other-provider",
                {
                    "grafana_source_data": json.dumps(OTHER_SOURCE_DATA),
                },
            )
            self.harness.add_relation_unit(rel_id, "other-provider/0")
            self.harness.update_relation_data(
                rel_id, "other-provider/0", {"grafana_source_host": "2.3.4.5:9090"}
            )
            self.assertEqual(self.harness.charm._stored.num_events, 4)

        return rel_ids

    def validate_sources(self, sources):
        for source in sources:
            self.assertIn("source_name", source)
            self.assertIn("source_type", source)
            self.assertIn("url", source)

    def test_consumer_notifies_on_new_sources(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://1.2.3.4:9090",
            "unit": "prometheus/0",
        }
        sources = self.harness.charm.grafana_consumer._stored.sources[rel_id][0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 2)

    def test_consumer_noop_if_not_leader_on_new_sources(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(False)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )

        with pytest.raises(KeyError):
            self.harness.charm.grafana_consumer._stored.sources[rel_id]
        self.assertEqual(self.harness.charm._stored.source_events, 0)

    def test_consumer_noop_if_data_is_empty_sources(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)

        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(rel_id, "prometheus", {"sources": "{}"})

        with pytest.raises(KeyError):
            self.harness.charm.grafana_consumer._stored.sources[rel_id]
        self.assertEqual(self.harness.charm._stored.source_events, 1)

    def test_consumer_handles_multiple_relations(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://1.2.3.4:9090",
            "unit": "prometheus/0",
        }
        sources = self.harness.charm.grafana_consumer._stored.sources[rel_id][0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 2)

        other_rel_id = self.harness.add_relation("grafana-source", "other-source")
        self.harness.update_relation_data(
            other_rel_id,
            "other-source",
            {"grafana_source_data": json.dumps(OTHER_SOURCE_DATA)},
        )
        self.harness.add_relation_unit(other_rel_id, "other-source/0")
        self.harness.update_relation_data(
            other_rel_id, "other-source/0", {"grafana_source_host": "2.3.4.5:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(OTHER_SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://2.3.4.5:9090",
            "unit": "other-source/0",
        }
        sources = self.harness.charm.grafana_consumer._stored.sources[other_rel_id][0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.sources), 2)
        self.assertEqual(self.harness.charm._stored.source_events, 4)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 2)

    def test_consumer_handles_source_removal(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://1.2.3.4:9090",
            "unit": "prometheus/0",
        }
        sources = self.harness.charm.grafana_consumer._stored.sources[rel_id][0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 2)

        other_rel_id = self.harness.add_relation("grafana-source", "other-source")
        self.harness.update_relation_data(
            other_rel_id,
            "other-source",
            {"grafana_source_data": json.dumps(OTHER_SOURCE_DATA)},
        )
        self.harness.add_relation_unit(other_rel_id, "other-source/0")
        self.harness.update_relation_data(
            other_rel_id, "other-source/0", {"grafana_source_host": "2.3.4.5:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(OTHER_SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://2.3.4.5:9090",
            "unit": "other-source/0",
        }
        sources = self.harness.charm.grafana_consumer._stored.sources[other_rel_id][0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.sources), 2)
        self.assertEqual(self.harness.charm._stored.source_events, 4)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 2)

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)  # type: ignore

        self.harness.charm.on["grafana-source"].relation_departed.emit(rel)
        self.assertEqual(self.harness.charm._stored.source_delete_events, 1)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources_to_delete), 1)

    def test_consumer_noop_on_source_removal_if_not_leader(self):
        self.harness.set_leader(False)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)  # type: ignore

        self.harness.charm.on["grafana-source"].relation_broken.emit(rel)
        self.assertEqual(self.harness.charm._stored.source_delete_events, 0)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources_to_delete), 0)

    def test_consumer_data_is_usable_after_upgrade(self):
        original_source_data = {
            "rel_id": [
                {
                    "source-name": "shouldconvert",
                    "source-type": "prometheus",
                    "unit": "prometheus/0",
                    "url": "1.2.3.4",
                }
            ]
        }
        compatible_source_data = {
            "rel_id": [
                {
                    "source-name": "shouldconvert",
                    "source_name": "shouldconvert",
                    "source-type": "prometheus",
                    "source_type": "prometheus",
                    "unit": "prometheus/0",
                    "url": "1.2.3.4",
                }
            ]
        }
        self.harness.set_leader(False)
        self.harness.charm.grafana_consumer._stored.sources = original_source_data
        self.harness.charm.grafana_consumer.upgrade_keys()
        # GrafanaConsumer.sources() actually puts them into a list without rel_id, which is
        # used only for tracking, so we don't check for an exact match in this lookup
        self.assertEqual(
            self.harness.charm.grafana_consumer.sources, compatible_source_data["rel_id"]
        )

    def test_consumer_noop_on_source_removal_if_bad_rel_id(self):
        self.harness.set_leader(False)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)  # type: ignore

        self.harness.charm.on["grafana-source"].relation_broken.emit(rel)
        self.assertEqual(self.harness.charm._stored.source_delete_events, 0)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources_to_delete), 0)
