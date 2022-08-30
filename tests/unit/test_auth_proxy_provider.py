#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
from unittest.mock import PropertyMock, call, patch

from charms.grafana_auth.v0.grafana_auth import AuthProvider, GrafanaAuthProxyProvider
from ops import testing
from ops.charm import CharmBase

METADATA = """
name: provider-tester
containers:
  auth-tester:
provides:
  grafana-auth:
    interface: grafana_auth
"""

CHARM_LIB_PATH = "charms.grafana_auth.v0.grafana_auth"

EXAMPLE_URLS = ["www.example.com"]


class DefaultAuthProxyProviderCharm(CharmBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.proxy_provider = GrafanaAuthProxyProvider(
            self,
        )


class TestDefaultGrafanaAuthProxyProvider(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(DefaultAuthProxyProviderCharm, meta=METADATA)
        self.harness.set_leader(True)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_given_unit_is_leader_when_auth_relation_joined_event_then_default_auth_config_is_set_in_relation_data(
        self,
    ):
        relation_id = self.harness.add_relation("grafana-auth", "requirer")
        self.harness.add_relation_unit(relation_id, "requirer/0")
        relation_data = self.harness.get_relation_data(relation_id, self.harness.model.app.name)
        self.assertIn("auth", relation_data)
        auth_config = json.loads(relation_data["auth"])
        expected_default_config = {
            "proxy": {
                "enabled": True,
                "header_name": "X-WEBAUTH-USER",
                "header_property": "username",
                "auto_sign_up": True,
            }
        }
        self.assertDictEqual(expected_default_config, auth_config)

    def test_given_unit_is_not_leader_when_auth_relation_joined_event_then_auth_config_is_not_set_in_relation_data(
        self,
    ):
        self.harness.set_leader(False)
        relation_id = self.harness.add_relation("grafana-auth", "requirer")
        self.harness.add_relation_unit(relation_id, "requirer/0")
        relation_data = self.harness.get_relation_data(relation_id, self.harness.model.app.name)
        self.assertNotIn("auth", relation_data)

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.urls_available",
        new_callable=PropertyMock,
    )
    def test_given_urls_are_in_relation_data_and_unit_is_leader_when_pebble_ready_event_then_urls_avaialble_event_is_emitted(
        self, mock_urls_available_event
    ):
        relation_id = self.harness.add_relation("grafana-auth", "requirer")
        self.harness.add_relation_unit(relation_id, "requirer/0")
        urls = {"urls": json.dumps(EXAMPLE_URLS)}
        self.harness.update_relation_data(
            relation_id=relation_id, key_values=urls, app_or_unit="requirer"
        )
        self.harness.container_pebble_ready("auth-tester")
        calls = [
            call().emit(
                urls=EXAMPLE_URLS,
                relation_id=relation_id,
            ),
            call().emit(
                urls=EXAMPLE_URLS,
                relation_id=relation_id,
            ),
        ]
        mock_urls_available_event.assert_has_calls(calls, any_order=True)

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.urls_available",
        new_callable=PropertyMock,
    )
    def test_given_urls_in_relation_data_and_unit_is_leader_when_relation_changed_event_then_urls_avaialble_event_is_emitted(
        self, mock_urls_available_event
    ):
        relation_id = self.harness.add_relation("grafana-auth", "requirer")
        self.harness.add_relation_unit(relation_id, "requirer/0")
        urls = {"urls": json.dumps(EXAMPLE_URLS)}
        self.harness.update_relation_data(relation_id, "requirer", urls)
        calls = [
            call().emit(
                urls=EXAMPLE_URLS,
                relation_id=relation_id,
            ),
        ]
        mock_urls_available_event.assert_has_calls(calls)

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.urls_available",
        new_callable=PropertyMock,
    )
    def test_given_relation_not_yet_created_when_pebble_ready_event_then_urls_avaialble_event_is_not_emitted(
        self, mock_urls_available_event
    ):
        self.harness.container_pebble_ready("auth-tester")
        mock_urls_available_event.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.urls_available",
        new_callable=PropertyMock,
    )
    def test_given_urls_are_not_in_relation_data_when_relation_changed_event_then_urls_avaialble_event_is_not_emitted(
        self, mock_urls_available_event
    ):
        relation_id = self.harness.add_relation("grafana-auth", "requirer")
        self.harness.add_relation_unit(relation_id, "requirer/0")
        self.harness.update_relation_data(relation_id, "requirer", {})
        mock_urls_available_event.assert_not_called()

    @patch(
        f"{CHARM_LIB_PATH}.AuthProviderCharmEvents.urls_available",
        new_callable=PropertyMock,
    )
    def test_given_urls_are_not_in_relation_data_when_pebble_ready_event_then_urls_avaialble_event_is_not_emitted(
        self, mock_urls_available_event
    ):
        relation_id = self.harness.add_relation("grafana-auth", "requirer")
        self.harness.add_relation_unit(relation_id, "requirer/0")
        self.harness.container_pebble_ready("auth-tester")
        mock_urls_available_event.assert_not_called()


class ProviderNonDefaultCharm(CharmBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.proxy_provider = GrafanaAuthProxyProvider(
            self, header_property="email", sync_ttl=10, auto_sign_up=False
        )


class TestNonDefaultGrafanaAuthProxyProvider(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(ProviderNonDefaultCharm, meta=METADATA)
        self.harness.set_leader(True)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_given_unit_is_leader_when_auth_relation_joined_event_then_auth_config_is_set_in_relation_data(
        self,
    ):
        relation_id = self.harness.add_relation("grafana-auth", "requirer")
        self.harness.add_relation_unit(relation_id, "requirer/0")
        relation_data = self.harness.get_relation_data(relation_id, self.harness.model.app.name)
        self.assertIn("auth", relation_data)
        auth_config = json.loads(relation_data["auth"])
        expected_default_config = {
            "proxy": {
                "enabled": True,
                "header_name": "X-WEBAUTH-USER",
                "header_property": "email",
                "auto_sign_up": False,
                "sync_ttl": 10,
            }
        }
        self.assertDictEqual(expected_default_config, auth_config)


class MissingModeProviderCharm(CharmBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.proxy_provider = AuthProvider(self, relationship_name="grafana-auth")


class TestMissingModeProvider(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(MissingModeProviderCharm, meta=METADATA)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_given_auth_config_is_missing_when_auth_relation_joined_event_then_auth_config_is_not_set_in_relation_data(
        self,
    ):
        relation_id = self.harness.add_relation("grafana-auth", "requirer")
        self.harness.add_relation_unit(relation_id, "requirer/0")
        relation_data = self.harness.get_relation_data(relation_id, self.harness.model.app.name)
        self.assertNotIn("auth", relation_data)
