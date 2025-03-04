# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import copy
import json
import unittest
import uuid
from unittest.mock import patch

from charms.grafana_k8s.v0.grafana_dashboard import (
    GrafanaDashboardProvider,
    InvalidDirectoryPathError,
)
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness

if "unittest.util" in __import__("sys").modules:
    # Show full diff in self.assertEqual.
    __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

RELATION_TEMPLATES_DATA = {
    "file:first": {
        "charm": "provider-tester",
        "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4ABnAGFdAD2IioaUXFVrEu9eEJyRf99sCsBItFjkmWby27QUlLkEOLcnhduY4+mCN01d1q200x5gz1Apuivvaa7GnxNV4yiVBn3QjP2OBr0vK+YIyoLqYOFFTVApImfM8MR4BO6WQAAAAAAAZwA0Rx1MbSEAAX1o+lt++R+2830BAAAAAARZWg==",
        "inject_dropdowns": True,
        "dashboard_alt_uid": "6291687b37603a46",
        "juju_topology": {
            "model": "testing",
            "model_uuid": "abcdefgh-1234",
            "application": "provider-tester",
            "unit": "provider-tester/0",
        },
    },
    "file:other": {
        "charm": "provider-tester",
        "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4ABoAGJdAD2IioaUXFVrEu9eFYCcHnOClmJwFGpUF9+f4scQVLIVh0dGRthp7VR8CepwuMuYM/ENRpca4OEO01DyoSAoNKyvNYzdITZDhBzuG6/HGZIDoZL34cJn3QP2kFr4HMRCtAAAAAAAmGsLclsH64QAAX5przhUpR+2830BAAAAAARZWg==",
        "inject_dropdowns": True,
        "dashboard_alt_uid": "a44939b79a5ba1d4",
        "juju_topology": {
            "model": "testing",
            "model_uuid": "abcdefgh-1234",
            "application": "provider-tester",
            "unit": "provider-tester/0",
        },
    },
}

MANUAL_TEMPLATE_DATA = {
    "file:manual": {
        "charm": "provider-tester",
        "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4ABoAGRdAD2IioaUXFVrEu9eEzLJAYcoJaoKeAoA9UD/AQKJqydHHoSE4tSLR65Xmqkzo/Sw/nNZImWBh5mIcpaLjVmjkrOlu9xza7tlno4m4n26CTdZOjfkAc3UD48RvzIVxS7j8POwIAAAEJtP70FL2ooAAYABaQAAADxRq6axxGf7AgAAAAAEWVo=",
        "inject_dropdowns": True,
        "dashboard_alt_uid": "0b73d01f7b214e98",
        "juju_topology": {
            "application": "provider-tester",
            "model": "testing",
            "model_uuid": "abcdefgh-1234",
            "unit": "provider-tester/0",
        },
    }
}


MANUAL_TEMPLATE_DATA_NO_DROPDOWNS = {
    "file:manual": {
        "charm": "provider-tester",
        "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4ABoAGRdAD2IioaUXFVrEu9eEzLJAYcoJaoKeAoA9UD/AQKJqydHHoSE4tSLR65Xmqkzo/Sw/nNZImWBh5mIcpaLjVmjkrOlu9xza7tlno4m4n26CTdZOjfkAc3UD48RvzIVxS7j8POwIAAAEJtP70FL2ooAAYABaQAAADxRq6axxGf7AgAAAAAEWVo=",
        "inject_dropdowns": False,
        "dashboard_alt_uid": "0b73d01f7b214e98",
        "juju_topology": {},
    }
}


CONSUMER_META = """
name: provider-tester
containers:
  grafana-tester:
provides:
  grafana-dashboard:
    interface: grafana_dashboard
"""


class ProviderCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaDashboardProvider(self)

        self._stored.set_default(valid_events=0)  # available data sources
        self._stored.set_default(invalid_events=0)

        self.framework.observe(
            self.provider.on.dashboard_status_changed,
            self._on_dashboard_status_changed,
        )

    def _on_dashboard_status_changed(self, event):
        if event.valid:
            self._stored.valid_events += 1
        elif event.error_message:
            self._stored.invalid_events += 1


@patch.object(uuid, "uuid4", new=lambda: "12345678")
class TestDashboardProvider(unittest.TestCase):
    def setUp(self):
        patcher = patch("charms.grafana_k8s.v0.grafana_dashboard._resolve_dir_against_charm_path")
        self.mock_resolve_dir = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_resolve_dir.return_value = "./tests/unit/dashboard_templates"
        self.harness = Harness(ProviderCharm, meta=CONSUMER_META)
        self.harness._backend.model_name = "testing"
        self.harness._backend.model_uuid = "abcdefgh-1234"
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.harness.set_leader(True)

    def test_provider_sets_dashboard_data(self):
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

    def test_provider_can_remove_programmatically_added_dashboards(self):
        self.harness.charm.provider.add_dashboard("third")

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
        expected_templates["prog:uC2Arx+2"] = {  # type: ignore
            "charm": "provider-tester",
            "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+WjAQAEdGhpcmQAAAAAtr5hbOrisy0AAR0FuC2Arx+2830BAAAAAARZWg==",
            "inject_dropdowns": True,
            "dashboard_alt_uid": "9f3746a8f16304dd",
            "juju_topology": {
                "model": "testing",
                "model_uuid": "abcdefgh-1234",
                "application": "provider-tester",
                "unit": "provider-tester/0",
            },
        }

        self.assertDictEqual(expected_data, actual_data)
        self.harness.charm.provider.remove_non_builtin_dashboards()
        self.assertEqual(
            expected_data_builtin_dashboards,
            json.loads(
                self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
            ),
        )

    def test_provider_cannot_remove_builtin_dashboards(self):
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

        self.harness.charm.provider.remove_non_builtin_dashboards()
        self.assertEqual(
            expected_data,
            json.loads(
                self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
            ),
        )

    def test_provider_destroys_old_data_on_rescan(self):
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

        self.harness.charm.provider._dashboards_path = "./tests/unit/manual_dashboards"
        self.harness.charm.provider._reinitialize_dashboard_data()
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        expected_data = {
            "templates": MANUAL_TEMPLATE_DATA,
            "uuid": "12345678",
        }
        self.assertDictEqual(expected_data, actual_data)

    def test_provider_can_rescan_and_avoid_dropdowns(self):
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

        self.harness.charm.provider._dashboards_path = "./tests/unit/manual_dashboards"
        self.harness.charm.provider._reinitialize_dashboard_data(inject_dropdowns=False)
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        expected_data = {
            "templates": MANUAL_TEMPLATE_DATA_NO_DROPDOWNS,
            "uuid": "12345678",
        }
        self.assertDictEqual(expected_data, actual_data)

    def test_provider_empties_data_on_exception(self):
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

        self.mock_resolve_dir.side_effect = InvalidDirectoryPathError("foo", "bar")
        self.harness.charm.provider._reinitialize_dashboard_data()
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        empty_data = {
            "templates": {},
            "uuid": "12345678",
        }
        self.assertDictEqual(empty_data, actual_data)

    def test_provider_clears_data_on_empty_dir(self):
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

        self.harness.charm.provider._dashboards_path = "./tests/unit/empty_dashboards"
        self.harness.charm.provider._reinitialize_dashboard_data()
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        empty_data = {
            "templates": {},
            "uuid": "12345678",
        }
        self.assertDictEqual(empty_data, actual_data)
