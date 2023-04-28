# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import base64
import json
import lzma
import unittest
import uuid
from unittest.mock import patch

from charms.grafana_k8s.v0.grafana_dashboard import (
    DATASOURCE_TEMPLATE_DROPDOWNS,
    TOPOLOGY_TEMPLATE_DROPDOWNS,
    CosTool,
    GrafanaDashboardConsumer,
)
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness

if "unittest.util" in __import__("sys").modules:
    # Show full diff in self.assertEqual.
    __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

MODEL_INFO = {"name": "testing", "uuid": "abcdefgh-1234"}
TEMPLATE_DROPDOWNS = TOPOLOGY_TEMPLATE_DROPDOWNS + DATASOURCE_TEMPLATE_DROPDOWNS

DASHBOARD_TEMPLATE = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "${prometheusds}",
            "targets": [
                {
                    "expr": "up{job='foo'}"
                }
            ]
        }
    ]
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
        "panels": [
            {
                "data": "label_values(up, juju_unit)",
                "datasource": "${prometheusds}",
                "targets": [
                    {
                        "expr": 'up{job="foo",juju_application=~"$juju_application",juju_model=~"$juju_model",juju_model_uuid=~"$juju_model_uuid",juju_unit=~"$juju_unit"}',
                    },
                ],
            },
        ],
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
    }
)

DASHBOARD_DATA_NO_TOPOLOGY = {
    "charm": "grafana-k8s",
    "content": DASHBOARD_TEMPLATE,
    "juju_topology": {},
}

DASHBOARD_RENDERED_NO_TOPOLOGY = json.dumps(
    {
        "panels": [
            {
                "data": "label_values(up, juju_unit)",
                "datasource": "${prometheusds}",
                "targets": [
                    {
                        "expr": "up{job='foo'}",
                    },
                ],
            },
        ],
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
    }
)

LOKI_DASHBOARD_TEMPLATE = r"""
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "${lokids}",
            "targets": [
                {
                    "expr": "{job=\".+\"}"
                }
            ]
        }
    ]
}
"""

LOKI_DASHBOARD_DATA = {
    "charm": "grafana-k8s",
    "content": LOKI_DASHBOARD_TEMPLATE,
    "juju_topology": {
        "model": MODEL_INFO["name"],
        "model_uuid": MODEL_INFO["uuid"],
        "application": "provider-tester",
        "unit": "provider-tester/0",
    },
}

LOKI_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {
                "data": "label_values(up, juju_unit)",
                "datasource": "${lokids}",
                "targets": [
                    {
                        "expr": r'{job=".+", juju_application=~"$juju_application", juju_model=~"$juju_model", juju_model_uuid=~"$juju_model_uuid", juju_unit=~"$juju_unit"}',
                    },
                ],
            },
        ],
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
    }
)

SOURCE_DATA = {
    "templates": {"file:tester": DASHBOARD_DATA},
    "uuid": "12345678",
}

DASHBOARD_TEMPLATE_WITH_NEGATIVE = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "targets": [
                {
                    "expr": "sum(up{job='foo'})"
                },
                {
                    "expr": "-sum(up{job='foo'})"
                }
            ],
            "datasource": "${prometheusds}"
        }
    ]
}
"""

DASHBOARD_DATA_WITH_NEGATIVE = {
    "charm": "grafana-k8s",
    "content": DASHBOARD_TEMPLATE_WITH_NEGATIVE,
    "juju_topology": {
        "model": MODEL_INFO["name"],
        "model_uuid": MODEL_INFO["uuid"],
        "application": "provider-tester",
        "unit": "provider-tester/0",
    },
}

DASHBOARD_RENDERED_WITH_NEGATIVE = json.dumps(
    {
        "panels": [
            {
                "data": "label_values(up, juju_unit)",
                "targets": [
                    {
                        "expr": 'sum(up{job="foo",juju_application=~"$juju_application",juju_model=~"$juju_model",juju_model_uuid=~"$juju_model_uuid",juju_unit=~"$juju_unit"})',
                    },
                    {
                        "expr": '-sum(up{job="foo",juju_application=~"$juju_application",juju_model=~"$juju_model",juju_model_uuid=~"$juju_model_uuid",juju_unit=~"$juju_unit"})',
                    },
                ],
                "datasource": "${prometheusds}",
            },
        ],
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
    }
)

DASHBOARD_TEMPLATE_WITH_RANGES = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "targets": [
                {
                    "expr": "rate(http_requests_total{job='foo'}[$__interval]) / rate(http_requests_total{job='foo'}[5m]) >= 0"
                }
            ],
            "datasource": "${prometheusds}"
        }
    ]
}
"""

DASHBOARD_DATA_WITH_RANGES = {
    "charm": "grafana-k8s",
    "content": DASHBOARD_TEMPLATE_WITH_RANGES,
    "juju_topology": {
        "model": MODEL_INFO["name"],
        "model_uuid": MODEL_INFO["uuid"],
        "application": "provider-tester",
        "unit": "provider-tester/0",
    },
}

