#  Copyright 2021 Canonical Ltd.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""A module used for interacting with a running Grafana instance."""

import json

import urllib3


class Grafana:
    """A class that represents a running Grafana instance."""

    def __init__(self, host: str, port: int) -> None:
        """A class to bring up and check a Grafana server.

        Args:
            host: a :str: which indicates the hostname
            port: an :int: to listen on
        """
        self.host = host
        self.port = port
        self.http = urllib3.PoolManager()

    @property
    def is_ready(self) -> bool:
        """Checks whether the Grafana server is up and running yet.

        Returns:
            :bool: indicating whether or not the server is ready
        """
        return True if self.build_info.get("database", None) == "ok" else False

    def password_has_been_changed(self, username: str, passwd: str) -> bool:
        """Checks whether the admin password has been changed from default generated.

        Returns:
            :bool: indicating whether the password was changed.
        """
        api_path = "/api/org"
        url = "http://{}:{}/{}".format(self.host, self.port, api_path)
        headers = urllib3.make_headers(basic_auth="{}:{}".format(username, passwd))

        try:
            res = self.http.request("GET", url, headers=headers)
            return True if "invalid username" in res.data.decode("utf8") else False
        except urllib3.exceptions.HTTPError:
            return True

    @property
    def build_info(self) -> dict:
        """A convenience method which queries the API to see whether Grafana is really ready.

        Returns:
            Empty :dict: if it is not up, otherwise a dict containing basic API health
        """
        api_path = "api/health"
        url = "http://{}:{}/{}".format(self.host, self.port, api_path)

        try:
            response = self.http.request("GET", url)
        except urllib3.exceptions.MaxRetryError:
            return {}

        info = json.loads(response.data.decode("utf-8"))
        if info["database"] == "ok":
            return info
        else:
            return {}
