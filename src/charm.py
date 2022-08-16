#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
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

"""A Kubernetes charm for Grafana."""

import configparser
import hashlib
import json
import logging
import os
import secrets
import string
from io import StringIO
from typing import Any
from urllib.parse import ParseResult, urlparse

import yaml
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardConsumer
from charms.grafana_k8s.v0.grafana_source import (
    GrafanaSourceConsumer,
    GrafanaSourceEvents,
    SourceFieldsMissingError,
)
from charms.observability_libs.v0.kubernetes_compute_resources_patch import (
    K8sResourcePatchFailedEvent,
    KubernetesComputeResourcesPatch,
    ResourceRequirements,
    adjust_resource_requirements,
)
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider
from ops.charm import (
    ActionEvent,
    CharmBase,
    ConfigChangedEvent,
    RelationBrokenEvent,
    RelationChangedEvent,
    UpgradeCharmEvent,
)
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus
from ops.pebble import ConnectionError, Layer, PathError, ProtocolError

from grafana_server import Grafana
from kubernetes_service import K8sServicePatch, PatchFailed

logger = logging.getLogger()

REQUIRED_DATABASE_FIELDS = {
    "type",  # mysql, postgres or sqlite3 (sqlite3 doesn't work for HA)
    "host",  # in the form '<url_or_ip>:<port>', e.g. 127.0.0.1:3306
    "name",
    "user",
    "password",
}

VALID_DATABASE_TYPES = {"mysql", "postgres", "sqlite3"}

CONFIG_PATH = "/etc/grafana/grafana-config.ini"
PROVISIONING_PATH = "/etc/grafana/provisioning"
DATASOURCES_PATH = "/etc/grafana/provisioning/datasources/datasources.yaml"
DATABASE = "database"
PEER = "grafana"

PORT = 3000


