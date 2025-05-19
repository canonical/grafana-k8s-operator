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
import time
from pathlib import Path
import os
import configparser
import hashlib
from io import StringIO
import json
import logging
from typing import Callable, Dict, List, Optional, cast
from ops import Container
from peer import Peer
from urllib3 import exceptions
import urllib3
import re
from ops.pebble import (
    APIError,
    ConnectionError,
    ChangeError,
    ExecError,
    Layer,
    PathError,
    ProtocolError,
)
import yaml
from charms.hydra.v0.oauth import (
    OauthProviderConfig
)
from models import DatasourceConfig, PebbleEnvConfig, TLSConfig, TracingConfig
from constants import GRAFANA_KEY_PATH, DATABASE_PATH, CA_CERT_PATH, GRAFANA_CRT_PATH, OAUTH_SCOPES, PROFILING_PORT, GRAFANA_WORKLOAD, CONFIG_PATH, WORKLOAD_PORT, PROVISIONING_PATH, DATASOURCES_PATH, DASHBOARDS_DIR, TRUSTED_CA_CERT_PATH

logger = logging.getLogger()



class GrafanaCommError(Exception):
    """Raised when comm fails unexpectedly."""


class Grafana:
    """Grafana workload."""

    def __init__(self,
                container: Container,
                is_leader: bool,
                peers: Peer,
                internal_url: str,
                external_url: str,
                datasources_config: DatasourceConfig,
                pebble_env_config: PebbleEnvConfig,
                tracing_config: Optional[TracingConfig] = None,
                oauth_config: Optional[OauthProviderConfig] = None,
                enable_profiling: bool = False,
                enable_reporting: bool = True,
                enable_external_db:  bool = False,
                admin_user: Optional[str] = None,
                admin_password: Optional[str] = None,
                tls_config: Optional[TLSConfig] = None,
                trusted_ca_certs: Optional[str] = None,
                dashboards: List[Dict] = [],
                provision_own_dashboard: bool = False,
                ) -> None:
        """A class to bring up and check a Grafana server."""
        self._container = container
        self._is_leader = is_leader
        self._peers = peers
        self._internal_url = internal_url
        self._external_url = external_url
        self._pebble_env_config = pebble_env_config
        self._datasources_config = datasources_config
        self._tracing_config = tracing_config
        self._enable_profiling = enable_profiling
        self._enable_reporting = enable_reporting
        self._enable_external_db = enable_external_db
        self._oauth_config = oauth_config
        self._admin_user = admin_user
        self._admin_password = admin_password
        self._tls_config = tls_config
        self._trusted_ca_certs = trusted_ca_certs
        self._dashboards = dashboards
        self._provision_own_dashboard = provision_own_dashboard
        self._http_client = urllib3.PoolManager()
        self._grafana_config_ini_hash = None
        self._grafana_datasources_hash = None
        self._scheme = "https" if internal_url.startswith("https://") else "http"


    @property
    def grafana_version(self) -> str:
        """Grafana server version.

        Returns:
            A string equal to the Grafana server version.
        """
        if not self._container.can_connect():
            return ""
        version_output, _ = self._container.exec(["grafana-server", "-v"]).wait_output()
        # Output looks like this:
        # Version 8.2.6 (commit: d2cccfe, branch: HEAD)
        result = re.search(r"Version (\d*\.\d*\.\d*)", version_output)
        if not result:
            return ""
        return result.group(1)


    def _get_hash_for_file(self, file: str) -> str:
        """Tries to connect to the container and hash a file.

        Args:
            file: a `str` filepath to read
        """
        try:
            content = self._container.pull(file)
            hash = hashlib.sha256(str(content.read()).encode("utf-8")).hexdigest()
            return hash
        except (FileNotFoundError, ProtocolError, PathError) as e:
            logger.warning(
                "Could not read configuration from the Grafana workload container: {}".format(
                    e
                )
            )

        return ""

    @property
    def _auth_env_vars(self):
        return self._peers.get_peer_data("auth_conf_env_vars")

    @property
    def _layer(self) -> Layer:
        """Construct the pebble layer information.

        Ref: https://github.com/grafana/grafana/blob/main/conf/defaults.ini
        """
        # Placeholder for when we add "proper" mysql support for HA
        extra_info = {
            "GF_DATABASE_TYPE": "sqlite3",
        }

        # Juju Proxy settings
        extra_info.update(
            {
                "https_proxy": os.environ.get("JUJU_CHARM_HTTPS_PROXY", ""),
                "http_proxy": os.environ.get("JUJU_CHARM_HTTP_PROXY", ""),
                "no_proxy": os.environ.get("JUJU_CHARM_NO_PROXY", ""),
            }
        )

        if self._auth_env_vars:
            extra_info.update(self._auth_env_vars)

        # For stripPrefix middleware to work correctly, we need to set serve_from_sub_path and
        # root_url in a particular way.
        extra_info.update(
            {
                "GF_SERVER_SERVE_FROM_SUB_PATH": "True",
                # https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#root_url
                "GF_SERVER_ROOT_URL": self._external_url,
                "GF_SERVER_ENFORCE_DOMAIN": "false",
                # When traefik provides TLS termination then traefik is https, but grafana is http.
                # We need to set GF_SERVER_PROTOCOL.
                # https://grafana.com/tutorials/run-grafana-behind-a-proxy/#1
                "GF_SERVER_PROTOCOL": self._scheme,
            }
        )

        # For consistency, set cert entries on the same condition as scheme is set to https.
        # NOTE: On one hand, we want to tell grafana to use TLS as soon as the tls relation is in
        # place; on the other hand, the certs may not be written to disk yet (they need to be
        # returned over relation data, go to peer data, and eventually be written to disk). When
        # grafana is restarted in HTTPS mode but without certs in place, we'll see a brief error:
        # "error: cert_file cannot be empty when using HTTPS".
        if self._scheme == "https":
            extra_info.update(
                {
                    "GF_SERVER_CERT_KEY": GRAFANA_KEY_PATH,
                    "GF_SERVER_CERT_FILE": GRAFANA_CRT_PATH,
                }
            )

        oauth_provider_info = self._oauth_config
        if oauth_provider_info:
            if oauth_provider_info:
                extra_info.update(
                    {
                        "GF_AUTH_GENERIC_OAUTH_ENABLED": "True",
                        "GF_AUTH_GENERIC_OAUTH_NAME": "external identity provider",
                        "GF_AUTH_GENERIC_OAUTH_CLIENT_ID": cast(
                            str, oauth_provider_info.client_id
                        ),
                        "GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET": cast(
                            str, oauth_provider_info.client_secret
                        ),
                        "GF_AUTH_GENERIC_OAUTH_SCOPES": OAUTH_SCOPES,
                        "GF_AUTH_GENERIC_OAUTH_AUTH_URL": oauth_provider_info.authorization_endpoint,
                        "GF_AUTH_GENERIC_OAUTH_TOKEN_URL": oauth_provider_info.token_endpoint,
                        "GF_AUTH_GENERIC_OAUTH_API_URL": oauth_provider_info.userinfo_endpoint,
                        "GF_AUTH_GENERIC_OAUTH_USE_REFRESH_TOKEN": "True",
                        # TODO: This toggle will be removed on grafana v10.3, remove it
                        "GF_FEATURE_TOGGLES_ENABLE": "accessTokenExpirationCheck",
                    }
                )

        if self._tracing_config:
            topology = self._tracing_config.juju_topology
            extra_info.update(
                {
                    "OTEL_RESOURCE_ATTRIBUTES": f"juju_application={topology.application},juju_model={topology.model}"
                                                + f",juju_model_uuid={topology.model_uuid},juju_unit={topology.unit},juju_charm={topology.charm_name}",
                }
            )

        # if we have any profiling relations, switch on profiling
        if self._enable_profiling:
            # https://grafana.com/docs/grafana/v9.5/setup-grafana/configure-grafana/configure-tracing/#turn-on-profiling
            extra_info.update(
                {
                    "GF_DIAGNOSTICS_PROFILING_ENABLED": "true",
                    "GF_DIAGNOSTICS_PROFILING_ADDR": "0.0.0.0",
                    "GF_DIAGNOSTICS_PROFILING_PORT": str(PROFILING_PORT),
                }
            )

        # If we're followers, we don't need to set any credentials on the grafana process.
        # This Grafana instance will inherit them automatically from the replication primary (the leader).
        if self._is_leader:
            # self.admin_password is guaranteed str if this unit is leader
            extra_info["GF_SECURITY_ADMIN_PASSWORD"] = cast(str, self._admin_password)
            extra_info["GF_SECURITY_ADMIN_USER"] = cast(str, self._admin_user)

        layer = Layer(
            {
                "summary": "grafana-k8s layer",
                "description": "grafana-k8s layer",
                "services": {
                    GRAFANA_WORKLOAD: {
                        "override": "replace",
                        "summary": "grafana-k8s service",
                        "command": "grafana-server -config {}".format(CONFIG_PATH),
                        "startup": "enabled",
                        "environment": {
                            "GF_SERVER_HTTP_PORT": str(WORKLOAD_PORT),
                            "GF_LOG_LEVEL": self._pebble_env_config.log_level,
                            "GF_PLUGINS_ENABLE_ALPHA": "true",
                            "GF_PATHS_PROVISIONING": PROVISIONING_PATH,
                            "GF_SECURITY_ALLOW_EMBEDDING": str(self._pebble_env_config.allow_embedding).lower(),
                            "GF_AUTH_ANONYMOUS_ENABLED": str(
                                self._pebble_env_config.allow_anonymous_access
                            ).lower(),
                            "GF_USERS_AUTO_ASSIGN_ORG": str(
                               self._pebble_env_config.enable_auto_assign_org
                            ).lower(),
                            **extra_info,
                        },
                    }
                },
            }
        )

        return layer

    @property
    def grafana_config_ini_hash(self) -> str:
        """Returns the hash for the Grafana ini file."""
        return self._grafana_config_ini_hash or self._get_hash_for_file(CONFIG_PATH)

    @grafana_config_ini_hash.setter
    def grafana_config_ini_hash(self, hash: str) -> None:
        """Sets the Grafana config ini hash."""
        self._grafana_config_ini_hash = hash

    @property
    def grafana_datasources_hash(self) -> str:
        """Returns the hash for the Grafana ini file."""
        return self._grafana_datasources_hash or self._get_hash_for_file(DATASOURCES_PATH)

    @grafana_datasources_hash.setter
    def grafana_datasources_hash(self, hash: str) -> None:
        """Sets the Grafana config ini hash."""
        self._grafana_datasources_hash = hash

    @property
    def _db_config(self) -> Optional[Dict[str, str]]:
        if self._enable_external_db:
            peer_data = self._peers.get_peer_data("database")
            if not peer_data:
                return None
            return peer_data
        return None

    def reconcile(self):
        """Unconditional control logic."""
        if self._container.can_connect():
            self._reconcile_provisioning_dirs()
            # updates to existing grafana dashboards don't require a grafana restart
            self._reconcile_dashboards()

            if any(
                    (self._reconcile_tls_config(),
                    self._reconcile_trusted_ca(),
                    self._reconcile_config(),
                    self._reconcile_ds_config(),
                    self._reconcile_dashboards_config(),
                    self._reconcile_pebble_plan(),
                    )
                   ):
                self._restart_grafana()


    def _reconcile_provisioning_dirs(self):
        for d in ("plugins", "notifiers", "alerting", "dashboards"):
            path = Path(PROVISIONING_PATH) / d
            if not self._container.exists(path):
                self._container.make_dir(path, make_parents=True)

    def _reconcile_dashboards(self):
        dashboards_file_to_be_kept = {}
        try:
            for dashboard_file in self._container.list_files(DASHBOARDS_DIR, pattern="juju_*.json"):
                dashboards_file_to_be_kept[dashboard_file.path] = False

            for dashboard in self._dashboards:
                dashboard_content = dashboard["content"]
                dashboard_content_bytes = dashboard_content.encode("utf-8")
                dashboard_content_digest = hashlib.sha256(dashboard_content_bytes).hexdigest()
                dashboard_filename = "juju_{}_{}.json".format(
                    dashboard["charm"], dashboard_content_digest[0:7]
                )

                path = os.path.join(DASHBOARDS_DIR, dashboard_filename)
                dashboards_file_to_be_kept[path] = True

                logger.debug("New dashboard %s", path)
                self._container.push(path, dashboard_content_bytes, make_dirs=True)

            for dashboard_file_path, to_be_kept in dashboards_file_to_be_kept.items():
                if not to_be_kept:
                    self._container.remove_path(dashboard_file_path)
                    logger.debug("Removed dashboard %s", dashboard_file_path)

        except ConnectionError:
            logger.exception("Could not update dashboards. Pebble shutting down?")

        # provision a self-monitoring dashboard
        self._reconcile_own_dashboard()

    def _reconcile_dashboards_config(self) -> bool:
        """Initialise the provisioning of Grafana dashboards."""
        logger.info("Initializing dashboard provisioning path")

        dashboard_config = {
            "apiVersion": 1,
            "providers": [
                {
                    "name": "Default",
                    "updateIntervalSeconds": "5",
                    "type": "file",
                    "options": {"path": DASHBOARDS_DIR},
                }
            ],
        }

        default_config = os.path.join(DASHBOARDS_DIR, "default.yaml")
        default_config_string = yaml.dump(dashboard_config)

        if not self._container.exists(default_config):
            try:
                self._container.push(default_config, default_config_string, make_dirs=True)
                return True
            except ConnectionError:
                logger.warning(
                    "Could not push default dashboard configuration. Pebble shutting down?"
                )
        return False

    def _reconcile_trusted_ca(self) -> bool:
        """This function receives the trusted certificates from the certificate_transfer integration.

        Grafana needs to restart to use newly received certificates. Certificates attached to the
        relation need to be pulled before Grafana is started.
        This function is needed because relation events are not emitted on upgrade, and because we
        do not have (nor do we want) persistent storage for certs.
        """
        any_change = False
        if self._trusted_ca_certs:
            current = (
                    self._container.pull(TRUSTED_CA_CERT_PATH).read()
                    if self._container.exists(TRUSTED_CA_CERT_PATH)
                    else ""
                )
            if current == self._trusted_ca_certs:
                return any_change

            any_change = True
            self._container.push(TRUSTED_CA_CERT_PATH, self._trusted_ca_certs, make_dirs=True)
            self._container.exec(["update-ca-certificates", "--fresh"]).wait()
        else:
            if self._container.exists(TRUSTED_CA_CERT_PATH):
                any_change = True
                self._container.remove_path(TRUSTED_CA_CERT_PATH, recursive=True)

        return any_change


    def _reconcile_tls_config(self) -> bool:
        any_change = False
        for cert, cert_path in (
            (self._tls_config.certificate if self._tls_config else None, GRAFANA_CRT_PATH),
            (self._tls_config.key if self._tls_config else None, GRAFANA_KEY_PATH),
            (self._tls_config.ca if self._tls_config else None, CA_CERT_PATH),
        ):
            if cert:
                current = (
                    self._container.pull(cert_path).read()
                    if self._container.exists(cert_path)
                    else ""
                )
                if current == cert:
                    continue
                any_change = True
                self._container.push(cert_path, cert ,make_dirs=True)
            else:
                if self._container.exists(cert_path):
                    any_change = True
                    self._container.remove_path(cert_path,recursive=True)

        self._container.exec(["update-ca-certificates", "--fresh"]).wait()
        return any_change

    def _reconcile_config(self) -> bool:
        logger.debug("Handling grafana-k8s configuration change")
        restart = False

         # Generate a new base config and see if it differs from what we have.
        # If it does, store it and signal that we should restart Grafana
        grafana_config_ini = self._generate_grafana_config()
        config_ini_hash = hashlib.sha256(str(grafana_config_ini).encode("utf-8")).hexdigest()
        if not self.grafana_config_ini_hash == config_ini_hash:
            self.grafana_config_ini_hash = config_ini_hash
            self._update_config_file(CONFIG_PATH, grafana_config_ini)
            logger.info("Updated Grafana's base configuration")

            restart = True
        return restart

    def _reconcile_ds_config(self) -> bool:
        """Check whether datasources need to be (re)provisioned."""
        grafana_datasources = self._generate_datasource_config()
        datasources_hash = hashlib.sha256(str(grafana_datasources).encode("utf-8")).hexdigest()
        if not self.grafana_datasources_hash == datasources_hash:
            self.grafana_datasources_hash = datasources_hash
            self._update_config_file(DATASOURCES_PATH, grafana_datasources)
            logger.info("Updated Grafana's datasource configuration")

            # Non-leaders will get updates from litestream
            if self._is_leader:
                return True
        return False

    def _reconcile_pebble_plan(self) -> bool:
        if self._container.get_plan().services != self._layer.services:
            return True
        return False

    def _restart_grafana(self) -> None:
        """Restart the pebble container.

        `container.replan()` is intentionally avoided, since if no environment
        variables are changed, this will not actually restart Grafana, which is
        necessary to reload the provisioning files.

        Note that Grafana does not support SIGHUP, so a full restart is needed.
        """
        # TODO: add a check that the config file is on disk
        if self._layer:
            try:
                self._container.add_layer(GRAFANA_WORKLOAD, self._layer, combine=True)
                if self._container.get_service(GRAFANA_WORKLOAD).is_running():
                    self._container.stop(GRAFANA_WORKLOAD)

                self._container.start(GRAFANA_WORKLOAD)
                logger.info("Restarted grafana-k8s")

                if self._poll_container(self._container.can_connect):
                    # We should also make sure sqlite is in WAL mode for replication
                    self._push_sqlite_static()

                    pragma = self._container.exec(
                        [
                            "/usr/local/bin/sqlite3",
                            DATABASE_PATH,
                            "pragma journal_mode=wal;",
                        ]
                    )
                    pragma.wait()

            except ExecError as e:
                # debug because, on initial container startup when Grafana has an open lock and is
                # populating, this comes up with ERRCODE: 26
                logger.debug("Could not apply journal_mode pragma. Exit code: {}".format(e.exit_code))
            except ConnectionError:
                logger.error(
                    "Could not restart grafana-k8s -- Pebble socket does "
                    "not exist or is not responsive"
                )
            except ChangeError as e:
                logger.error("Could not restart grafana at this time: %s", e)

    def _push_sqlite_static(self):
        # for ease of mocking in unittests, this is a standalone function
        self._container.push(
            "/usr/local/bin/sqlite3",
            Path("sqlite-static").read_bytes(),
            permissions=0o755,
            make_dirs=True,
        )

    def _poll_container(
            self, func: Callable[[], bool], timeout: float = 2.0, delay: float = 0.1
    ) -> bool:
        """Try to poll the container to work around Container.is_connect() being point-in-time.

        Args:
            func: a :Callable: to check, which should return a boolean.
            timeout: a :float: to time out after
            delay: a :float: to wait between checks

        """
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                if func():
                    return True

                time.sleep(delay)
            except (APIError, ConnectionError, ProtocolError):
                logger.debug("Failed to poll the container due to a Pebble error")

        return False

    def _generate_datasource_config(self) -> str:
        """Template out a Grafana datasource config.

        Template using the sources (and removed sources) the consumer knows about, and dump it to
        YAML.

        Returns:
            A string-dumped YAML config for the datasources
        """
        # Boilerplate for the config file
        datasources_dict = {"apiVersion": 1, "datasources": [], "deleteDatasources": []}

        for source_info in self._datasources_config.datasources():
            source = {
                "orgId": "1",
                "access": "proxy",
                "isDefault": "false",
                "name": source_info["source_name"],
                "type": source_info["source_type"],
                "url": source_info["url"],
            }
            if source_info.get("extra_fields", None):
                source["jsonData"] = source_info.get("extra_fields")
            if source_info.get("secure_extra_fields", None):
                source["secureJsonData"] = source_info.get("secure_extra_fields")

            # set timeout for querying this data source
            timeout = int(source.get("jsonData", {}).get("timeout", 0))
            configured_timeout = self._datasources_config.query_timeout
            if timeout < configured_timeout:
                json_data = source.get("jsonData", {})
                json_data.update({"timeout": configured_timeout})
                source["jsonData"] = json_data

            datasources_dict["datasources"].append(source)  # type: ignore[attr-defined]

        # Also get a list of all the sources which have previously been purged and add them
        for name in self._datasources_config.datasources_to_delete():
            source = {"orgId": 1, "name": name}
            datasources_dict["deleteDatasources"].append(source)  # type: ignore[attr-defined]

        datasources_string = yaml.dump(datasources_dict)
        return datasources_string

    def _update_config_file(self, config_path: str, config: str) -> None:
        """Write an updated Grafana configuration file to the Pebble container if necessary.

        Args:
            config_path: The path where the configuration will be pushed
            config: A :str: containing the configuration
        """
        try:
            self._container.push(config_path, config, make_dirs=True)
        except ConnectionError:
            logger.error(
                "Could not push config. Pebble refused connection. Shutting down?"
            )

    def _generate_grafana_config(self) -> str:
        """Generate a database configuration for Grafana.

        For now, this only creates database information, since everything else
        can be set in ENV variables, but leave for expansion later so we can
        hide auth secrets
        """
        configs = [self._generate_tracing_config(), self._generate_analytics_config(), self._generate_database_config()]
        if not self._enable_external_db:
            with StringIO() as data:
                config_ini = configparser.ConfigParser()
                config_ini["database"] = {
                    "type": "sqlite3",
                    "path": DATABASE_PATH,
                }
                config_ini.write(data)
                data.seek(0)
                configs.append(data.read())
        return "\n".join(filter(bool, configs))

    def _generate_tracing_config(self) -> str:
        """Generate tracing configuration.

        Returns:
            A string containing the required tracing information to be stubbed into the config
            file.
        """
        if self._tracing_config is None:
            return ""

        tracing_endpoint = self._tracing_config.endpoint
        config_ini = configparser.ConfigParser()
        config_ini["tracing.opentelemetry"] = {
            "sampler_type": "probabilistic",
            "sampler_param": "0.01",
        }
        # ref: https://github.com/grafana/grafana/blob/main/conf/defaults.ini#L1505
        config_ini["tracing.opentelemetry.otlp"] = {
            "address": tracing_endpoint,
        }

        # This is silly, but a ConfigParser() handles this nicer than
        # raw string manipulation
        data = StringIO()
        config_ini.write(data)
        ret = data.getvalue()
        return ret

    def _generate_analytics_config(self) -> str:
        """Generate analytics configuration.

        Returns:
            A string containing the analytics config to be stubbed into the config file.
        """
        if self._enable_reporting:
            return ""
        config_ini = configparser.ConfigParser()
        # Ref: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#analytics
        config_ini["analytics"] = {
            "reporting_enabled": "false",
            "check_for_updates": "false",
            "check_for_plugin_updates": "false",
        }

        data = StringIO()
        config_ini.write(data)
        ret = data.getvalue()
        return ret

    def _generate_database_config(self) -> str:
        """Generate a database configuration.

        Returns:
            A string containing the required database information to be stubbed into the config
            file.
        """
        config_ini = configparser.ConfigParser()
        db_type = "mysql"
        db_config = self._db_config
        if not db_config:
            return ""

        db_url = "{0}://{1}:{2}@{3}/{4}".format(
            db_type,
            db_config.get("user"),
            db_config.get("password"),
            db_config.get("host"),
            db_config.get("name"),
        )
        config_ini["database"] = {
            "type": db_type,
            "host": db_config.get("host", ""),
            "name": db_config.get("name", ""),
            "user": db_config.get("user", ""),
            "password": db_config.get("password", ""),
            "url": db_url,
        }

        # This is still silly
        data = StringIO()
        config_ini.write(data)
        ret = data.getvalue()
        return ret

    def _reconcile_own_dashboard(self) -> None:
        """If all the prerequisites are enabled, provision a self-monitoring dashboard.

        Requires:
            A Prometheus relation on self.prometheus_scrape
            The SAME Prometheus relation again on grafana_source

        If those are true, we have a Prometheus scraping this Grafana, and we should
        provision our dashboard.
        """
        dashboard_path = os.path.join(DASHBOARDS_DIR, "self_dashboard.json")
        if self._provision_own_dashboard and self._is_leader:
            # This is not going through the library due to the massive refactor needed in order
            # to squash all the `validate_relation_direction` and structure around smashing
            # the datastructures for a self-monitoring use case.
            self._container.push(
                dashboard_path, Path("src/self_dashboard.json").read_bytes(), make_dirs=True
            )
        elif not self._provision_own_dashboard:
            if self._container.list_files(DASHBOARDS_DIR, pattern="self_dashboard.json"):
                self._container.remove_path(dashboard_path)
                logger.debug("Removed dashboard %s", dashboard_path)

    @property
    def is_ready(self) -> bool:
        """Checks whether the Grafana server is up and running yet.

        Returns:
            :bool: indicating whether the server is ready
        """
        return True if self.build_info.get("database", None) == "ok" else False

    def password_has_been_changed(self, username: str, passwd: str) -> bool:
        """Checks whether the admin password has been changed from default generated.

        Raises:
            GrafanaCommError, if http request fails for any reason.

        Returns:
            :bool: indicating whether the password was changed.
        """
        url = f"{self._internal_url}/api/org"
        headers = urllib3.make_headers(basic_auth="{}:{}".format(username, passwd))

        try:
            res = self._http_client.request("GET", url, headers=headers, timeout=2.0)
            return True if "invalid username" in res.data.decode("utf8") else False
        except exceptions.HTTPError as e:
            # We do not want to blindly return "True" for unexpected exceptions such as:
            # - urllib3.exceptions.NewConnectionError: [Errno 111] Connection refused
            # - urllib3.exceptions.MaxRetryError
            raise GrafanaCommError("Unable to determine if password has been changed") from e

    @property
    def build_info(self) -> dict:
        """A convenience method which queries the API to see whether Grafana is really ready.

        Returns:
            Empty :dict: if it is not up, otherwise a dict containing basic API health
        """
        # The /api/health endpoint does not require authentication
        url = f"{self._internal_url}/api/health"

        try:
            response = self._http_client.request("GET", url, timeout=2.0)
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
