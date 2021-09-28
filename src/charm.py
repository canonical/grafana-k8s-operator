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

import base64
import configparser
import hashlib
import logging
import os
import zlib
from io import StringIO

import yaml
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from charms.grafana_k8s.v0.grafana_source import (
    GrafanaSourceEvents,
    GrafanaSourceProvider,
    SourceFieldsMissingError,
)
from ops.charm import (
    CharmBase,
    CharmEvents,
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
        self.grafana_service = Grafana("localhost", self.model.config["port"])
        self.grafana_config_ini_hash = None
        self.grafana_datasources_hash = None
        self._stored.set_default(database=dict(), pebble_ready=False)

        # -- standard events
        self.framework.observe(self.on.grafana_pebble_ready, self._on_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)

        # -- grafana_source relation observations
        self.source_provider = GrafanaSourceProvider(self, "grafana-source")
        self.framework.observe(
            self.source_provider.on.sources_changed,
            self._on_grafana_source_changed,
        )
        self.framework.observe(
            self.source_provider.on.sources_to_delete_changed,
            self._on_grafana_source_changed,
        )

        # -- grafana_dashboard relation observations
        self.dashboard_provider = GrafanaDashboardProvider(self, "grafana-dashboard")
        self.framework.observe(
            self.dashboard_provider.on.dashboards_changed, self._on_dashboards_changed
        )

        # -- database relation observations
        self.framework.observe(self.on["database"].relation_changed, self._on_database_changed)
        self.framework.observe(self.on["database"].relation_broken, self._on_database_broken)

    def _on_config_changed(self, event: ConfigChangedEvent) -> None:
        """Event handler for the config-changed event.

        If the configuration is changed, update the variables we know about and
        restart the services. We don't know specifically whether it's a new install,
        a relation change, a leader election, or other, so call `_configure` to check
        the config files

        Args:
            event: a :class:`ConfigChangedEvent` to signal that something happened
        """
        self.source_provider.update_port(self.name, self.model.config["port"])
        self._configure(event)

    def _on_grafana_source_changed(self, event: GrafanaSourceEvents) -> None:
        """When a grafana-source is added or modified, update the config.

        Args:
            event: a :class:`GrafanaSourceEvents` instance sent from the consumer
        """
        self.dashboard_provider.renew_dashboards(self.source_provider.sources)
        self._configure(event)

    def _on_upgrade_charm(self, event: UpgradeCharmEvent) -> None:
        """Re-provision Grafana and its datasources on upgrade.

        Args:
            event: a :class:`UpgradeCharmEvent` to signal the upgrade
        """
        self._configure(event)
        self._on_dashboards_changed(event)

    def _on_stop(self, _) -> None:
        """Go into maintenance state if the unit is stopped."""
        self.unit.status = MaintenanceStatus("Application is terminating.")

    def _configure(self, event: CharmEvents) -> None:
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
            logger.info("Pushed new grafana-k8s base configuration")

            restart = True

        # Do the same thing for datasources
        grafana_datasources = self._generate_datasource_config()
        datasources_hash = hashlib.sha256(str(grafana_datasources).encode("utf-8")).hexdigest()
        if not self.grafana_datasources_hash == datasources_hash:
            self.grafana_datasources_hash = datasources_hash
            self._update_datasource_config(grafana_datasources)
            logger.info("Pushed new grafana-k8s datasource configuration")

            restart = True

        if restart:
            self.restart_grafana()

    def _update_datasource_config(self, config: str) -> None:
        """Write an updated datasource configuration file to the Pebble container if necessary.

        Args:
            config: A :str: containing the datasource configuraiton
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
            config: A :str: containing the datasource configuraiton
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

    def _on_dashboards_changed(self, _) -> None:
        """Handle dashboard events."""
        container = self.unit.get_container(self.name)
        dashboard_path = os.path.join(DATASOURCE_PATH, "dashboards")

        self.init_dashboard_provisioning(dashboard_path)

        existing_dashboards = {}
        try:
            for f in container.list_files(dashboard_path, pattern="*_juju.json"):
                existing_dashboards[f.path] = False
        except ConnectionError:
            logger.warning("Could not list dashboards. Pebble shutting down?")

        for dashboard in self.dashboard_provider.dashboards:
            for fname, tmpl in dashboard["dashboard"]["templates"].items():
                dash = zlib.decompress(base64.b64decode(tmpl.encode())).decode()
                name = "{}_{}_juju.json".format(dashboard["target"], fname)

                dashboard_path = os.path.join(dashboard_path, name)
                existing_dashboards[dashboard_path] = True

                logger.info("Newly created dashboard will be saved at: {}".format(dashboard_path))
                container.push(dashboard_path, dash, make_dirs=True)

        for f, known in existing_dashboards.items():
            logger.debug("Checking for dashboard {}".format(f))
            if not known:
                logger.info("Removing unknown dashboard {}".format(f))
                container.remove_path(f)

        self.restart_grafana()

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
                "Missing required data fields for grafana-k8s database "
                "relation: {}".format(missing_fields)
            )

        # add the new database relation data to the datastore
        self._stored.database.update(
            {field: value for field, value in database_fields.items() if value is not None}
        )

        self._configure(event)

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
        self._configure(event)

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
        self._configure(event)

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
                            "GF_SERVER_HTTP_PORT": self.model.config["port"],
                            "GF_LOG_LEVEL": self.model.config["log_level"],
                            "GF_PATHS_PROVISIONING": DATASOURCE_PATH,
                            "GF_SECURITY_ADMIN_USER": self.model.config["admin_user"],
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

        for source_info in self.source_provider.sources:
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
        for name in self.source_provider.sources_to_delete:
            source = {"orgId": 1, "name": name}
            datasources_dict["deleteDatasources"].append(source)  # type: ignore[attr-defined]

        datasources_string = yaml.dump(datasources_dict)
        return datasources_string


if __name__ == "__main__":
    main(GrafanaCharm, use_juju_for_storage=True)
