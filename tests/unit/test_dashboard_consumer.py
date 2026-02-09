# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import base64
import json
import yaml
import lzma
import unittest
import uuid
from unittest.mock import patch
from pathlib import Path
from helpers import conv_dashboard_list
from charms.grafana_k8s.v0.grafana_dashboard import (
    DATASOURCE_TEMPLATE_DROPDOWNS,
    TOPOLOGY_TEMPLATE_DROPDOWNS,
    GrafanaDashboardConsumer,
)
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness, Relation, PeerRelation, Context, State
from cosl import LZMABase64
if "unittest.util" in __import__("sys").modules:
    # Show full diff in self.assertEqual.
    __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

MODEL_INFO = {"name": "testing", "uuid": "abcdefgh-1234"}
TEMPLATE_DROPDOWNS = TOPOLOGY_TEMPLATE_DROPDOWNS + DATASOURCE_TEMPLATE_DROPDOWNS

DASHBOARD_TEMPLATE = """
{
    "panels": {
        "data": "label_values(up, juju_unit)"
    },
    "uid": "deadbeef"
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
        "uid": "deadbeef",
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
    }
)


DASHBOARD_RENDERED_NO_DROPDOWNS = json.dumps(
    {
        "panels": {"data": "label_values(up, juju_unit)"},
        "templating": {"list": list(DATASOURCE_TEMPLATE_DROPDOWNS)},
        "uid": "deadbeef",
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
    ],
    "uid": "deadbeef"
}
"""

VARIABLE_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {"data": "label_values(up, juju_unit)", "datasource": "${prometheusds}"},
        ],
        "uid": "deadbeef",
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
    }
)

ROW_ONLY_DASHBOARD_TEMPLATE = """
{
    "rows": [
        {
            "panels": [
                {
                    "data": "label_values(up, juju_unit)",
                    "datasource": "$replace_me"
                }
            ]
        },
        {
            "panels": [
                {
                    "data": "label_values(up, juju_charm)",
                    "datasource": "$replace_me"
                }
            ]
        }
    ],
    "uid": "deadbeef"
}
"""

ROW_ONLY_DASHBOARD_RENDERED = json.dumps(
    {
        "rows": [
            {
                "panels": [
                    {"data": "label_values(up, juju_unit)", "datasource": "${prometheusds}"},
                ],
            },
            {
                "panels": [
                    {"data": "label_values(up, juju_charm)", "datasource": "${prometheusds}"},
                ],
            },
        ],
        "uid": "deadbeef",
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
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
    ],
    "uid": "deadbeef"
}
"""

INPUT_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {"data": "label_values(up, juju_unit)", "datasource": "${prometheusds}"},
        ],
        "uid": "deadbeef",
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
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
    ],
    "uid": "deadbeef"
}
"""

NULL_DATASOURCE_DASHBOARD_RENDERED = json.dumps(
    {
        "panels": [
            {"data": "label_values(up, juju_unit)", "datasource": "${prometheusds}"},
            {"data": "Row separator", "datasource": None},
        ],
        "uid": "deadbeef",
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
    }
)

BUILTIN_DATASOURCE_DASHBOARD_TEMPLATE = """
{
    "annotations": {
        "list": [
            {
                "builtIn": 1,
                "datasource": "grafana",
                "enable": true,
                "type": "dashboard"
            }
        ]
    },
    "panels": [
        {
            "datasource": "grafana",
            "panels": [],
            "targets": [
                {
                    "datasource": "grafana",
                    "refId": "A"
                }
            ],
            "title": "foo"
        }
    ],
    "uid": "deadbeef"
}
"""

