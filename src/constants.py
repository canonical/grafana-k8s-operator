"""Charm constants."""

REQUIRED_DATABASE_FIELDS = {
    "type",  # mysql, postgres or sqlite3 (sqlite3 doesn't work for HA)
    "host",  # in the form '<url_or_ip>:<port>', e.g. 127.0.0.1:3306
    "name",
    "user",
    "password",
}
PEER_RELATION = "grafana"
PGSQL_RELATION = "pgsql"
DATABASE_PATH = "/var/lib/grafana/grafana.db"
# https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/generic-oauth
OAUTH_SCOPES = "openid email offline_access"
OAUTH_GRANT_TYPES = ["authorization_code", "refresh_token"]
GRAFANA_WORKLOAD = "grafana"
VALID_AUTHENTICATION_MODES = {"proxy"}
CONFIG_PATH = "/etc/grafana/grafana-config.ini"
PROVISIONING_PATH = "/etc/grafana/provisioning"
DATASOURCES_PATH = "/etc/grafana/provisioning/datasources/datasources.yaml"
DASHBOARDS_DIR = f"{PROVISIONING_PATH}/dashboards"
GRAFANA_CRT_PATH = "/etc/grafana/grafana.crt"
GRAFANA_KEY_PATH = "/etc/grafana/grafana.key"
CA_CERT_PATH = "/usr/local/share/ca-certificates/cos-ca.crt"
TRUSTED_CA_CERT_PATH = "/usr/local/share/ca-certificates/trusted-ca-cert.crt"
PROFILING_PORT = 8080
WORKLOAD_PORT = 3000
