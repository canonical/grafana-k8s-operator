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
import logging
import os
import secrets
import string
from io import StringIO

import yaml
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardConsumer
from charms.grafana_k8s.v0.grafana_source import (
    GrafanaSourceConsumer,
    GrafanaSourceEvents,
    SourceFieldsMissingError,
)
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
from ops.model import ActiveStatus, MaintenanceStatus
from ops.pebble import ConnectionError, Layer

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
DATASOURCE_PATH = "/etc/grafana/provisioning"
PEER = "grafana-peers"

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
        self.grafana_config_ini_hash = None
        self.grafana_datasources_hash = None
        self._stored.set_default(
            database=dict(), pebble_ready=False, k8s_service_patched=False, admin_password=""
        )

        # -- standard events
        self.framework.observe(self.on.install, self._on_install)  # type: ignore[arg-type]
        self.framework.observe(self.on.grafana_pebble_ready, self._on_pebble_ready)  # type: ignore[arg-type]
        self.framework.observe(self.on.config_changed, self._on_config_changed)  # type: ignore[arg-type]
        self.framework.observe(self.on.stop, self._on_stop)  # type: ignore[arg-type]
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)  # type: ignore[arg-type]
        self.framework.observe(self.on.get_admin_password_action, self._on_get_admin_password)  # type: ignore[arg-type]

        # -- grafana_source relation observations
        self.source_consumer = GrafanaSourceConsumer(self, "grafana-source")
        self.framework.observe(
            self.source_consumer.on.sources_changed,
            self._on_grafana_source_changed,  # type: ignore[arg-type]
        )
        self.framework.observe(
            self.source_consumer.on.sources_to_delete_changed,
            self._on_grafana_source_changed,  # type: ignore[arg-type]
        )

        # -- grafana_dashboard relation observations
        self.dashboard_consumer = GrafanaDashboardConsumer(self, "grafana-dashboard")
        self.framework.observe(
            self.dashboard_consumer.on.dashboards_changed, self._on_dashboards_changed  # type: ignore[arg-type]
        )

        # -- database relation observations
        self.framework.observe(self.on["database"].relation_changed, self._on_database_changed)  # type: ignore[arg-type]
        self.framework.observe(self.on["database"].relation_broken, self._on_database_broken)  # type: ignore[arg-type]

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

        if restart:
            self.restart_grafana()

    def _update_datasource_config(self, config: str) -> None:
        """Write an updated datasource configuration file to the Pebble container if necessary.

        Args:
            config: A :str: containing the datasource configuration
        """
        container = self.unit.get_container(self.name)

        datasources_path = os.path.join(DATASOURCE_PATH, "datasources", "datasources.yaml")
        try:
            container.push(datasources_path, config)
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
            self.container.push(CONFIG_PATH, config)
        except ConnectionError:
            logger.error(
                "Could not push datasource config. Pebble refused connection. Shutting down?"
            )

    @property
    def has_peers(self) -> bool:
        """Check whether or nto there are any other Grafanas as peers."""
        rel = self.model.get_relation(PEER)
        return len(rel.units) > 0 if rel is not None else False

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
        dashboards_dir_path = os.path.join(DATASOURCE_PATH, "dashboards")

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
                container.push(path, dashboard_content_bytes)

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
                (f"{self.app.name}", PORT, PORT),
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
        return len(self._stored.database) > 0

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
                f"Missing required data fields for database relation: {missing_fields}"
            )

        # add the new database relation data to the datastore
        self._stored.database.update(
            {field: value for field, value in database_fields.items() if value is not None}
        )

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
        self._stored.database = dict()
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
        db_config = self._stored.database
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
        self._stored.pebble_ready = True
        self._configure()

    def restart_grafana(self) -> None:
        """Restart the pebble container."""
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

    def _build_layer(self) -> Layer:
        """Construct the pebble layer information."""
        # Placeholder for when we add "proper" mysql support for HA
        dbinfo = {"GF_DATABASE_TYPE": "sqlite3"}

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
                            "GF_PATHS_PROVISIONING": DATASOURCE_PATH,
                            "GF_SECURITY_ADMIN_USER": self.model.config["admin_user"],
                            "GF_SECURITY_ADMIN_PASSWORD": self._get_admin_password(),
                            **dbinfo,
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
                "name": source_info["source-name"],
                "type": source_info["source-type"],
                "url": source_info["url"],
            }
            datasources_dict["datasources"].append(source)  # type: ignore[attr-defined]

        # Also get a list of all the sources which have previously been purged and add them
        for name in self.source_consumer.sources_to_delete:
            source = {"orgId": 1, "name": name}
            datasources_dict["deleteDatasources"].append(source)  # type: ignore[attr-defined]

        datasources_string = yaml.dump(datasources_dict)
        return datasources_string

    def _on_get_admin_password(self, event: ActionEvent) -> None:
        """Returns the password for the admin user as an action response."""
        if self.grafana_service.password_has_been_changed:
            event.set_results({"admin-password": "Admin password has been changed by an administrator"})
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


if __name__ == "__main__":
    main(GrafanaCharm, use_juju_for_storage=True)
