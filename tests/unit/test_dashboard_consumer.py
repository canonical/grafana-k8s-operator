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


DASHBOARD_RENDERED_NO_DROPDOWNS = json.dumps(
    {
        "panels": {"data": "label_values(up, juju_unit)"},
        "templating": {"list": [d for d in DATASOURCE_TEMPLATE_DROPDOWNS]},
    }
)


SOURCE_DATA = {
    "templates": {"file:tester": DASHBOARD_DATA},
    "uuid": "12345678",
}

VARIABLE_DASHBOARD_TEMPLATE = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "$replace_me"
        }
    ]
}
"""

VARIABLE_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {"data": "label_values(up, juju_unit)", "datasource": "${prometheusds}"},
        ],
        "templating": {"list": [d for d in TEMPLATE_DROPDOWNS]},
    }
)

INPUT_DASHBOARD_TEMPLATE = """
{
    "__inputs": [
        {
            "name": "DS_PROMETHEUS",
            "label": "Prometheus",
            "type": "datasource",
            "pluginId": "prometheus",
            "pluginName": "prometheus"
        }
    ],
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "$DS_PROMETHEUS"
        }
    ]
}
"""

INPUT_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {"data": "label_values(up, juju_unit)", "datasource": "${prometheusds}"},
        ],
        "templating": {"list": [d for d in TEMPLATE_DROPDOWNS]},
    }
)

NULL_DATASOURCE_DASHBOARD_TEMPLATE = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "$replace_me"
        },
        {
            "data": "Row separator",
            "datasource": null
        }
    ]
}
"""

NULL_DATASOURCE_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {"data": "label_values(up, juju_unit)", "datasource": "${prometheusds}"},
            {"data": "Row separator", "datasource": None},
        ],
        "templating": {"list": [d for d in TEMPLATE_DROPDOWNS]},
    }
)

EXISTING_VARIABLE_DASHBOARD_TEMPLATE = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "${replace_me_too}"
        },
        {
            "data": "label_values(up, juju_application)",
            "datasource": "$replace_me_also"
        },
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "${leave_me_alone}"
        }
    ],
    "templating": {
        "list": [
            {
                "name": "replace_me_too",
                "query": "prometheus",
                "type": "datasource"
            },
            {
                "name": "replace_me_also",
                "query": "ProMeTheus",
                "type": "datasource"
            },
            {
                "name": "leave_me_alone",
                "query": "influxdb",
                "type": "datasource"
            }
        ]
    }
}
"""

EXISTING_VARIABLE_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {"data": "label_values(up, juju_unit)", "datasource": "${prometheusds}"},
            {"data": "label_values(up, juju_application)", "datasource": "${prometheusds}"},
            {"data": "label_values(up, juju_unit)", "datasource": "${leave_me_alone}"},
        ],
        "templating": {
            "list": [d for d in reversed(TEMPLATE_DROPDOWNS)]
            + [{"name": "leave_me_alone", "query": "influxdb", "type": "datasource"}]
        },
    }
)

EXISTING_DATASOURCE_DASHBOARD_TEMPLATE = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "${prometheusds}"
        },
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "${leave_me_alone}"
        }
    ],
    "templating": {
        "list": [
            {
                "description": null,
                "error": null,
                "hide": 0,
                "includeAll": false,
                "label": null,
                "multi": false,
                "name": "prometheusds",
                "options": [],
                "query": "prometheus",
                "refresh": 1,
                "regex": "",
                "skipUrlSync": false,
                "type": "datasource"
            },
            {
                "name": "leave_me_alone",
                "query": "influxdb",
                "type": "datasource"
            }
        ]
    }
}
"""

EXISTING_DATASOURCE_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {"data": "label_values(up, juju_unit)", "datasource": "${prometheusds}"},
            {"data": "label_values(up, juju_unit)", "datasource": "${leave_me_alone}"},
        ],
        "templating": {
            "list": [d for d in reversed(TEMPLATE_DROPDOWNS)]
            + [{"name": "leave_me_alone", "query": "influxdb", "type": "datasource"}]
        },
    }
)

