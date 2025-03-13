#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
from typing import Optional

import aiohttp
from tenacity import retry
from urllib3 import make_headers


class Grafana:
    """A class which abstracts access to a running instance of Grafana."""

    def __init__(
        self,
        *,
        host: Optional[str] = "localhost",
        port: Optional[int] = 3000,
        path: Optional[str] = "",
        username: Optional[str] = "admin",
        pw: Optional[str] = "",
    ):
        """Utility to manage a Grafana application.

        Args:
            host: Optional host address of Grafana application, defaults to `localhost`
            port: Optional port on which Grafana service is exposed, defaults to `3000`
            path: Optional path (e.g. due to ingress).
            username: Optional username to connect with, defaults to `admin`
            pw: Optional password to connect with, defaults to `""`
        """
        path = ("/" + path.lstrip("/")) if path else ""
        self.base_uri = "http://{}:{}{}".format(host, port, path)
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
        api_path = "api/admin/settings"
        uri = "{}/{}".format(self.base_uri, api_path)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri) as response:
                result = await response.json()
                return result if response.status == 200 else {}

    @retry
    async def health(self) -> dict:
        """A convenience method which queries the API to see whether Grafana is really ready.

        Returns:
            Empty :dict: if it is not up, otherwise a dict containing basic API health
        """
        api_path = "api/health"
        uri = "{}/{}".format(self.base_uri, api_path)

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri) as response:
                result = await response.json()
                if response.status == 200:
                    return result
                raise Exception("Grafana is not ready")

    async def datasources(self) -> list:
        """Fetch datasources.

        Returns:
          Configured datasources, if any
        """
        api_path = "api/datasources"
        uri = "{}/{}".format(self.base_uri, api_path)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri) as response:
                result = await response.json()
                return result if response.status == 200 else []

    async def dashboards_all(self) -> list:
        """Try to get 'all' dashboards, since relation dashboards are not starred.

        Returns:
          Found dashboards, if any
        """
        api_path = "api/search"
        uri = "{}/{}".format(self.base_uri, api_path)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri, params={"starred": "false"}) as response:
                result = await response.json()
                return result if response.status == 200 else []

    async def dashboard_search(self, query_str: str) -> list:
        """Fetch dashboards matching a string.

        Returns:
          Found dashboards, if any
        """
        api_path = "api/search"
        uri = "{}/{}".format(self.base_uri, api_path)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri, params={"query": query_str}) as response:
                result = await response.json()
                return result if response.status == 200 else []

    async def fetch_dashboard(self, dashboard_uid: str) -> dict:
        """Get the JSON representation of a complete dashboard.

        Returns:
          A dashboard.
        """
        api_path = "api/dashboards/uid/{}".format(dashboard_uid)
        uri = "{}/{}".format(self.base_uri, api_path)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri) as response:
                result = await response.json()
                return result if response.status == 200 else {}

    async def fetch_org(self, name: str) -> dict:
        """Get the JSON representation of orgs.

        Returns:
          Organisation.
        """
        api_path = f"/api/orgs/name/{name}"
        uri = f"{self.base_uri}{api_path}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(uri) as response:
                result = await response.json()
                return result if response.status == 200 else {}

    async def create_org(self, name: str) -> dict:
        """Create org.

        Returns:
          Dict containing the orgId.
        """
        api_path = "/api/orgs"
        uri = f"{self.base_uri}{api_path}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(uri, json={"name": name}) as response:
                result = await response.json()
                return result if response.status == 200 else {}
