# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
from unittest.mock import patch

import urllib3

from grafana_client import Grafana


class TestServer(unittest.TestCase):
    def setUp(self):
        self.grafana = Grafana("localhost:9090")

    @patch("src.grafana_client.urllib3.PoolManager.request")
    def test_grafana_client_returns_valid_data(self, request):
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

    @patch("src.grafana_client.urllib3.PoolManager.request")
    def test_grafana_client_max_retry_test(self, request):
        # Ignore mypy here so we don't have to mock out absolutely everything
        request.side_effect = urllib3.exceptions.MaxRetryError(None, "/", "We shouldn't get here")  # type: ignore
        build_info = self.grafana.build_info
        self.assertEqual(build_info, {})

    @patch("src.grafana_client.urllib3.PoolManager.request")
    def test_grafana_client_becomes_ready(self, request):
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

    @patch("src.grafana_client.urllib3.PoolManager.request")
    def test_grafana_client_is_unready(self, request):
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