DASHBOARD_RENDERED_WITH_RANGES = json.dumps(
    {
        "panels": [
            {
                "data": "label_values(up, juju_unit)",
                "targets": [
                    {
                        "expr": 'rate(http_requests_total{job="foo",juju_application=~"$juju_application",juju_model=~"$juju_model",juju_model_uuid=~"$juju_model_uuid",juju_unit=~"$juju_unit"}[$__interval]) / rate(http_requests_total{job="foo",juju_application=~"$juju_application",juju_model=~"$juju_model",juju_model_uuid=~"$juju_model_uuid",juju_unit=~"$juju_unit"}[5m]) >= 0',
                    },
                ],
                "datasource": "${prometheusds}",
            },
        ],
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
    }
)

DASHBOARD_TEMPLATE_WITH_OFFSETS = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "targets": [
                {
                    "expr": "sum(http_requests_total{job='foo'} offset $__interval) - sum(http_requests_total{job='foo'} offset -5m)"
                }
            ],
            "datasource": "${prometheusds}"
        }
    ]
}
"""

DASHBOARD_DATA_WITH_OFFSETS = {
    "charm": "grafana-k8s",
    "content": DASHBOARD_TEMPLATE_WITH_OFFSETS,
    "juju_topology": {
        "model": MODEL_INFO["name"],
        "model_uuid": MODEL_INFO["uuid"],
        "application": "provider-tester",
        "unit": "provider-tester/0",
    },
}

DASHBOARD_RENDERED_WITH_OFFSETS = json.dumps(
    {
        "panels": [
            {
                "data": "label_values(up, juju_unit)",
                "targets": [
                    {
                        "expr": 'sum(http_requests_total{job="foo",juju_application=~"$juju_application",juju_model=~"$juju_model",juju_model_uuid=~"$juju_model_uuid",juju_unit=~"$juju_unit"} offset $__interval) - sum(http_requests_total{job="foo",juju_application=~"$juju_application",juju_model=~"$juju_model",juju_model_uuid=~"$juju_model_uuid",juju_unit=~"$juju_unit"} offset -5m)',
                    },
                ],
                "datasource": "${prometheusds}",
            },
        ],
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
    }
)


class ConsumerCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._stored.set_default(dashboard_events=0)

        self.transformer = CosTool(self)
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
class TestDashboardLabelInjector(unittest.TestCase):
    def setUp(self):
        meta = open("metadata.yaml")
        self.harness = Harness(ConsumerCharm, meta=meta)
        self.harness.set_model_info(name=MODEL_INFO["name"], uuid=MODEL_INFO["uuid"])
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()
        self.harness.add_relation("grafana", "grafana")

    def setup_charm_relations(self) -> list:
        """Create relations used by test cases."""
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

    def setup_different_dashboard(self, template: str, alternative_data: dict = None) -> list:
        """Create relations used by test cases with alternate templates."""
        rel_ids = []
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        source_rel_id = self.harness.add_relation("grafana-source", "source")
        self.harness.add_relation_unit(source_rel_id, "source/0")
        rel_id = self.harness.add_relation("grafana-dashboard", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        rel_ids.append(rel_id)

        d = alternative_data or DASHBOARD_DATA
        d["content"] = template

        data = {
            "templates": {"file:tester": d},
            "uuid": "12345678",
        }

        self.harness.update_relation_data(
            rel_id,
            "provider",
            {
                "dashboards": json.dumps(data),
            },
        )

        return rel_ids

    @unittest.mock.patch("platform.processor", lambda: "x86_64")
    def test_consumer_adds_labels(self):
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

    @unittest.mock.patch("platform.processor", lambda: "x86_64")
    def test_consumer_does_not_add_labels_without_topology(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(DASHBOARD_TEMPLATE, DASHBOARD_DATA_NO_TOPOLOGY)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": DASHBOARD_RENDERED_NO_TOPOLOGY,
                }
            ],
        )

    @unittest.mock.patch("platform.processor", lambda: "x86_64")
    def test_consumer_adds_labels_for_loki(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(LOKI_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": LOKI_DASHBOARD_RENDERED,
                }
            ],
        )

    @unittest.mock.patch("platform.processor", lambda: "x86_64")
    def test_consumer_handles_negatives_and_multiple_targets(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(DASHBOARD_TEMPLATE_WITH_NEGATIVE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": DASHBOARD_RENDERED_WITH_NEGATIVE,
                }
            ],
        )

    @unittest.mock.patch("platform.processor", lambda: "x86_64")
    def test_consumer_handles_expressions_with_ranges(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(DASHBOARD_TEMPLATE_WITH_RANGES)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": DASHBOARD_RENDERED_WITH_RANGES,
                }
            ],
        )

    @unittest.mock.patch("platform.processor", lambda: "x86_64")
    def test_consumer_handles_expressions_with_offsets(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(DASHBOARD_TEMPLATE_WITH_OFFSETS)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": DASHBOARD_RENDERED_WITH_OFFSETS,
                }
            ],
        )