BUILTIN_DATASOURCE_DASHBOARD_RENDERED = json.dumps(
    {
        "annotations": {
            "list": [{"builtIn": 1, "datasource": "grafana", "enable": True, "type": "dashboard"}]
        },
        "panels": [
            {
                "datasource": "grafana",
                "panels": [],
                "targets": [{"datasource": "grafana", "refId": "A"}],
                "title": "foo",
            }
        ],
        "uid": "deadbeef",
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
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
    "uid": "deadbeef",
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
        "uid": "deadbeef",
        "templating": {
            "list": list(reversed(TEMPLATE_DROPDOWNS))
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
    "uid": "deadbeef",
    "templating": {
        "list": [
            {
                "description": null,
                "error": null,
                "hide": 0,
                "includeAll": true,
                "label": "Prometheus datasource",
                "multi": true,
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
        "uid": "deadbeef",
        "templating": {
            "list": list(reversed(TEMPLATE_DROPDOWNS))
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
    "uid": "deadbeef",
    "templating": {
        "list": [
            {
                "description": null,
                "error": null,
                "hide": 0,
                "includeAll": true,
                "label": "Loki datasource",
                "multi": true,
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
        "uid": "deadbeef",
        "templating": {
            "list": list(reversed(TEMPLATE_DROPDOWNS))
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
    ],
    "uid": "deadbeef"
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
        "uid": "deadbeef",
        "templating": {"list": list(TEMPLATE_DROPDOWNS)},
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
        meta = open("charmcraft.yaml")
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

    @patch("grafana.Grafana._restart_grafana")
    def test_consumer_notifies_on_new_dashboards(self, restart_patcher):
        self.assertEqual(len(self.harness.charm.grafana_consumer.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_charm_relations()
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            conv_dashboard_list(self.harness.charm.grafana_consumer.dashboards),
            conv_dashboard_list([
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": DASHBOARD_RENDERED,
                    "dashboard_uid": "deadbeef",
                    "dashboard_version": 0,
                    "dashboard_title": "",
                }
            ]),
        )
        # assert restart is not called
        assert restart_patcher.call_count == 0

    @patch("grafana.Grafana._restart_grafana")
    def test_consumer_notifies_on_new_dashboards_without_dropdowns(self, restart_patcher):
        self.assertEqual(len(self.harness.charm.grafana_consumer.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_without_dropdowns(DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)


        self.assertEqual(conv_dashboard_list(self.harness.charm.grafana_consumer.dashboards), conv_dashboard_list([{
            "id": "file:tester",
            "relation_id": "2",
            "charm": "grafana-k8s",
            "content": DASHBOARD_RENDERED_NO_DROPDOWNS,
            "dashboard_uid": "deadbeef",
            "dashboard_version": 0,
            "dashboard_title": "",
        }]))

        # assert restart is not called
        assert restart_patcher.call_count == 0

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
            self.assertIn("Invalid JSON in Grafana dashboard 'file:tester'", "\n".join(cm.output))  # type: ignore

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
                    "dashboard_uid": "deadbeef",
                    "dashboard_version": 0,
                    "dashboard_title": "",
                }
            ],
        )

    def test_consumer_templates_rows(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(ROW_ONLY_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": ROW_ONLY_DASHBOARD_RENDERED,
                    "dashboard_uid": "deadbeef",
                    "dashboard_version": 0,
                    "dashboard_title": "",
                }
            ],
        )

    def test_consumer_templates_dashboard_with_inputs(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(INPUT_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            conv_dashboard_list(self.harness.charm.grafana_consumer.dashboards),
            conv_dashboard_list([
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": INPUT_DASHBOARD_RENDERED,
                    "dashboard_uid": "deadbeef",
                    "dashboard_version": 0,
                    "dashboard_title": "",
                }
            ]),
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
                    "dashboard_uid": "deadbeef",
                    "dashboard_version": 0,
                    "dashboard_title": "",
                }
            ],
        )

    def test_consumer_templates_with_builtin_datasource(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer._stored.dashboards), 0)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 0)
        self.setup_different_dashboard(BUILTIN_DATASOURCE_DASHBOARD_TEMPLATE)
        self.assertEqual(self.harness.charm._stored.dashboard_events, 1)

        self.assertEqual(
            self.harness.charm.grafana_consumer.dashboards,
            [
                {
                    "id": "file:tester",
                    "relation_id": "2",
                    "charm": "grafana-k8s",
                    "content": BUILTIN_DATASOURCE_DASHBOARD_RENDERED,
                    "dashboard_uid": "deadbeef",
                    "dashboard_version": 0,
                    "dashboard_title": "",
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
                    "dashboard_uid": "deadbeef",
                    "dashboard_version": 0,
                    "dashboard_title": "",
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
                    "dashboard_uid": "deadbeef",
                    "dashboard_version": 0,
                    "dashboard_title": "",
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

MINIMAL_TEMPLATE_WITH_DROPDOWNS = {
  "title": "Mimir / Config (Minimal)",
  "uid": "mimir-config-minimal",
  "schemaVersion": 37,
  "version": 1,
  "editable": "true",
  "refresh": "10s",
  "timezone": "utc",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "panels": [],
  "templating": {
    "list": [
      {
        "allValue": ".*",
        "current": {
          "selected": "false",
          "text": "All",
          "value": "$__all"
        },
        "datasource": {
          "uid": "${prometheusds}"
        },
        "definition": "label_values(up{juju_model=~\"$juju_model\",juju_model_uuid=~\"$juju_model_uuid\",juju_application=~\"$juju_application\"},juju_unit)",
        "hide": 0,
        "includeAll": "true",
        "label": "Juju unit",
        "multi": "true",
        "name": "juju_unit",
        "options": [],
        "query": {
          "query": "label_values(up{juju_model=~\"$juju_model\",juju_model_uuid=~\"$juju_model_uuid\",juju_application=~\"$juju_application\"},juju_unit)",
          "refId": "StandardVariableQuery"
        },
        "refresh": 1,
        "type": "query"
      },
      {
        "allValue": ".*",
        "current": {
          "selected": "true",
          "text": "All",
          "value": "$__all"
        },
        "datasource": {
          "uid": "${prometheusds}"
        },
        "definition": "label_values(up{juju_model=~\"$juju_model\",juju_model_uuid=~\"$juju_model_uuid\"},juju_application)",
        "hide": 0,
        "includeAll": "true",
        "label": "Juju application",
        "multi": "true",
        "name": "juju_application",
        "options": [],
        "query": {
          "query": "label_values(up{juju_model=~\"$juju_model\",juju_model_uuid=~\"$juju_model_uuid\"},juju_application)",
          "refId": "StandardVariableQuery"
        },
        "refresh": 1,
        "type": "query"
      },
      {
        "allValue": ".*",
        "current": {
          "selected": "true",
          "text": "All",
          "value": "$__all"
        },
        "datasource": {
          "uid": "${prometheusds}"
        },
        "definition": "label_values(up{juju_model=~\"$juju_model\"},juju_model_uuid)",
        "hide": 0,
        "includeAll": "true",
        "label": "Juju model uuid",
        "multi": "true",
        "name": "juju_model_uuid",
        "options": [],
        "query": {
          "query": "label_values(up{juju_model=~\"$juju_model\"},juju_model_uuid)",
          "refId": "StandardVariableQuery"
        },
        "refresh": 1,
        "type": "query"
      },
      {
        "allValue": ".*",
        "current": {
          "selected": "false",
          "text": "All",
          "value": "$__all"
        },
        "datasource": {
          "uid": "${prometheusds}"
        },
        "definition": "label_values(up,juju_model)",
        "hide": 0,
        "includeAll": "true",
        "label": "Juju model",
        "multi": "true",
        "name": "juju_model",
        "options": [],
        "query": {
          "query": "label_values(up,juju_model)",
          "refId": "StandardVariableQuery"
        },
        "refresh": 1,
        "type": "query"
      },
      {
        "current": {
          "selected": "true",
          "text": ["All"],
          "value": ["$__all"]
        },
        "hide": 0,
        "includeAll": "true",
        "label": "Prometheus datasource",
        "multi": "true",
        "name": "prometheusds",
        "options": [],
        "query": "prometheus",
        "refresh": 1,
        "type": "datasource"
      }
    ]
  }
}

relation_data = {
    "dashboards": json.dumps({
        "templates": {
            "file:mimir-config-minimal": {
                "charm": "mimir",
                "content": LZMABase64.compress(json.dumps(MINIMAL_TEMPLATE_WITH_DROPDOWNS)),
            }
        },
        "uuid": "some_uuid",
    })
}

def test_no_dashboard_dropdown_duplication(ctx:Context, containers):
    """Ensure no duplication of dropdowns.

    When a dashboard is provided over relation data, it may already come with dropdowns
    for the Juju Topology. In such cases, we want to ensure that the `grafana_dashboard`
    library does not inject these topology-related dropdowns again.

    To test this, we simulate a scenario in which a dashboard providing charm has sent
    the `MINIMAL_TEMPLATE_WITH_DROPDOWNS` dashboard over relation data. This dashboard already
    comes with 6 dropdowns for the Juju Topology. In the scenario test, we'll have the context
    run two events:
      - First, a `relation_created` event, in which the library writes the provided dashboards
      to peer relation data.
      - Second, a generic `update_status` event which causes the dashboards saved to peer data
      to be eventually written to disk.

    Finally, we'll read the dashboards saved to disk and ensure they still contain the same number
    of dropdowns, which is 6, one for each element of the Juju Topology.
    """
    dashboards_path = "/etc/grafana/provisioning/dashboards"

    # GIVEN a relation to a dashboard provider with relation data,
    # where the relation data contains a template that already comes with dropdowns
    # AND a peer relation.
    dashboard_relation = Relation(endpoint="grafana-dashboard", remote_app_data=relation_data)

    # The peer relation is necessary as this is where the dashboards will be stored before being written to disk.
    peer_relation = PeerRelation(endpoint="grafana", peers_data={1: {}})
    state = State(relations={dashboard_relation, peer_relation}, containers=containers, leader=True)

    # First, create the relation so dashboards are written to peer data.
    with ctx(ctx.on.relation_created(dashboard_relation), state) as mgr:
        state_out = mgr.run()

        # Now that peer relation data contains the dashboards,
        # we simulate another event.
        with ctx(ctx.on.update_status(), state_out) as mgr:

          state_out = mgr.run()
          agent = state_out.get_container("grafana")

          # Get the filesystem and read the dashboard file for Mimir.
          # We search for the string `mimir` in the filename because
          # `MINIMAL_TEMPLATE_WITH_DROPDOWNS` has the name `mimir-config-minimal`.
          # The dashboard name on disk reflects the file name.
          fs = agent.get_filesystem(ctx)
          dashboard_files = fs.joinpath(*dashboards_path.strip("/").split("/"))
          mimir_dashboard = [d for d in dashboard_files.iterdir() if "mimir" in d.name][0]
          dashboard_content = yaml.safe_load(Path(mimir_dashboard).read_text())

          # THEN in the Mimir dashboard being written to the `grafana` container, no duplication of dropdowns happens.
          # This means, we still expect 6 elements in the `list` sub-section of the `templating` section.
          assert len(dashboard_content["templating"]["list"]) == 6