class GrafanaCharm(CharmBase):
    """Charm to run Grafana on Kubernetes.

    This charm allows for high-availability
    (as long as a non-sqlite database relation is present).

    Developers of this charm should be aware of the Grafana provisioning docs:
    https://grafana.com/docs/grafana/latest/administration/provisioning/
    """

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        # -- initialize states --
        self.name = "grafana"
        self.container = self.unit.get_container(self.name)
        self.grafana_service = Grafana("localhost", PORT)
        self._grafana_config_ini_hash = None
        self._grafana_datasources_hash = None
        self._stored.set_default(k8s_service_patched=False, admin_password="")

        # -- Prometheus self-monitoring
        self.metrics_endpoint = MetricsEndpointProvider(
            self,
            jobs=[
                {
                    "static_configs": [{"targets": ["*:3000"]}],
                },
            ],
        )

        # -- standard events
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.grafana_pebble_ready, self._on_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on.get_admin_password_action, self._on_get_admin_password)

        # -- grafana_source relation observations
        self.source_consumer = GrafanaSourceConsumer(self, "grafana-source")
        self.framework.observe(
            self.source_consumer.on.sources_changed,
            self._on_grafana_source_changed,
        )
        self.framework.observe(
            self.source_consumer.on.sources_to_delete_changed,
            self._on_grafana_source_changed,
        )

        # -- grafana_dashboard relation observations
        self.dashboard_consumer = GrafanaDashboardConsumer(self, "grafana-dashboard")
        self.framework.observe(
            self.dashboard_consumer.on.dashboards_changed, self._on_dashboards_changed
        )

        # -- database relation observations
        self.framework.observe(self.on[DATABASE].relation_changed, self._on_database_changed)
        self.framework.observe(self.on[DATABASE].relation_broken, self._on_database_broken)

        # -- k8s resource patch
        self.resource_patch = KubernetesComputeResourcesPatch(
            self, self.name, resource_reqs_func=self._resource_reqs_from_config
        )
        self.framework.observe(self.resource_patch.on.patch_failed, self._on_resource_patch_failed)

    def _on_install(self, _):
        """Handler for the install event during which we will update the K8s service."""
        self._patch_k8s_service()

    def _on_config_changed(self, event: ConfigChangedEvent) -> None:
        """Event handler for the config-changed event.

        If the configuration is changed, update the variables we know about and
        restart the services. We don't know specifically whether it's a new install,
        a relation change, a leader election, or other, so call `_configure` to check
        the config files

        Args:
            event: a :class:`ConfigChangedEvent` to signal that something happened
        """
        self._configure()

    def _on_grafana_source_changed(self, event: GrafanaSourceEvents) -> None:
        """When a grafana-source is added or modified, update the config.

        Args:
            event: a :class:`GrafanaSourceEvents` instance sent from the provider
        """
        self._configure()

    def _on_upgrade_charm(self, event: UpgradeCharmEvent) -> None:
        """Re-provision Grafana and its datasources on upgrade.

        Args:
            event: a :class:`UpgradeCharmEvent` to signal the upgrade
        """
        self.source_consumer.upgrade_keys()
        self._configure()
        self._on_dashboards_changed(event)

    def _on_stop(self, _) -> None:
        """Go into maintenance state if the unit is stopped."""
        self.unit.status = MaintenanceStatus("Application is terminating.")

    def _configure(self) -> None:
        """Configure Grafana.

        Generate configuration files and check the sums against what is
        already stored in the charm. If either the base Grafana config
        or the datasource config differs, restart Grafana.
        """
        if not self.container.can_connect():
            return

        logger.debug("Handling grafana-k8a configuration change")
        restart = False

        # Generate a new base config and see if it differs from what we have.
        # If it does, store it and signal that we should restart Grafana
        grafana_config_ini = self._generate_grafana_config()
        config_ini_hash = hashlib.sha256(str(grafana_config_ini).encode("utf-8")).hexdigest()
        if not self.grafana_config_ini_hash == config_ini_hash:
            self.grafana_config_ini_hash = config_ini_hash
            self._update_grafana_config_ini(grafana_config_ini)
            logger.info("Updated Grafana's base configuration")

            restart = True

        # Do the same thing for datasources
        grafana_datasources = self._generate_datasource_config()
        datasources_hash = hashlib.sha256(str(grafana_datasources).encode("utf-8")).hexdigest()
        if not self.grafana_datasources_hash == datasources_hash:
            self.grafana_datasources_hash = datasources_hash
            self._update_datasource_config(grafana_datasources)
            logger.info("Updated Grafana's datasource configuration")

            restart = True

        if self.container.get_plan().services != self._build_layer().services:
            restart = True

        if not self.resource_patch.is_ready():
            if isinstance(self.unit.status, ActiveStatus) or self.unit.status.message == "":
                self.unit.status = MaintenanceStatus("Waiting for resource limit patch to apply")
            return

        if restart:
            self.restart_grafana()

    def _update_datasource_config(self, config: str) -> None:
        """Write an updated datasource configuration file to the Pebble container if necessary.

        Args:
            config: A :str: containing the datasource configuration
        """
        container = self.unit.get_container(self.name)

        try:
            container.push(DATASOURCES_PATH, config, make_dirs=True)
        except ConnectionError:
            logger.error(
                "Could not push datasource config. Pebble refused connection. Shutting down?"
            )

    def _update_grafana_config_ini(self, config: str) -> None:
        """Write an updated Grafana configuration file to the Pebble container if necessary.

        Args:
            config: A :str: containing the datasource configuration
        """
        try:
            self.container.push(CONFIG_PATH, config, make_dirs=True)
        except ConnectionError:
            logger.error(
                "Could not push datasource config. Pebble refused connection. Shutting down?"
            )

    @property
    def has_peers(self) -> bool:
        """Check whether or not there are any other Grafanas as peers."""
        rel = self.model.get_relation(PEER)
        return len(rel.units) > 0 if rel is not None else False

    @property
    def peers(self):
        """Fetch the peer relation."""
        return self.model.get_relation(PEER)

    def set_peer_data(self, key: str, data: Any) -> None:
        """Put information into the peer data bucket instead of `StoredState`."""
        self.peers.data[self.app][key] = json.dumps(data)

    def get_peer_data(self, key: str) -> Any:
        """Retrieve information from the peer data bucket instead of `StoredState`."""
        data = self.peers.data[self.app].get(key, "")
        return json.loads(data) if data else {}

    ############################
    # DASHBOARD IMPORT
    ###########################
    def init_dashboard_provisioning(self, dashboard_path: str):
        """Initialise the provisioning of Grafana dashboards.

        Args:
            dashboard_path: str; A file path to the dashboard to provision
        """
        self._configure()
        logger.info("Initializing dashboard provisioning path")
        container = self.unit.get_container(self.name)

        dashboard_config = {
            "apiVersion": 1,
            "providers": [
                {
                    "name": "Default",
                    "type": "file",
                    "options": {"path": dashboard_path},
                }
            ],
        }

        default_config = os.path.join(dashboard_path, "default.yaml")
        default_config_string = yaml.dump(dashboard_config)

        if not os.path.exists(dashboard_path):
            try:
                container.push(default_config, default_config_string, make_dirs=True)
            except ConnectionError:
                logger.warning(
                    "Could not push default dashboard configuration. Pebble shutting down?"
                )

    def _on_dashboards_changed(self, event) -> None:
        """Handle dashboard events."""
        container = self.unit.get_container(self.name)
        dashboards_dir_path = os.path.join(PROVISIONING_PATH, "dashboards")

        self.init_dashboard_provisioning(dashboards_dir_path)

        if not container.can_connect():
            logger.debug("Cannot connect to Pebble yet, deferring event")
            event.defer()
            return

        dashboards_file_to_be_kept = {}
        try:
            for dashboard_file in container.list_files(dashboards_dir_path, pattern="juju_*.json"):
                dashboards_file_to_be_kept[dashboard_file.path] = False

            for dashboard in self.dashboard_consumer.dashboards:
                dashboard_content = dashboard["content"]
                dashboard_content_bytes = dashboard_content.encode("utf-8")
                dashboard_content_digest = hashlib.sha256(dashboard_content_bytes).hexdigest()
                dashboard_filename = "juju_{}_{}.json".format(
                    dashboard["charm"], dashboard_content_digest[0:7]
                )

                path = os.path.join(dashboards_dir_path, dashboard_filename)
                dashboards_file_to_be_kept[path] = True

                logger.debug("New dashboard %s", path)
                container.push(path, dashboard_content_bytes, make_dirs=True)

            for dashboard_file_path, to_be_kept in dashboards_file_to_be_kept.items():
                if not to_be_kept:
                    container.remove_path(dashboard_file_path)
                    logger.debug("Removed dashboard %s", dashboard_file_path)

            self.restart_grafana()
        except ConnectionError:
            logger.exception("Could not update dashboards. Pebble shutting down?")

    #####################################

    # K8S WRANGLING

    #####################################

    def _patch_k8s_service(self):
        """Fix the Kubernetes service that was setup by Juju with correct port numbers."""
        if self.unit.is_leader() and not self._stored.k8s_service_patched:
            service_ports = [
                (self.app.name, PORT, PORT),
            ]
            try:
                K8sServicePatch.set_ports(self.app.name, service_ports)
            except PatchFailed as e:
                logger.error("Unable to patch the Kubernetes service: %s", str(e))
            else:
                self._stored.k8s_service_patched = True
                logger.info("Successfully patched the Kubernetes service!")

    #####################################

    # DATABASE EVENTS

    #####################################

    @property
    def has_db(self) -> bool:
        """Only consider a DB connection if we have config info."""
        rel = self.model.get_relation(DATABASE)
        return len(rel.units) > 0 if rel is not None else False

    def _on_database_changed(self, event: RelationChangedEvent) -> None:
        """Sets configuration information for database connection.

        Args:
            event: A :class:`RelationChangedEvent` from a `database` source
        """
        if not self.unit.is_leader():
            return

        # Get required information
        database_fields = {
            field: event.relation.data[event.app].get(field) for field in REQUIRED_DATABASE_FIELDS
        }

        # if any required fields are missing, warn the user and return
        missing_fields = [
            field for field in REQUIRED_DATABASE_FIELDS if database_fields.get(field) is None
        ]
        if len(missing_fields) > 0:
            raise SourceFieldsMissingError(
                "Missing required data fields for database relation: {}".format(missing_fields)
            )

        # add the new database relation data to the datastore
        db_info = {field: value for field, value in database_fields.items() if value}
        self.set_peer_data("database", db_info)

        self._configure()

    def _on_database_broken(self, event: RelationBrokenEvent) -> None:
        """Removes database connection info from datastore.

        We are guaranteed to only have one DB connection, so clearing
        datastore.database is all we need for the change to be propagated
        to the Pebble container.

        Args:
            event: a :class:`RelationBrokenEvent` from a `database` source
        """
        if not self.unit.is_leader():
            return

        # remove the existing database info from datastore
        self.set_peer_data("database", {})
        logger.info("Removing the grafana-k8s database backend config")

        # Cleanup the config file
        self._configure()

    def _generate_grafana_config(self) -> str:
        """Generate a database configuration for Grafana.

        For now, this only creates database information, since everything else
        can be set in ENV variables, but leave for expansion later so we can
        hide auth secrets
        """
        return self._generate_database_config() if self.has_db else ""

    def _generate_database_config(self) -> str:
        """Generate a database configuration.

        Returns:
            A string containing the required database information to be stubbed into the config
            file.
        """
        db_config = self.get_peer_data("database")
        if not db_config:
            return ""

        config_ini = configparser.ConfigParser()
        db_type = "mysql"

        db_url = "{0}://{1}:{2}@{3}/{4}".format(
            db_type,
            db_config.get("user"),
            db_config.get("password"),
            db_config.get("host"),
            db_config.get("name"),
        )
        config_ini["database"] = {
            "type": db_type,
            "host": db_config.get("host"),
            "name": db_config.get("name", ""),
            "user": db_config.get("user", ""),
            "password": db_config.get("password", ""),
            "url": db_url,
        }

        # This is silly, but a ConfigParser() handles this nicer than
        # raw string manipulation
        data = StringIO()
        config_ini.write(data)
        data.seek(0)
        ret = data.read()
        data.close()
        return ret

    #####################################

    # PEBBLE OPERATIONS

    #####################################

    def _on_pebble_ready(self, event) -> None:
        """When Pebble is ready, start everything up."""
        self._configure()

    def restart_grafana(self) -> None:
        """Restart the pebble container.

        `container.replan()` is intentionally avoided, since if no environment
        variables are changed, this will not actually restart Grafana, which is
        necessary to reload the provisioning files.

        Note that Grafana does not support SIGHUP, so a full restart is needed.
        """
        layer = self._build_layer()

        try:
            plan = self.container.get_plan()
            if plan.services != layer.services:
                self.container.add_layer(self.name, layer, combine=True)
                if self.container.get_service(self.name).is_running():
                    self.container.stop(self.name)

                self.container.start(self.name)
                logger.info("Restarted grafana-k8s")

            self.unit.status = ActiveStatus()
        except ConnectionError:
            logger.error(
                "Could not restart grafana-k8s -- Pebble socket does "
                "not exist or is not responsive"
            )

    def _parse_grafana_path(self, parts: ParseResult) -> dict:
        """Convert web_external_url into a usable path."""
        # urlparse.path parsing is absolutely horrid and only
        # guarantees any kind of sanity if there is a scheme
        if not parts.scheme and not parts.path.startswith("/"):
            # This could really be anything!
            logger.warning(
                "Could not determine web_external_url for Grafana. Please "
                "use a fully-qualified path or a bare subpath"
            )
            return {}

        return {
            "scheme": parts.scheme or "http",
            "host": "0.0.0.0",
            "port": parts.netloc.split(":")[1] if ":" in parts.netloc else PORT,
            "path": parts.path,
        }

    def _build_layer(self) -> Layer:
        """Construct the pebble layer information."""
        # Placeholder for when we add "proper" mysql support for HA
        extra_info = {
            "GF_DATABASE_TYPE": "sqlite3",
        }

        grafana_path = self.model.config.get("web_external_url", "")

        # We have to do this dance because urlparse() doesn't have any good
        # truthiness, and parsing an empty string is still 'true'
        if grafana_path:
            parts = self._parse_grafana_path(urlparse(grafana_path))

            # It doesn't matter unless there's a subpath, since the
            # redirect to login is fine with a bare hostname
            if parts and parts["path"]:
                extra_info.update(
                    {
                        "GF_SERVER_SERVE_FROM_SUB_PATH": "True",
                        "GF_SERVER_ROOT_URL": "{}://{}:{}{}".format(
                            parts["scheme"], parts["host"], parts["port"], parts["path"]
                        ),
                    }
                )

        layer = Layer(
            {
                "summary": "grafana-k8s layer",
                "description": "grafana-k8s layer",
                "services": {
                    self.name: {
                        "override": "replace",
                        "summary": "grafana-k8s service",
                        "command": "grafana-server -config {}".format(CONFIG_PATH),
                        "startup": "enabled",
                        "environment": {
                            "GF_SERVER_HTTP_PORT": PORT,
                            "GF_LOG_LEVEL": self.model.config["log_level"],
                            "GF_PLUGINS_ENABLE_ALPHA": True,
                            "GF_PATHS_PROVISIONING": PROVISIONING_PATH,
                            "GF_SECURITY_ADMIN_USER": self.model.config["admin_user"],
                            "GF_SECURITY_ADMIN_PASSWORD": self._get_admin_password(),
                            **extra_info,
                        },
                    }
                },
            }
        )

        return layer

    @property
    def grafana_version(self):
        """Grafana server version."""
        info = self.grafana_service.build_info
        if info:
            return info.get("version", None)
        return None

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

    def _get_hash_for_file(self, file: str) -> str:
        """Tries to connect to the container and hash a file.

        Args:
            file: a `str` filepath to read
        """
        if self.container.can_connect():
            try:
                content = self.container.pull(file)
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
    def build_info(self) -> dict:
        """Returns information about the running Grafana service."""
        return self.grafana_service.build_info

    def _generate_datasource_config(self) -> str:
        """Template out a Grafana datasource config.

        Template using the sources (and removed sources) the consumer knows about, and dump it to
        YAML.

        Returns:
            A a string-dumped YAML config for the datasources
        """
        # Boilerplate for the config file
        datasources_dict = {"apiVersion": 1, "datasources": [], "deleteDatasources": []}

        for source_info in self.source_consumer.sources:
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

            # set timeout for querying this data source
            timeout = source.get("jsonData", {}).get("timeout", 0)
            configured_timeout = self.model.config.get("datasource_query_timeout")
            if timeout < configured_timeout:
                json_data = source.get("jsonData", {})
                json_data.update({"timeout": configured_timeout})
                source["jsonData"] = json_data

            datasources_dict["datasources"].append(source)  # type: ignore[attr-defined]

        # Also get a list of all the sources which have previously been purged and add them
        for name in self.source_consumer.sources_to_delete:
            source = {"orgId": 1, "name": name}
            datasources_dict["deleteDatasources"].append(source)  # type: ignore[attr-defined]

        datasources_string = yaml.dump(datasources_dict)
        return datasources_string

    def _on_get_admin_password(self, event: ActionEvent) -> None:
        """Returns the password for the admin user as an action response."""
        if not self.grafana_service.is_ready:
            event.fail("Grafana is not reachable yet. Please try again in a few minutes")
            return
        if self.grafana_service.password_has_been_changed(
            self.model.config["admin_user"], self._get_admin_password()
        ):
            event.set_results(
                {"admin-password": "Admin password has been changed by an administrator"}
            )
        else:
            event.set_results({"admin-password": self._get_admin_password()})

    def _get_admin_password(self) -> str:
        """Returns the password for the admin user."""
        if not self._stored.admin_password:
            self._stored.admin_password = self._generate_password()

        return self._stored.admin_password

    def _generate_password(self) -> str:
        """Generates a random 12 character password."""
        # Really limited by what can be passed into shell commands, since this all goes
        # through subprocess. So much for complex password
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(12))

    def _resource_reqs_from_config(self) -> ResourceRequirements:
        limits = {"cpu": self.model.config.get("cpu"), "memory": self.model.config.get("memory")}
        requests = {"cpu": "0.25", "memory": "200Mi"}
        return adjust_resource_requirements(limits, requests, adhere_to_requests=True)

    def _on_resource_patch_failed(self, event: K8sResourcePatchFailedEvent):
        self.unit.status = BlockedStatus(event.message)


if __name__ == "__main__":
    main(GrafanaCharm, use_juju_for_storage=True)
