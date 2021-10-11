# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import copy
import json
import unittest
import uuid
from unittest.mock import patch

from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardConsumer
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness

if "unittest.util" in __import__("sys").modules:
    # Show full diff in self.assertEqual.
    __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

RELATION_TEMPLATES_DATA = {
    "file:first": {
        "charm": "consumer-tester",
        "content": "eNorSS0uiU/LLCou4QIAG8EEUg==",
        "juju_topology": {
            "model": "testing",
            "model_uuid": "abcdefgh-1234",
            "application": "consumer-tester",
            "unit": "consumer-tester/0",
        },
    },
    "file:other": {
        "charm": "consumer-tester",
        "content": "eNorSS0uiS9OTc7PS+ECACCnBKY=",
        "juju_topology": {
            "model": "testing",
            "model_uuid": "abcdefgh-1234",
            "application": "consumer-tester",
            "unit": "consumer-tester/0",
        },
    },
}


CONSUMER_META = """
name: consumer-tester
containers:
  grafana-tester:
provides:
  grafana-dashboard:
    interface: grafana_dashboard
"""


class ConsumerCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.consumer = GrafanaDashboardConsumer(self)

        self._stored.set_default(valid_events=0)  # available data sources
        self._stored.set_default(invalid_events=0)

        self.framework.observe(
            self.consumer.on.dashboard_status_changed,
            self._on_dashboard_status_changed,
        )

    def _on_dashboard_status_changed(self, event):
        if event.valid:
            self._stored.valid_events += 1
        elif event.error_message:
            self._stored.invalid_events += 1


class TestDashboardConsumer(unittest.TestCase):
    @patch(
        "charms.grafana_k8s.v0.grafana_dashboard._resolve_dir_against_charm_path",
        new=lambda x, *args, **kwargs: "./tests/dashboard_templates",
    )
    @patch.object(uuid, "uuid4", new=lambda: "12345678")
    def setUp(self):
        self.harness = Harness(ConsumerCharm, meta=CONSUMER_META)
        self.harness._backend.model_name = "testing"
        self.harness._backend.model_uuid = "abcdefgh-1234"
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.harness.set_leader(True)

    @patch.object(uuid, "uuid4", new=lambda: "12345678")
    def test_consumer_sets_dashboard_data(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )

        self.assertDictEqual(
            {
                "templates": RELATION_TEMPLATES_DATA,
                "uuid": "12345678",
            },
            data,
        )

    @patch.object(uuid, "uuid4", new=lambda: "12345678")
    def test_consumer_can_remove_programmatically_added_dashboards(self):
        self.harness.charm.consumer.add_dashboard("third")

        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )

        expected_data_builtin_dashboards = {
            "templates": copy.deepcopy(RELATION_TEMPLATES_DATA),
            "uuid": "12345678",
        }

        expected_data = copy.deepcopy(expected_data_builtin_dashboards)
        expected_templates = expected_data["templates"]
        expected_templates["prog:eNorycg"] = {  # type: ignore
            "charm": "consumer-tester",
            "content": "eNorycgsSgEABmwCHA==",
            "juju_topology": {
                "model": "testing",
                "model_uuid": "abcdefgh-1234",
                "application": "consumer-tester",
                "unit": "consumer-tester/0",
            },
        }

        self.assertDictEqual(expected_data, actual_data)
        self.harness.charm.consumer.remove_non_builtin_dashboards()
        self.assertEqual(
            expected_data_builtin_dashboards,
            json.loads(
                self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
            ),
        )

    @patch.object(uuid, "uuid4", new=lambda: "12345678")
    def test_consumer_cannot_remove_builtin_dashboards(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )

        expected_data = {
            "templates": RELATION_TEMPLATES_DATA,
            "uuid": "12345678",
        }

        self.assertDictEqual(expected_data, actual_data)

        self.harness.charm.consumer.remove_non_builtin_dashboards()
        self.assertEqual(
            expected_data,
            json.loads(
                self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
            ),
        )
