#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
from unittest.mock import PropertyMock, call, patch

from charms.grafana_k8s.v0.grafana_auth import AuthRequirer
from ops import testing
from ops.charm import CharmBase

METADATA = """
name: requirer-tester
containers:
  auth-tester:
requires:
  grafana-auth:
    interface: grafana_auth
"""

CHARM_LIB_PATH = "charms.grafana_k8s.v0.grafana_auth"

EXAMPLE_URLS = ["www.example.com"]
EXAMPLE_AUTH_CONF = {
    "proxy": {
        "enabled": True,
        "header_name": "X-WEBAUTH-USER",
        "header_property": "username",
        "auto_sign_up": True,
    }
}


class RequirerCharm(CharmBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.proxy_provider = AuthRequirer(self, urls=EXAMPLE_URLS)


class RequirerCharmRefreshEvent(CharmBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.proxy_provider = AuthRequirer(
            self, urls=EXAMPLE_URLS, refresh_event=self.on.auth_tester_pebble_ready
        )


class TestAuthRequirer(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(RequirerCharm, meta=METADATA)
        self.harness.set_leader(True)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_given_unit_is_leader_when_auth_relation_joined_event_then_urls_are_set_in_relation_data(
        self,
    ):
        relation_id = self.harness.add_relation("grafana-auth", "provider")
        self.harness.add_relation_unit(relation_id, "provider/0")
        relation_data = self.harness.get_relation_data(relation_id, self.harness.model.app.name)
        self.assertIn("urls", relation_data)
        urls = json.loads(relation_data["urls"])
        expected_urls = EXAMPLE_URLS
        self.assertEqual(expected_urls, urls)

    def test_given_unit_is_not_leader_when_auth_relation_joined_event_then_urls_are_not_set_in_relation_data(
        self,
    ):
        self.harness.set_leader(False)
        relation_id = self.harness.add_relation("grafana-auth", "provider")
        self.harness.add_relation_unit(relation_id, "provider/0")
        relation_data = self.harness.get_relation_data(relation_id, self.harness.model.app.name)
        self.assertNotIn("urls", relation_data)

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_auth_conf_in_relation_data_and_unit_is_leader_when_refresh_event_then_auth_conf_avaialble_event_is_emitted(
        self, mock_auth_conf_available_event
    ):
        relation_id = self.harness.add_relation("grafana-auth", "provider")
        self.harness.add_relation_unit(relation_id, "provider/0")
        auth_conf = {"auth": json.dumps(EXAMPLE_AUTH_CONF)}
        self.harness.update_relation_data(
            relation_id=relation_id, key_values=auth_conf, app_or_unit="provider"
        )
        self.harness.container_pebble_ready("auth-tester")
        calls = [
            call().emit(
                auth=EXAMPLE_AUTH_CONF,
                relation_id=relation_id,
            ),
            call().emit(
                auth=EXAMPLE_AUTH_CONF,
                relation_id=relation_id,
            ),
        ]
        mock_auth_conf_available_event.assert_has_calls(calls, any_order=True)

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_auth_conf_in_relation_data_and_unit_is_leader_when_relation_changed_event_then_auth_conf_avaialble_event_is_emitted(
        self, mock_auth_conf_available_event
    ):
        relation_id = self.harness.add_relation("grafana-auth", "provider")
        self.harness.add_relation_unit(relation_id, "provider/0")
        auth_conf = {"auth": json.dumps(EXAMPLE_AUTH_CONF)}
        self.harness.update_relation_data(relation_id, "provider", auth_conf)
        calls = [
            call().emit(
                auth=EXAMPLE_AUTH_CONF,
                relation_id=relation_id,
            ),
        ]
        mock_auth_conf_available_event.assert_has_calls(calls)

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_relation_not_yet_created_when_refresh_event_then_auth_conf_avaialble_event_is_not_emitted(
        self, mock_auth_conf_available_event
    ):
        self.harness.container_pebble_ready("auth-tester")
        mock_auth_conf_available_event.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_auth_conf_not_in_relation_data_when_relation_changed_event_then_auth_conf_avaialble_event_is_not_emitted(
        self, mock_auth_conf_available_event
    ):
        relation_id = self.harness.add_relation("grafana-auth", "provider")
        self.harness.add_relation_unit(relation_id, "provider/0")
        self.harness.update_relation_data(relation_id, "provider", {})
        mock_auth_conf_available_event.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_given_auth_conf_not_in_relation_data_when_refresh_event_then_auth_conf_avaialble_event_is_not_emitted(
        self, mock_auth_conf_available_event
    ):
        relation_id = self.harness.add_relation("grafana-auth", "provider")
        self.harness.add_relation_unit(relation_id, "provider/0")
        self.harness.container_pebble_ready("auth-tester")
        mock_auth_conf_available_event.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_default_refresh_event_is_update_status_for_multiple_containers(
        self,
        mock_auth_conf_available_event,
    ):
        meta = """
        name: requirer-tester
        containers:
            auth-tester:
            another-container:
        requires:
            grafana-auth:
                interface: grafana_auth
        """
        harness = testing.Harness(RequirerCharm, meta=meta)
        harness.set_leader(True)
        harness.begin()
        relation_id = harness.add_relation("grafana-auth", "provider")
        harness.add_relation_unit(relation_id, "provider/0")
        auth_conf = {"auth": json.dumps(EXAMPLE_AUTH_CONF)}
        harness.update_relation_data(
            relation_id=relation_id, key_values=auth_conf, app_or_unit="provider"
        )
        harness.charm.on.update_status.emit()
        calls = [
            call().emit(
                auth=EXAMPLE_AUTH_CONF,
                relation_id=relation_id,
            ),
            call().emit(
                auth=EXAMPLE_AUTH_CONF,
                relation_id=relation_id,
            ),
        ]
        mock_auth_conf_available_event.assert_has_calls(calls, any_order=True)

    @patch(
        f"{CHARM_LIB_PATH}.AuthRequirerCharmEvents.auth_conf_available",
        new_callable=PropertyMock,
    )
    def test_refresh_event_is_pebble_ready_when_provided_as_parameter(
        self,
        mock_auth_conf_available_event,
    ):
        meta = """
        name: requirer-tester
        containers:
            auth-tester:
            another-container:
        requires:
            grafana-auth:
                interface: grafana_auth
        """
        harness = testing.Harness(RequirerCharmRefreshEvent, meta=meta)
        harness.set_leader(True)
        harness.begin()
        relation_id = harness.add_relation("grafana-auth", "provider")
        harness.add_relation_unit(relation_id, "provider/0")
        auth_conf = {"auth": json.dumps(EXAMPLE_AUTH_CONF)}
        harness.update_relation_data(
            relation_id=relation_id, key_values=auth_conf, app_or_unit="provider"
        )
        harness.container_pebble_ready("auth-tester")
        calls = [
            call().emit(
                auth=EXAMPLE_AUTH_CONF,
                relation_id=relation_id,
            ),
            call().emit(
                auth=EXAMPLE_AUTH_CONF,
                relation_id=relation_id,
            ),
        ]
        mock_auth_conf_available_event.assert_has_calls(calls, any_order=True)
