# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import base64
import json
import lzma
import unittest
import uuid
from unittest.mock import patch

from charms.grafana_k8s.v0.grafana_dashboard import (
    TEMPLATE_DROPDOWNS,
    GrafanaDashboardConsumer,
)
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness

if "unittest.util" in __import__("sys").modules:
    # Show full diff in self.assertEqual.
    __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

MODEL_INFO = {"name": "testing", "uuid": "abcdefgh-1234"}

DASHBOARD_TEMPLATE = """
{
    "panels": {
        "data": "label_values(up, juju_unit)"
    }
}
"""

DASHBOARD_DATA = {
    "charm": "grafana-k8s",
    "content": DASHBOARD_TEMPLATE,
    "juju_topology": {
        "model": MODEL_INFO["name"],
        "model_uuid": MODEL_INFO["uuid"],
        "application": "provider-tester",
        "unit": "provider-tester/0",
    },
}

DASHBOARD_RENDERED = json.dumps(
    {
        "panels": {"data": "label_values(up, juju_unit)"},
        "templating": {"list": [d for d in TEMPLATE_DROPDOWNS]},
    }
)


SOURCE_DATA = {
    "templates": {"file:tester": DASHBOARD_DATA},
    "uuid": "12345678",
}


class ConsumerCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._stored.set_default(dashboard_events=0)

        self.grafana_consumer = GrafanaDashboardConsumer(self)
        self.framework.observe(self.grafana_consumer.on.dashboards_changed, self.dashboard_events)

    def dashboard_events(self, _):
        self._stored.dashboard_events += 1

    @property
    def version(self):
        return "2.0.0"

    @property
    def peers(self):
        """Fetch the peer relation."""
        return self.model.get_relation("grafana")


@patch.object(lzma, "compress", new=lambda x, *args, **kwargs: x)
@patch.object(lzma, "decompress", new=lambda x, *args, **kwargs: x)
@patch.object(uuid, "uuid4", new=lambda: "12345678")
@patch.object(base64, "b64encode", new=lambda x: x)
@patch.object(base64, "b64decode", new=lambda x: x)
class TestDashboardConsumer(unittest.TestCase):
    def setUp(self):
        meta = open("metadata.yaml")
        self.harness = Harness(ConsumerCharm, meta=meta)
        self.harness.set_model_info(name=MODEL_INFO["name"], uuid=MODEL_INFO["uuid"])
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()
        self.harness.add_relation("grafana", "grafana")

    def setup_charm_relations(self):
        """Create relations used by test cases.

        Args:
            multi: a boolean indicating if multiple relations must be
            created.
        """
        rel_ids = []
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        source_rel_id = self.harness.add_relation("grafana-source", "source")
        self.harness.add_relation_unit(source_rel_id, "source/0")
        rel_id = self.harness.add_relation("grafana-dashboard", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        rel_ids.append(rel_id)
        self.harness.update_relation_data(
            rel_id,
            "provider",
            {
                "dashboards": json.dumps(SOURCE_DATA),
            },
        )

        return rel_ids

    def test_consumer_notifies_on_new_dashboards(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_charm_relations()
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": DASHBOARD_RENDERED,
                }
            ],
        )

    def test_consumer_error_on_bad_template(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        rels = self.setup_charm_relations()
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        bad_data = {
            "templates": {
                "file:tester": {
                    "charm": "grafana-k8s",
                    "content": "{{ unclosed variable",
                    "juju_topology": {
                        "model": MODEL_INFO["name"],
                        "model_uuid": MODEL_INFO["uuid"],
                        "application": "provider-tester",
                        "unit": "provider-tester/0",
                    },
                }
            },
            "uuid": "12345678",
        }

        self.harness.update_relation_data(
            rels[0],
            "provider",
            {
                "dashboards": json.dumps(bad_data),
            },
        )

        data = json.loads(
            self.harness.get_relation_data(rels[0], self.harness.model.app.name)["event"]
        )
        self.assertEqual(
            data["errors"],
            [
                {
                    "dashboard_id": "file:tester",
                    "error": "expected token 'end of print statement', got 'variable'",
                }
            ],
        )
