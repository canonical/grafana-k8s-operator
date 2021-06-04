#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import configparser
import logging
import hashlib
import os
import uuid
import yaml

from io import StringIO
from ops.charm import (
    CharmBase,
    ConfigChangedEvent,
    RelationBrokenEvent,
    RelationChangedEvent,
)
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, WaitingStatus
from ops.pebble import Layer

from lib.charms.grafana.v1.grafana_source import (
    GrafanaSourceProvider,
    GrafanaSourceEvents,
    SourceFieldsMissingError,
)
from lib.charms.ingress.v0.ingress import IngressRequires


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
VERSION = "1.0.0"


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
        self.name = "grafana"
        self.container = self.unit.get_container(self.name)

        # -- initialize states --
        self.ingress = None
        self._stored.set_default(database=dict())  # db configuration
        self._stored.set_default(pebble_ready=False)
        self._stored.set_default(grafana_config_ini_hash=None)
        self._stored.set_default(grafana_datasources_hash=None)

        # -- standard events
        self.framework.observe(self.on.grafana_pebble_ready, self.on_pebble_ready)
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        self.framework.observe(self.on.stop, self.on_stop)

        # -- grafana-source relation observations
        self.provider = GrafanaSourceProvider(
            self, "grafana-source", "grafana", VERSION
        )
        self.framework.observe(
            self.provider.on.sources_changed,
            self.on_grafana_source_changed,
        )
        self.framework.observe(
            self.provider.on.sources_to_delete_changed,
            self.on_grafana_source_changed,
        )

        # -- database relation observations
        self.framework.observe(
            self.on["database"].relation_changed, self.on_database_changed
        )
        self.framework.observe(
            self.on["database"].relation_broken, self.on_database_broken
        )

    def on_config_changed(self, event: ConfigChangedEvent) -> None:
        """
        If the configuration is changed, update the variables we know about and
        restart the services. We don't know specifically whether it's a new install,
        a relation change, a leader election, or other, so call `_configure` to check
        the config files

        Args:
            event: a :class:`ConfigChangedEvent` to signal that something happened
        """
        self.provider.update_port(self.name, self.model.config["port"])
        self._configure(event)

    def on_grafana_source_changed(self, event: GrafanaSourceEvents) -> None:
        """
        When a grafana-source is added or modified, update the config

        Args:
            event: a :class:`GrafanaSourceEvents` instance sent from the consumer
        """
        self._configure(event)

    def on_stop(self, _) -> None:
        """Go into maintenance state if the unit is stopped."""
        self.unit.status = MaintenanceStatus("Application is terminating.")

    def _configure(self, _) -> None:
        """
        Generate configuration files and check the sums against what is
        already stored in the charm. If either the base Grafana config
        or the datasource config differs, restart Grafana.
        """

        logger.debug("Handling grafana-k8a configuration change")
        restart = False

        # Generate a new base config and see if it differs from what we have.
        # If it does, store it and signal that we should restart Grafana
        grafana_config_ini = self.generate_grafana_config()
        config_ini_hash = hashlib.md5(
            str(grafana_config_ini).encode("utf-8")
        ).hexdigest()
        if not self._stored.grafana_config_ini_hash == config_ini_hash:
            self._stored.grafana_config_ini_hash = config_ini_hash
            self.update_grafana_config_ini(grafana_config_ini)
            logger.debug("Pushed new grafana base configuration")

            restart = True

        # Do the same thing for datasources
        grafana_datasources = self.provider.generate_datasource_config()
        datasources_hash = hashlib.md5(
            str(grafana_datasources).encode("utf-8")
        ).hexdigest()
        if not self._stored.grafana_datasources_hash == datasources_hash:
            self._stored.grafana_datasources_hash = datasources_hash
            self.update_datasource_config(grafana_datasources)
            logger.debug("Pushed new datasource configuration")

            restart = True

        if restart:
            self.restart_grafana()

    def update_datasource_config(self, config: str) -> None:
        """
        Write an updated datasource configuration file to the
        Pebble container if necessary.

        Args:
            config: A :str: containing the datasource configuraiton
        """
        container = self.unit.get_container(self.name)

        datasources_path = os.path.join(
            DATASOURCE_PATH, "datasources", "datasources.yaml"
        )
        container.push(datasources_path, config)

    def update_grafana_config_ini(self, config: str) -> None:
        """
        Write an updated Grafana configuration file to the
        Pebble container if necessary

        Args:
            config: A :str: containing the datasource configuraiton
        """
        self.container.push(CONFIG_PATH, config)

    @property
    def has_peers(self) -> bool:
        """Check whether or nto there are any other Grafanas as peers"""
        rel = self.model.get_relation(self.name)
        return len(rel.units) > 0 if rel is not None else False

    ############################
    # DASHBOARD IMPORT
    ###########################
    def init_dashboard_provisioning(self, dashboard_path: str):
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
            logger.info("Creating the initial Dashboards config")
            container.push(default_config, default_config_string, make_dirs=True)

    def on_import_dashboard_action(self, event):
        container = self.unit.get_container(self.name)
        dashboard_path = os.path.join(DATASOURCE_PATH, "dashboards")

        self.init_dashboard_provisioning(dashboard_path)
        dashboard_base64_string = event.params["dashboard"]

        name = "{}.json".format(uuid.uuid4())
        imported_dashboard_path = os.path.join(dashboard_path, name)
        imported_dashboard_string = base64.b64decode(dashboard_base64_string).decode(
            "ascii"
        )

        logger.info(
            "Newly created dashboard will be saved at: {}".format(dashboard_path)
        )
        container.push(
            imported_dashboard_path, imported_dashboard_string, make_dirs=True
        )

        self.restart_grafana()

    def on_add_ingress_action(self, event):
        self.ingress = IngressRequires(
            self,
            {
                "service-hostname": event.params["external_hostname"],
                "service-name": self.app.name,
                "service-port": self.model.config["port"],
            },
        )

    #####################################

    # DATABASE EVENTS

    #####################################

    @property
    def has_db(self) -> bool:
        """Only consider a DB connection if we have config info."""
        return len(self._stored.database) > 0

    def on_database_changed(self, event: RelationChangedEvent) -> None:
        """Sets configuration information for database connection.

        Args:
            event: A :class:`RelationChangedEvent` from a `database` source
        """
        if not self.unit.is_leader():
            return

        if event.unit is None:
            return

        # Get required information
        database_fields = {
            field: event.relation.data[event.unit].get(field)
            for field in REQUIRED_DATABASE_FIELDS
        }

        # if any required fields are missing, warn the user and return
        missing_fields = [
            field
            for field in REQUIRED_DATABASE_FIELDS
            if database_fields.get(field) is None
        ]
        if len(missing_fields) > 0:
            raise SourceFieldsMissingError(
                "Missing required data fields for grafana-k8s database "
                "relation: {}".format(missing_fields)
            )

        # add the new database relation data to the datastore
        self._stored.database.update(
            {
                field: value
                for field, value in database_fields.items()
                if value is not None
            }
        )

        self._configure(event)

    def on_database_broken(self, event: RelationBrokenEvent) -> None:
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

    def generate_grafana_config(self) -> str:
        """
        For now, this only creates database information, since everything else
        can be set in ENV variables, but leave for expansion later so we can
        hide auth secrets
        """
        return self.generate_database_config() if self.has_db else ""

    def generate_database_config(self) -> str:
        """
        Returns a :str: containing the required database information to
        be stubbed into the config file
        """
        db_config = self._stored.database
        config_ini = configparser.ConfigParser()
        db_type = "mysql"

        db_url = "{0}://{3}:{4}@{1}/{2}".format(
            db_type,
            db_config.get("host"),
            db_config.get("database"),
            db_config.get("user"),
            db_config.get("password"),
        )
        config_ini["database"] = {
            "type": db_type,
            "host": self._stored.database.get("host"),
            "name": db_config.get("database", ""),
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

    def on_pebble_ready(self, _) -> None:
        """
        When Pebble is ready, start everything up
        """
        self._stored.pebble_ready = True
        self._configure_container()

    def restart_grafana(self) -> None:
        """Restart the pebble container"""
        layer = self._build_layer()

        plan = self.container.get_plan()
        if plan.services != layer.services:
            self.container.add_layer(self.name, layer, combine=True)

            if self.container.get_service(self.name).is_running():
                self.container.stop(self.name)

            self.container.start(self.name)
            logger.info("Restarted grafana-k8s")

        self.unit.status = ActiveStatus()

    def _build_layer(self) -> Layer:
        """Construct the pebble layer information"""
        if self.has_peers:
            # mysql_uri = self.mysql.get_cluster_info()
            mysql_uri = "fake data for now"
            # Populate for a MySQL relation
            dbinfo = {"GF_DATABASE_TYPE": "mysql", "GF_DATABASE_URL": mysql_uri}
        else:
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
                            "GF_LOG_LEVEL": self.model.config["grafana_log_level"],
                            "GF_PATHS_PROVISIONING": DATASOURCE_PATH,
                            "GF_SECURITY_ADMIN_USER": self.model.config["admin_user"],
                            "GF_SECURITY_ADMIN_PASSWORD": self.model.config[
                                "admin_password"
                            ],
                            **dbinfo,
                        },
                    }
                },
            }
        )

        return layer

    def _configure_container(self) -> bool:
        """Configure the Pebble layer for grafana-k8s."""

        if self.has_peers:
            # if not self.mysql.is_valid():
            if True:
                logger.warning(
                    "A MySQL relation is needed for Grafana to "
                    "function in HA mode. Blocking until a "
                    "relation is added or the application "
                    "is scaled down"
                )
                self.unit.status = BlockedStatus("Missing MySQL relation")
                return False

        if not self._stored.pebble_ready:
            self.unit.status = WaitingStatus("Waiting for Pebble startup to complete")

        layer = self._build_layer()
        if self.has_peers and not layer.services.grafana.environment.GF_DATABASE_URL:
            self.unit.status = MaintenanceStatus("Related MySQL not yet ready")

        self.container.add_layer("grafana", layer, combine=True)
        self.container.autostart()
        self.provider.ready()
        self.unit.status = ActiveStatus()

    @property
    def grafana_version(self):
        """Grafana server version."""
        info = self.provider.build_info
        if info:
            return info.get("version", None)
        return None


if __name__ == "__main__":
    main(GrafanaCharm, use_juju_for_storage=True)
