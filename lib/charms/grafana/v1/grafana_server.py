import json
import urllib3


class Grafana:
    def __init__(self, host: str, port: int) -> None:
        """A class to bring up and check a Grafana serverr

        Args:
            host: a :str: which indicates the hostname
            port: an :int: to listen on

        """
        self.host = host
        self.port = port
        self.http = urllib3.PoolManager()

    def is_ready(self) -> bool:
        """Checks whether the Grafana server is up and running yet

        Returns:
            :bool: indicating whether or not the server is ready
        """

        return True if self.build_info.get("database", None) == "ok" else False

    @property
    def build_info(self) -> dict:
        """
        A convenience method which queries the API to see whether Grafana is really ready

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
