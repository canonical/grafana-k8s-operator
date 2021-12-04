#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
import logging
from typing import Optional

import aiohttp
from urllib3 import make_headers

logger = logging.getLogger(__name__)


class Grafana:
    """A class which abstracts access to a running instance of Grafana."""

    def __init__(
        self,
        host: Optional[str] = "localhost",
        port: Optional[int] = 3000,
        username: Optional[str] = "admin",
        pw: Optional[str] = "",
    ):
        """Utility to manage a Grafana application.

        Args:
            host: Optional host address of Grafana application, defaults to `localhost`
            port: Optional port on which Grafana service is exposed, defaults to `3000`
            username: Optional username to connect with, defaults to `admin`
            pw: Optional password to connect with, defaults to `""`
        """
        self.base_uri = f"http://{host}:{port}"
        self.headers = make_headers(basic_auth="{}:{}".format(username, pw))

    async def is_ready(self) -> bool:
        """Send a request to check readiness.

        Returns:
          True if Grafana is ready (returned database information OK); False otherwise.
        """
        res = await self.health()
        return res.get("database", "") == "ok" or False

    async def settings(self) -> dict:
        """Send a request to get Grafana global settings.

        Returns:
          All the settings as a dict
        """
        uri = f"{self.base_uri}/api/admin/settings"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri) as response:
                result = await response.json()
                return result if response.status == 200 else {}

    async def health(self) -> dict:
        """A convenience method which queries the API to see whether Grafana is really ready.

        Returns:
            Empty :dict: if it is not up, otherwise a dict containing basic API health
        """
        api_path = "api/health"
        uri = f"http://{self.base_uri}/{api_path}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri) as response:
                result = await response.json()
                return result if response.status == 200 else {}

    async def datasources(self) -> list:
        """Fetch datasources.

        Returns:
          Configured datasources, if any
        """
        uri = f"{self.base_uri}/api/datasources"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri) as response:
                result = await response.json()
                return result if response.status == 200 else []

    async def dashboards_all(self) -> list:
        """Try to get 'all' dashboards, since relation dashboards are not starred.

        Returns:
          Found dashboards, if any
        """
        uri = f"{self.base_uri}/api/search"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri, params={"starred": False}) as response:
                result = await response.json()
                return result if response.status == 200 else []

    async def dashboard_search(self, query_str: str) -> list:
        """Fetch dashboards matching a string.

        Returns:
          Found dashboards, if any
        """
        uri = f"{self.base_uri}/api/search"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri, params={"query": query_str}) as response:
                result = await response.json()
                return result if response.status == 200 else []

    async def fetch_dashboard(self, dashboard_uid: str) -> dict:
        """Get the JSON representation of a complete dashboard.

        Returns:
          A dashboard.
        """
        uri = f"{self.base_uri}/api/dashboards/uid/{dashboard_uid}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri) as response:
                result = await response.json()
                return result if response.status == 200 else {}
