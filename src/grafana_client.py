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

from urllib3 import exceptions
import urllib3


class GrafanaCommError(Exception):
    """Raised when comm fails unexpectedly."""


class GrafanaClient:
    """Client for interacting with the Grafana API."""

    def __init__(self, endpoint_url: str) -> None:
        """A class to bring up and check a Grafana server.

        Args:
            endpoint_url: The url on which grafana serves its api (not including `/api`). If this
                is an HTTPS endpoint, the hostname must match the SAN DNS in a system cert.
        """
        self._endpoint_url = endpoint_url
        self._http_client = urllib3.PoolManager()
        self._timeout = 2.0


    @property
    def is_ready(self) -> bool:
        """Checks whether the Grafana server is up and running yet.

        Returns:
            :bool: indicating whether the server is ready
        """
        return True if self.build_info.get("database", None) == "ok" else False


    @property
    def build_info(self) -> dict:
        """A convenience method which queries the API to see whether Grafana is really ready.

        Returns:
            Empty :dict: if it is not up, otherwise a dict containing basic API health
        """
        # The /api/health endpoint does not require authentication
        url = f"{self._endpoint_url}/api/health"

        try:
            response = self._http_client.request("GET", url, timeout=self._timeout)
        except exceptions.MaxRetryError:
            return {}

        decoded = response.data.decode("utf-8")
        try:
            # Occasionally we get an empty response, that, without the try-except block, would have
            # resulted in:
            # json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
            info = json.loads(decoded)
        except json.decoder.JSONDecodeError:
            return {}

        if info["database"] == "ok":
            return info
        return {}

    def password_has_been_changed(self, username: str, passwd: str) -> bool:
        """Checks whether the admin password has been changed from default generated.

        Raises:
            GrafanaCommError, if http request fails for any reason.

        Returns:
            :bool: indicating whether the password was changed.
        """
        url = f"{self._endpoint_url}/api/org"
        headers = urllib3.make_headers(basic_auth="{}:{}".format(username, passwd))

        try:
            res = self._http_client.request("GET", url, headers=headers, timeout=self._timeout)
            return True if "invalid username" in res.data.decode("utf8") else False
        except exceptions.HTTPError as e:
            # We do not want to blindly return "True" for unexpected exceptions such as:
            # - urllib3.exceptions.NewConnectionError: [Errno 111] Connection refused
            # - urllib3.exceptions.MaxRetryError
            raise GrafanaCommError("Unable to determine if password has been changed") from e
