# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import base64
import json
import unittest
import uuid
import zlib
from unittest.mock import patch

from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardConsumer
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness

if "unittest.util" in __import__("sys").modules:
    # Show full diff in self.assertEqual.
    __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

DASHBOARD_TMPL = """

"""

CONSUMER_META = """
name: consumer-tester
containers:
  grafana-tester:
requires:
  grafana-dashboard:
    interface: grafana_dashboard
  monitoring:
    interface: monitoring
"""


class ConsumerCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.consumer = GrafanaDashboardConsumer(
            self, "grafana-dashboard", event_relation="monitoring"
        )

        self._stored.set_default(valid_events=0)  # available data sources
        self._stored.set_default(invalid_events=0)

        self.framework.observe(
            self.consumer.on.dashboard_status_changed,
            self._on_dashboard_status_changed,
        )

    def _on_dashboard_status_changed(self, event):
        print(event)
        if event.valid:
            self._stored.valid_events += 1
        elif event.error_message:
            self._stored.invalid_events += 1


@patch.object(zlib, "compress", new=lambda x, *args, **kwargs: x)
@patch.object(zlib, "decompress", new=lambda x, *args, **kwargs: x)
@patch.object(uuid, "uuid4", new=lambda: "12345678")
@patch.object(base64, "b64encode", new=lambda x: x)
@patch.object(base64, "b64decode", new=lambda x: x)
class TestDashboardConsumer(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(ConsumerCharm, meta=CONSUMER_META)
        self.harness._backend.model_name = "testing"
        self.harness._backend.model_uuid = "abcdefgh-1234"
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    def test_consumer_does_not_set_dashboard_without_monitoring(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "consumer")
        self.harness.add_relation_unit(rel_id, "consumer/0")
        self.harness.charm.consumer.add_dashboard(DASHBOARD_TMPL)
        self.assertEqual(self.harness.charm._stored.invalid_events, 1)

    def test_consumer_sets_dashboard_data(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "consumer")
        self.harness.add_relation_unit(rel_id, "consumer/0")
        mon_rel_id = self.harness.add_relation("monitoring", "consumer")
        self.harness.add_relation_unit(mon_rel_id, "monitoring/0")
        self.harness.charm.consumer.add_dashboard(DASHBOARD_TMPL)
        data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        return_data = {
            "monitoring_identifier": "testing_abcdefgh-1234_monitoring",
            "monitoring_target": "Consumer-tester [ testing / abcdefgh-1234 ]",
            "monitoring_query": "juju_model='testing',juju_model_uuid='abcdefgh-1234',juju_application='consumer-tester'",
            "template": "\n\n",
            "removed": False,
            "invalidated": False,
            "invalidated_reason": "",
            "uuid": "12345678",
        }
        self.assertEqual(return_data, data)

    def test_consumer_can_remove_dashboard(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "consumer")
        self.harness.add_relation_unit(rel_id, "consumer/0")
        mon_rel_id = self.harness.add_relation("monitoring", "consumer")
        self.harness.add_relation_unit(mon_rel_id, "monitoring/0")
        self.harness.charm.consumer.add_dashboard(DASHBOARD_TMPL)
        data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        return_data = {
            "monitoring_identifier": "testing_abcdefgh-1234_monitoring",
            "monitoring_target": "Consumer-tester [ testing / abcdefgh-1234 ]",
            "monitoring_query": "juju_model='testing',juju_model_uuid='abcdefgh-1234',juju_application='consumer-tester'",
            "template": "\n\n",
            "removed": False,
            "invalidated": False,
            "invalidated_reason": "",
            "uuid": "12345678",
        }
        self.assertEqual(return_data, data)
        self.harness.charm.consumer.remove_dashboard()
        return_data = {
            "monitoring_identifier": "testing_abcdefgh-1234_monitoring",
            "monitoring_target": "Consumer-tester [ testing / abcdefgh-1234 ]",
            "monitoring_query": "juju_model='testing',juju_model_uuid='abcdefgh-1234',juju_application='consumer-tester'",
            "template": "\n\n",
            "removed": True,
            "invalidated": False,
            "invalidated_reason": "",
            "uuid": "12345678",
        }

    def test_consumer_resends_dashboard_after_monitoring_established(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "consumer")
        self.harness.add_relation_unit(rel_id, "consumer/0")
        self.harness.charm.consumer.add_dashboard(DASHBOARD_TMPL)
        self.assertEqual(self.harness.charm._stored.invalid_events, 1)

        mon_rel_id = self.harness.add_relation("monitoring", "consumer")
        self.harness.add_relation_unit(mon_rel_id, "monitoring/0")
        data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        return_data = {
            "monitoring_identifier": "testing_abcdefgh-1234_monitoring",
            "monitoring_target": "Consumer-tester [ testing / abcdefgh-1234 ]",
            "monitoring_query": "juju_model='testing',juju_model_uuid='abcdefgh-1234',juju_application='consumer-tester'",
            "template": "\n\n",
            "removed": False,
            "invalidated": False,
            "invalidated_reason": "",
            "uuid": "12345678",
        }
        self.assertEqual(return_data, data)

    def test_consumer_invalidates_dashboard_after_monitoring_established_then_broken(
        self,
    ):
        rel_id = self.harness.add_relation("grafana-dashboard", "consumer")
        self.harness.add_relation_unit(rel_id, "consumer/0")
        self.harness.charm.consumer.add_dashboard(DASHBOARD_TMPL)
        self.assertEqual(self.harness.charm._stored.invalid_events, 1)

        mon_rel_id = self.harness.add_relation("monitoring", "consumer")
        self.harness.add_relation_unit(mon_rel_id, "monitoring/0")
        self.harness.remove_relation(mon_rel_id)
        data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        return_data = {
            "monitoring_identifier": "testing_abcdefgh-1234_monitoring",
            "monitoring_target": "Consumer-tester [ testing / abcdefgh-1234 ]",
            "monitoring_query": "juju_model='testing',juju_model_uuid='abcdefgh-1234',juju_application='consumer-tester'",
            "template": "\n\n",
            "removed": False,
            "invalidated": True,
            "invalidated_reason": "Waiting for a monitoring relation to send dashboard data",
            "uuid": "12345678",
        }
        self.assertEqual(return_data, data)
        self.assertEqual(self.harness.charm._stored.invalid_events, 1)
