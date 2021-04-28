import json
import urllib3


class Grafana:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.http = urllib3.PoolManager()

    def build_info(self):
        api_path = "api/health"
        url = "http://{}:{}/{}".format(
            self.host,
            self.port,
            api_path)

        try:
            response = self.http.request("GET", url)
        except urllib3.exceptions.MaxRetryError:
            return {}

        info = json.loads(response.data.decode('utf-8'))
        if info["database"] == "ok":
            return info
        else:
            return {}