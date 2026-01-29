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
import hashlib
import logging
from typing import Callable, Dict, List, Optional, cast
from ops import Container
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
from models import TLSConfig
from constants import (
    GRAFANA_KEY_PATH,
    DATABASE_PATH,
    CA_CERT_PATH,
    GRAFANA_CRT_PATH,
    OAUTH_SCOPES,
    PROFILING_PORT,
    GRAFANA_WORKLOAD,
    CONFIG_PATH,
    WORKLOAD_PORT,
    PROVISIONING_PATH,
    DATASOURCES_PATH,
    DASHBOARDS_DIR,
    TRUSTED_CA_CERT_PATH
)
from grafana_config import GrafanaConfig

logger = logging.getLogger()


class Grafana:
    """Grafana workload."""

    def __init__(self,
                container: Container,
                is_leader: bool,
                grafana_config_generator: GrafanaConfig,
                pebble_env: Callable,
                enable_profiling: bool = False,
                tls_config: Optional[TLSConfig] = None,
                trusted_ca_certs: Optional[str] = None,
                dashboards: List[Dict] = [],
                provision_own_dashboard: bool = False,
                scheme: str = "http",
                ingress_ready: bool = False,
                ) -> None:
        """A class to bring up and check a Grafana server."""
        self._container = container
        self._is_leader = is_leader
        self._grafana_config_generator = grafana_config_generator
        self._pebble_env = pebble_env
        self._enable_profiling = enable_profiling
        self._tls_config = tls_config
        self._trusted_ca_certs = trusted_ca_certs
        self._dashboards = dashboards
        self._provision_own_dashboard = provision_own_dashboard
        self._current_config_hash = None
        self._current_datasources_hash = None
        self._scheme =  scheme
        self.ingress_ready = ingress_ready

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


    @property
    def _layer(self) -> Layer:
        """Construct the pebble layer information.

        Ref: https://github.com/grafana/grafana/blob/main/conf/defaults.ini
        """
        pebble_env = self._pebble_env()
        extra_info = {}

        # Juju Proxy settings
        extra_info.update(
            {
                "https_proxy": os.environ.get("JUJU_CHARM_HTTPS_PROXY", ""),
                "http_proxy": os.environ.get("JUJU_CHARM_HTTP_PROXY", ""),
                "no_proxy": os.environ.get("JUJU_CHARM_NO_PROXY", ""),
            }
        )

        auth_env_config = self._grafana_config_generator.auth_env_config
        if auth_env_config:
            extra_info.update(auth_env_config)

        # For stripPrefix middleware to work correctly, we need to set serve_from_sub_path and
        # root_url in a particular way.
        extra_info.update(
            {
                "GF_SERVER_SERVE_FROM_SUB_PATH": "True" if self.ingress_ready else "False",
                # https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#root_url
                "GF_SERVER_ROOT_URL": pebble_env.external_url,
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

        oauth_provider_info = self._grafana_config_generator.oauth_config
        if oauth_provider_info:
            extra_info.update(
                {
                    "GF_SERVER_SERVE_FROM_SUB_PATH": "True",
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
                }
            )
        
        if role_attribute_path := self._grafana_config_generator.role_attribute_path:
            extra_info.update({"GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH": role_attribute_path})

        tracing_resource_attrs = pebble_env.tracing_resource_attributes
        if tracing_resource_attrs:
            extra_info.update(
                {
                    "OTEL_RESOURCE_ATTRIBUTES": tracing_resource_attrs
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
            extra_info["GF_SECURITY_ADMIN_PASSWORD"] = cast(str, pebble_env.admin_password)
            extra_info["GF_SECURITY_ADMIN_USER"] = cast(str, pebble_env.admin_user)

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
                            "GF_LOG_LEVEL": pebble_env.log_level,
                            "GF_PLUGINS_ENABLE_ALPHA": "true",
                            "GF_PATHS_PROVISIONING": PROVISIONING_PATH,
                            "GF_SECURITY_ALLOW_EMBEDDING": str(pebble_env.allow_embedding).lower(),
                            "GF_AUTH_ANONYMOUS_ENABLED": str(
                                pebble_env.allow_anonymous_access
                            ).lower(),
                            "GF_USERS_AUTO_ASSIGN_ORG": str(
                               pebble_env.enable_auto_assign_org
                            ).lower(),
                            **extra_info,
                        },
                    }
                },
            }
        )

        return layer

    @property
    def current_config_hash(self) -> str:
        """Returns the hash for the Grafana ini file."""
        return self._current_config_hash or self._get_hash_for_file(CONFIG_PATH)

    @current_config_hash.setter
    def current_config_hash(self, hash: str) -> None:
        """Sets the Grafana config ini hash."""
        self._current_config_hash = hash

    @property
    def current_datasources_hash(self) -> str:
        """Returns the hash for the Grafana datasources file."""
        return self._current_datasources_hash or self._get_hash_for_file(DATASOURCES_PATH)

    @current_datasources_hash.setter
    def current_datasources_hash(self, hash: str) -> None:
        """Sets the Grafana datasources config hash."""
        self._current_datasources_hash = hash


    def reconcile(self):
        """Unconditional control logic."""
        if self._container.can_connect():
            self._provision_dirs()
            # updates to existing grafana dashboards don't require a grafana restart
            self._reconcile_dashboards()
            changes = []
            self._reconcile_tls_config(changes)
            self._reconcile_trusted_ca(changes)
            self._reconcile_config(changes)
            self._reconcile_ds_config(changes)
            self._reconcile_dashboards_config(changes)
            self._reconcile_pebble_plan(changes)
            if any(changes):
                self._restart_grafana()


    def _provision_dirs(self):
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

    def _reconcile_dashboards_config(self, changes:List):
        """Initialise the provisioning of Grafana dashboards."""
        logger.info("Initializing dashboard provisioning path")

        config_path = os.path.join(DASHBOARDS_DIR, "default.yaml")
        config = self._grafana_config_generator.generate_dashboard_config()

        if not self._container.exists(config_path):
            self._update_config_file(config_path, config)
            changes.append(True)

    def _reconcile_trusted_ca(self, changes: List):
        """This function receives the trusted certificates from the certificate_transfer integration.

        Grafana needs to restart to use newly received certificates. Certificates attached to the
        relation need to be pulled before Grafana is started.
        This function is needed because relation events are not emitted on upgrade, and because we
        do not have (nor do we want) persistent storage for certs.
        """
        if self._trusted_ca_certs:
            current = (
                    self._container.pull(TRUSTED_CA_CERT_PATH).read()
                    if self._container.exists(TRUSTED_CA_CERT_PATH)
                    else ""
                )
            if current == self._trusted_ca_certs:
                return

            changes.append(True)
            self._container.push(TRUSTED_CA_CERT_PATH, self._trusted_ca_certs, make_dirs=True)
            self._container.exec(["update-ca-certificates", "--fresh"]).wait()
        else:
            if self._container.exists(TRUSTED_CA_CERT_PATH):
                changes.append(True)
                self._container.remove_path(TRUSTED_CA_CERT_PATH, recursive=True)


    def _reconcile_tls_config(self, changes: List):
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
                changes.append(True)
                self._container.push(cert_path, cert ,make_dirs=True)
                self._container.exec(["update-ca-certificates", "--fresh"]).wait()
            else:
                if self._container.exists(cert_path):
                    changes.append(True)
                    self._container.remove_path(cert_path,recursive=True)
                    self._container.exec(["update-ca-certificates", "--fresh"]).wait()

    def _reconcile_config(self, changes: List):
        logger.debug("Handling grafana-k8s configuration change")

        # Generate a new base config and see if it differs from what we have.
        # If it does, store it and signal that we should restart Grafana
        config = self._grafana_config_generator.generate_grafana_config()
        config_hash = hashlib.sha256(str(config).encode("utf-8")).hexdigest()
        if self.current_config_hash != config_hash:
            self.current_config_hash = config_hash
            self._update_config_file(CONFIG_PATH, config)
            logger.info("Updated Grafana's base configuration")
            changes.append(True)

    def _reconcile_ds_config(self, changes:List):
        """Check whether datasources need to be (re)provisioned."""
        grafana_datasources = self._grafana_config_generator.generate_datasource_config()
        datasources_hash = hashlib.sha256(str(grafana_datasources).encode("utf-8")).hexdigest()
        if not self.current_datasources_hash == datasources_hash:
            self.current_datasources_hash = datasources_hash
            self._update_config_file(DATASOURCES_PATH, grafana_datasources)
            logger.info("Updated Grafana's datasource configuration")

            # Non-leaders will get updates from the database
            if self._is_leader:
                changes.append(True)

    def _reconcile_pebble_plan(self, changes:List):
        if self._container.get_plan().services != self._layer.services:
            changes.append(True)

    def _restart_grafana(self) -> None:
        """Restart the pebble container.

        `container.replan()` is intentionally avoided, since if no environment
        variables are changed, this will not actually restart Grafana, which is
        necessary to reload the provisioning files.

        Note that Grafana does not support SIGHUP, so a full restart is needed.
        """
        # TODO: add a check that the config file is on disk
        if layer:= self._layer:
            try:
                self._container.add_layer(GRAFANA_WORKLOAD, layer, combine=True)
                self._container.restart(GRAFANA_WORKLOAD)
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
