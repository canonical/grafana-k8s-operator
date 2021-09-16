# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import base64
import copy
import json
import unittest
import uuid
import zlib
from unittest.mock import patch

from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness

if "unittest.util" in __import__("sys").modules:
    # Show full diff in self.assertEqual.
    __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

DASHBOARD_TMPL = """
"name": "{{ grafana_datasource }}"
"label": "{{ prometheus_target }}"
"query": "label_values(up{ {{ prometheus_query }} }, juju_unit)"
"""

DASHBOARD_RENDERED = """
"name": "testing_abcdefgh-1234_monitoring"
"label": "Consumer-tester [ testing / abcdefgh-1234 ]"
"query": "label_values(up{ juju_model='testing',juju_model_uuid='abcdefgh-1234',juju_application='consumer-tester' }, juju_unit)"
"""

SOURCE_DATA = {
    "monitoring_identifier": "testing_abcdefgh-1234_monitoring",
    "monitoring_target": "Consumer-tester [ testing / abcdefgh-1234 ]",
    "monitoring_query": "juju_model='testing',juju_model_uuid='abcdefgh-1234',juju_application='consumer-tester'",
    "name": "dashboard-test",
    "template": DASHBOARD_TMPL,
    "removed": False,
    "invalidated": False,
    "invalidated_reason": "",
    "uuid": "12345678",
}

OTHER_SOURCE_DATA = {
    "monitoring_identifier": "testing_abcdefgh-2345_monitoring",
    "monitoring_target": "Consumer-tester [ testing / abcdefgh-2345 ]",
    "monitoring_query": "juju_model='testing',juju_model_uuid='abcdefgh-2345',juju_application='consumer-tester'",
    "name": "dashboard-test",
    "template": DASHBOARD_TMPL,
    "removed": False,
    "invalidated": False,
    "invalidated_reason": "",
    "uuid": "12345678",
}


class ProviderCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._stored.set_default(dashboard_events=0)

        self.grafana_provider = GrafanaDashboardProvider(self, "grafana-dashboard")
        self.framework.observe(self.grafana_provider.on.dashboards_changed, self.dashboard_events)

    def dashboard_events(self, _):
        self._stored.dashboard_events += 1

    @property
    def version(self):
        return "2.0.0"


@patch.object(zlib, "compress", new=lambda x, *args, **kwargs: x)
@patch.object(zlib, "decompress", new=lambda x, *args, **kwargs: x)
@patch.object(uuid, "uuid4", new=lambda: "12345678")
@patch.object(base64, "b64encode", new=lambda x: x)
@patch.object(base64, "b64decode", new=lambda x: x)
class TestDashboardProvider(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(ProviderCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()

    def setup_charm_relations(self, multi=False):
        """Create relations used by test cases.

        Args:
            multi: a boolean indicating if multiple relations must be
            created.
        """
        self.harness.charm.grafana_provider._stored.active_sources = [
            {"source-name": "testing_abcdefgh-1234_monitoring"},
            {"source-name": "testing_abcdefgh-2345_monitoring"},
        ]

        rel_ids = []
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        rel_id = self.harness.add_relation("grafana-dashboard", "consumer")
        rel_ids.append(rel_id)
        self.harness.add_relation_unit(rel_id, "consumer/0")
        self.harness.update_relation_data(
            rel_id,
            "consumer",
            {
                "dashboards": json.dumps(SOURCE_DATA),
            },
        )
        if multi:
            rel_id = self.harness.add_relation("grafana-source", "other-consumer")
            rel_ids.append(rel_id)
            self.harness.add_relation_unit(rel_id, "other-consumer/0")
            self.harness.update_relation_data(
                rel_id,
                "other-consumer",
                {
                    "dashboards": json.dumps(SOURCE_DATA),
                },
            )

        return rel_ids

    def test_provider_notifies_on_new_dashboards(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_charm_relations()
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        # Terrible type conversions again
        stored = self.harness.charm.grafana_provider.dashboards[0]
        stored = dict(stored)
        stored["data"] = dict(stored["data"])
        self.maxDiff = None
        self.assertEqual(
            stored,
            {
                "target": "testing_abcdefgh-1234_monitoring",
                "data": {
                    "monitoring_identifier": "testing_abcdefgh-1234_monitoring",
                    "monitoring_target": "Consumer-tester [ testing / abcdefgh-1234 ]",
                    "monitoring_query": "juju_model='testing',juju_model_uuid='abcdefgh-1234',juju_application='consumer-tester'",
                    "name": "dashboard-test",
                    "template": DASHBOARD_TMPL,
                    "removed": False,
                    "invalidated": False,
                    "invalidated_reason": "",
                },
                "name": "dashboard-test",
                "dashboard": DASHBOARD_RENDERED.rstrip(),
            },
        )

    def test_provider_error_on_bad_template(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        rels = self.setup_charm_relations()
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        bad_data = copy.deepcopy(SOURCE_DATA)
        bad_data["template"] = "JUNK! {{{novar}}}"

        self.harness.update_relation_data(
            rels[0],
            "consumer",
            {
                "dashboards": json.dumps(bad_data),
            },
        )

        data = json.loads(
            self.harness.get_relation_data(rels[0], self.harness.model.app.name)["event"]
        )
        self.assertEqual(data["valid"], False)
        self.assertIn("Cannot add Grafana dashboard. Template is not valid Jinja", data["errors"])

    def test_provider_error_on_invalidation(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        rels = self.setup_charm_relations()
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        bad_data = copy.deepcopy(SOURCE_DATA)
        bad_data["invalidated"] = True
        bad_data["invalidated_reason"] = "Doesn't matter"

        self.harness.update_relation_data(
            rels[0],
            "consumer",
            {
                "dashboards": json.dumps(bad_data),
            },
        )

        data = json.loads(
            self.harness.get_relation_data(rels[0], self.harness.model.app.name)["event"]
        )
        self.assertEqual(data["valid"], False)
        self.assertIn("Doesn't matter", data["errors"])

    def test_provider_error_on_no_sources(self):
        self.assertEqual(len(self.harness.charm.grafana_provider._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        rels = self.setup_charm_relations()
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)
        self.harness.charm.grafana_provider._stored.active_sources = []

        self.harness.update_relation_data(
            rels[0],
            "consumer",
            {
                "dashboards": json.dumps(SOURCE_DATA),
            },
        )

        data = json.loads(
            self.harness.get_relation_data(rels[0], self.harness.model.app.name)["event"]
        )
        self.assertEqual(data["valid"], False)
        self.assertIn("No configured datasources", data["errors"])
