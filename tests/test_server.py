# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
import urllib3

from unittest.mock import patch

from lib.charms.grafana.v1.grafana_server import Grafana


class TestServer(unittest.TestCase):
    def setUp(self):
        self.grafana = Grafana("localhost", "9090")

    @patch("lib.charms.grafana.v1.grafana_server.urllib3.PoolManager.request")
    def test_grafana_server_returns_valid_data(self, request):
        version = "7.2.1"
        request.return_value.data = bytes(
            json.dumps(
                {
                    "commit": "12345abcd",
                    "database": "ok",
                    "version": version,
                }
            ),
            encoding="utf-8",
        )
        build_info = self.grafana.build_info
        got_version = build_info.get("version", None)
        self.assertIsNotNone(got_version)
        self.assertEqual(got_version, version)

    @patch("lib.charms.grafana.v1.grafana_server.urllib3.PoolManager.request")
    def test_grafana_server_max_retry_test(self, request):
        request.side_effect = urllib3.exceptions.MaxRetryError(
            None, "/", "We shouldn't get here"
        )
        build_info = self.grafana.build_info
        self.assertEqual(build_info, {})

    @patch("lib.charms.grafana.v1.grafana_server.urllib3.PoolManager.request")
    def test_grafana_server_becomes_ready(self, request):
        version = "7.2.1"
        request.return_value.data = bytes(
            json.dumps(
                {
                    "commit": "12345abcd",
                    "database": "ok",
                    "version": version,
                }
            ),
            encoding="utf-8",
        )
        self.assertIsNotNone(self.grafana.is_ready)
        self.assertTrue(self.grafana.is_ready)

    @patch("lib.charms.grafana.v1.grafana_server.urllib3.PoolManager.request")
    def test_grafana_server_is_unready(self, request):
        request.return_value.data = bytes(
            json.dumps(
                {
                    "database": "fail",
                }
            ),
            encoding="utf-8",
        )
        self.assertIsNotNone(self.grafana.is_ready)
        self.assertFalse(self.grafana.is_ready)