EXISTING_LOKI_DATASOURCE_DASHBOARD_TEMPLATE = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "${lokids}"
        },
        {
            "data": "label_values(up, juju_unit)",
            "datasource": "${leave_me_alone}"
        }
    ],
    "templating": {
        "list": [
            {
                "description": null,
                "error": null,
                "hide": 0,
                "includeAll": false,
                "label": null,
                "multi": false,
                "name": "lokids",
                "options": [],
                "query": "loki",
                "refresh": 1,
                "regex": "",
                "skipUrlSync": false,
                "type": "datasource"
            },
            {
                "name": "leave_me_alone",
                "query": "influxdb",
                "type": "datasource"
            }
        ]
    }
}
"""

EXISTING_LOKI_DATASOURCE_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {"data": "label_values(up, juju_unit)", "datasource": "${lokids}"},
            {"data": "label_values(up, juju_unit)", "datasource": "${leave_me_alone}"},
        ],
        "templating": {
            "list": [d for d in reversed(TEMPLATE_DROPDOWNS)]
            + [{"name": "leave_me_alone", "query": "influxdb", "type": "datasource"}]
        },
    }
)

DICT_DATASOURCE_DASHBOARD_TEMPLATE = """
{
    "panels": [
        {
            "data": "label_values(up, juju_unit)",
            "datasource": {
                "type": "prometheus",
                "uid": "someuid"
            }
        }
    ]
}
"""

DICT_DATASOURCE_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {
                "data": "label_values(up, juju_unit)",
                "datasource": {
                    "type": "prometheus",
                    "uid": "${prometheusds}",
                },
            },
        ],
        "templating": {"list": [d for d in TEMPLATE_DROPDOWNS]},
    }
)


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
        self.harness.add_relation("grafana", "grafana-k8s")

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

    def setup_without_dropdowns(self, template: str) -> list:
        """Create relations used by test cases with alternate templates."""
        rel_ids = []
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        source_rel_id = self.harness.add_relation("grafana-source", "source")
        self.harness.add_relation_unit(source_rel_id, "source/0")
        rel_id = self.harness.add_relation("grafana-dashboard", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        rel_ids.append(rel_id)

        d = DASHBOARD_DATA.copy()
        d["inject_dropdowns"] = False
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

    def setup_different_dashboard(self, template: str) -> list:
        """Create relations used by test cases with alternate templates."""
        rel_ids = []
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        source_rel_id = self.harness.add_relation("grafana-source", "source")
        self.harness.add_relation_unit(source_rel_id, "source/0")
        rel_id = self.harness.add_relation("grafana-dashboard", "provider")
        self.harness.add_relation_unit(rel_id, "provider/0")
        rel_ids.append(rel_id)

        d = DASHBOARD_DATA
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

    def test_consumer_notifies_on_new_dashboards_without_dropdowns(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_without_dropdowns(DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": DASHBOARD_RENDERED_NO_DROPDOWNS,
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

    def test_consumer_error_on_bad_json(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        rels = self.setup_charm_relations()
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        bad_data = {
            "templates": {
                "file:tester": {
                    "charm": "grafana-k8s",
                    "content": '{ "foo": "bar",,},',
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

        with self.assertLogs(level="WARNING") as cm:
            self.harness.update_relation_data(
                rels[0],
                "provider",
                {
                    "dashboards": json.dumps(bad_data),
                },
            )
            self.assertTrue(
                any(["Invalid JSON in Grafana dashboard: file:tester" in msg for msg in cm.output])
            )

    def test_consumer_templates_datasource(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(VARIABLE_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": VARIABLE_DASHBOARD_RENDERED,
                }
            ],
        )

    def test_consumer_templates_dashboard_with_inputs(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(INPUT_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.maxDiff = None
        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": INPUT_DASHBOARD_RENDERED,
                }
            ],
        )

    def test_consumer_templates_with_null_datasource(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(NULL_DATASOURCE_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": NULL_DATASOURCE_DASHBOARD_RENDERED,
                }
            ],
        )

    def test_consumer_templates_with_dict_datasource(self):
        """Dict datasources replace str datasources in Grafana 9."""
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(DICT_DATASOURCE_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": DICT_DATASOURCE_DASHBOARD_RENDERED,
                }
            ],
        )

    def test_consumer_templates_dashboard_and_keeps_variables(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(EXISTING_VARIABLE_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": EXISTING_VARIABLE_DASHBOARD_RENDERED,
                }
            ],
        )

    def test_consumer_templates_dashboard_and_keeps_prometheus_datasources(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(EXISTING_DATASOURCE_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        # Comparing lists of dicts is painful. Convert back to a dict so we can sort
        # and compare appropriately
        db_content = json.loads(self.harness.charm.grafana_consumer.dashboards[0]["content"])
        expected_content = json.loads(EXISTING_DATASOURCE_DASHBOARD_RENDERED)

        db_content["templating"]["list"] = sorted(
            db_content["templating"]["list"], key=lambda k: k["name"]
        )
        expected_content["templating"]["list"] = sorted(
            expected_content["templating"]["list"], key=lambda k: k["name"]
        )

        self.assertEqual(db_content, expected_content)

    def test_consumer_templates_dashboard_and_keeps_loki_datasources(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(EXISTING_LOKI_DATASOURCE_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        # Comparing lists of dicts is painful. Convert back to a dict so we can sort
        # and compare appropriately
        db_content = json.loads(self.harness.charm.grafana_consumer.dashboards[0]["content"])
        expected_content = json.loads(EXISTING_LOKI_DATASOURCE_DASHBOARD_RENDERED)

        db_content["templating"]["list"] = sorted(
            db_content["templating"]["list"], key=lambda k: k["name"]
        )
        expected_content["templating"]["list"] = sorted(
            expected_content["templating"]["list"], key=lambda k: k["name"]
        )

        self.assertEqual(db_content, expected_content)
