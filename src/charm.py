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
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus, BlockedStatus, WaitingStatus

from grafana_server import Grafana
import config as grafana_config
from grafana_provider import GrafanaSourceProvider
from lib.charms.ingress.v0.ingress import IngressRequires


logger = logging.getLogger()

PEER = "grafana"
SERVICE = "grafana"


class GrafanaCharm(CharmBase):
    """Charm to run Grafana on Kubernetes.

    This charm allows for high-availability
    (as long as a non-sqlite database relation is present).

    Developers of this charm should be aware of the Grafana provisioning docs:
    https://grafana.com/docs/grafana/latest/administration/provisioning/
    """

    _stored = StoredState()

    def __init__(self, *args):
        logger.debug('Initializing charm.')
        super().__init__(*args)

        self.grafana = Grafana("localhost", str(self.model.config['port']))

        # -- initialize states --
        self.ingress = None
        self._stored.set_default(database=dict())  # db configuration
        self._stored.set_default(provider_ready=False)
        self._stored.set_default(grafana_config_ini_hash=None)
        self._stored.set_default(grafana_datasources_hash=None)

        # -- standard hooks
        self.framework.observe(self.on.grafana_pebble_ready, self.on_pebble_ready)
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        self.framework.observe(self.on.stop, self.on_stop)

        # -- grafana (peer) relation observations
        self.framework.observe(self.on[PEER].relation_changed,
                               self.on_peer_changed)
        # self.framework.observe(self.on['grafana'].relation_departed,
        #                        self.on_peer_departed)

        # -- database relation observations
        self.framework.observe(self.on['database'].relation_changed,
                               self.on_database_changed)
        self.framework.observe(self.on['database'].relation_broken,
                               self.on_database_broken)

        # -- actions observations
        self.framework.observe(
            self.on.import_dashboard_action, self.on_import_dashboard_action
        )

        self.framework.observe(
            self.on.add_ingress_action, self.on_add_ingress_action
        )

        # -- grafana-source relation observations
        self.grafana_provider = GrafanaSourceProvider(self, 'grafana-source',
                                                      'grafana', self.version)
        self.framework.observe(self.grafana_provider.on.grafana_sources_changed,
                               self.on_grafana_source_changed)
        self.framework.observe(self.grafana_provider.on.grafana_sources_to_delete_changed,
                               self.on_grafana_source_broken)

    def on_pebble_ready(self, event):
        self._configure(event)
        logger.debug("Pebble ready")

        container = event.workload
        if not container.get_service(SERVICE).is_running():
            logger.info("Starting Grafana")
            container.start(SERVICE)

    def on_config_changed(self, event):
        self._configure(event)
        self.grafana_provider.update_port(SERVICE, self.model.config["port"])

    def on_grafana_source_changed(self, event):
        """When a grafana-source is added or modified, update the config"""

        logger.debug("Source changed")
        self._configure(event)

    def on_grafana_source_broken(self, event):
        """When a grafana-source is removed, update the config"""

        logger.debug("Source removed")
        self._configure(event)

    def on_stop(self, _):
        """Go into maintenance state if the unit is stopped."""
        self.unit.status = MaintenanceStatus('Application is terminating.')

    def _configure(self, _):
        logger.info("Handling config change")

        restart = False

        grafana_config_ini = self.generate_grafana_config()
        config_ini_hash = hashlib.md5(str(grafana_config_ini).encode('utf-8')).hexdigest()
        if not self._stored.grafana_config_ini_hash == config_ini_hash:
            self._stored.grafana_config_ini_hash = config_ini_hash
            self.update_grafana_config_ini(grafana_config_ini)
            logger.info("Pushed new grafana base configuration")

            restart = True

        grafana_datasources = self.generate_datasource_config()
        datasources_hash = hashlib.md5(str(grafana_datasources).encode('utf-8')).hexdigest()
        if not self._stored.grafana_datasources_hash == datasources_hash:
            self._stored.grafana_datasources_hash = datasources_hash
            self.update_datasource_config(grafana_datasources)
            logger.info("Pushed new datasource configuration")

            restart = True

        if restart:
            self.restart_grafana()

    def generate_datasource_config(self):
        datasources_dict = {"apiVersion": 1, "datasources": [], "deleteDatasources": []}

        for source_info in self.grafana_provider.sources():
            source = {
                "orgId": "1",
                "access": "proxy",
                "isDefault": source_info["isDefault"],
                "name": source_info["source-name"],
                "type": source_info["source-type"],
                "url": "http://{}:{}".format(
                    source_info["private-address"], source_info["port"]
                ),
            }
            datasources_dict["datasources"].append(source)

        for name in self.grafana_provider.sources_to_delete():
            source = {"orgId": 1, "name": name}
            datasources_dict["deleteDatasources"].append(source)

        datasources_string = yaml.dump(datasources_dict)
        return datasources_string

    def generate_grafana_config(self):
        return self.generate_database_config() if self.has_db else ""

    def update_datasource_config(self, config):
        container = self.unit.get_container(SERVICE)

        datasources_path = os.path.join(
            grafana_config.DATASOURCE_PATH, "datasources", "datasources.yaml"
        )
        container.push(datasources_path, config)

    def update_grafana_config_ini(self, config):
        container = self.unit.get_container(SERVICE)
        container.push(grafana_config.CONFIG_PATH, config)

    #####################################

    # HIGH AVAILABILITY

    #####################################

    @property
    def has_peer(self) -> bool:
        rel = self.model.get_relation('grafana')
        return len(rel.units) > 0 if rel is not None else False

    def check_high_availability(self):
        """Checks whether the configuration allows for HA."""
        if self.has_peer:
            if self.has_db:
                logger.info('high availability possible.')
                status = MaintenanceStatus('Grafana ready for HA.')
            else:
                logger.warning('high availability not possible '
                               'with current configuration.')
                status = BlockedStatus('Need database relation for HA.')
        else:
            logger.info('running Grafana on single node.')
            status = MaintenanceStatus('Grafana ready on single node.')

        # make sure we don't have a maintenance status overwrite
        # a currently active status
        if isinstance(status, MaintenanceStatus) \
                and isinstance(self.unit.status, ActiveStatus):
            return status

        self.unit.status = status
        return status

    def on_peer_changed(self, _):
        self.check_high_availability()

    def on_peer_departed(self, _):
        self.check_high_availability()

    ############################
    # DASHBOARD IMPORT
    ###########################
    def init_dashboard_provisioning(self, dashboard_path):
        container = self.unit.get_container(SERVICE)

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
        container = self.unit.get_container(SERVICE)
        dashboard_path = os.path.join(
            grafana_config.DATASOURCE_PATH, "dashboards")

        self.init_dashboard_provisioning(dashboard_path)
        dashboard_base64_string = event.params["dashboard"]

        name = "{}.json".format(uuid.uuid4())
        imported_dashboard_path = os.path.join(dashboard_path, name)
        imported_dashboard_string = base64.b64decode(
            dashboard_base64_string).decode("ascii")

        logger.info(
            "Newly created dashboard will be saved at: {}".format(dashboard_path)
        )
        container.push(imported_dashboard_path,
                       imported_dashboard_string, make_dirs=True)

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

    def on_database_changed(self, event):
        """Sets configuration information for database connection."""
        if not self.unit.is_leader():
            return

        if event.unit is None:
            return

        # save the necessary configuration of this database connection
        database_fields = {
            field: event.relation.data[event.unit].get(field)
            for field in grafana_config.REQUIRED_DATABASE_FIELDS
        }

        # if any required fields are missing, warn the user and return
        missing_fields = [
            field for field in grafana_config.REQUIRED_DATABASE_FIELDS
            if database_fields.get(field) is None
        ]
        if len(missing_fields) > 0:
            logger.error(
                "Missing required data fields for related database "
                "relation: {}".format(missing_fields)
            )
            return

        # add the new database relation data to the datastore
        self._stored.database.update(
            {
                field: value for field, value in database_fields.items()
                if value is not None
            }
        )

        logger.info("Configuring database settings ...")
        self._configure(event)

    def on_database_broken(self, event):
        """Removes database connection info from datastore.
        We are guaranteed to only have one DB connection, so clearing
        datastore.database is all we need for the change to be propagated
        to the pod spec."""
        if not self.unit.is_leader():
            return

        # remove the existing database info from datastore
        self._stored.database = dict()
        logger.info("Removing the Grafana database backend config")

        # Cleanup the config file
        self._configure(event)

    def generate_database_config(self):
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

        logger.info("Config set to :{}".format(config_ini))

        data = StringIO()
        config_ini.write(data)
        data.seek(0)
        ret = data.read()
        data.close()
        return ret

    #####################################

    # PEBBLE OPERATIONS

    #####################################

    def restart_grafana(self):
        container = self.unit.get_container(SERVICE)
        layer = self._grafana_layer()

        plan = container.get_plan()
        if plan.services != layer["services"]:
            container.add_layer("grafana", layer, combine=True)

            if container.get_service(SERVICE).is_running():
                container.stop(SERVICE)

            container.start(SERVICE)
            logger.info("Restarted grafana container")

        self.app.status = ActiveStatus()
        self.unit.status = ActiveStatus()

    def _grafana_layer(self):
        """Construct the pebble layer
        """
        logger.info('Building pebble layer')

        charm_config = self.model.config

        layer = {
            "summary": "grafana layer",
            "description": "grafana layer",
            "services": {
                "grafana": {
                    "override": "replace",
                    "summary": "grafana service",
                    "command": "grafana-server -config {}".format(grafana_config.CONFIG_PATH),
                    "startup": "enabled",
                    "environment": {
                        "GF_HTTP_PORT": charm_config["port"],
                        "GF_LOG_LEVEL": charm_config["grafana_log_level"],
                        "GF_PATHS_PROVISIONING": grafana_config.DATASOURCE_PATH,
                    },
                }
            },
        }

        return layer

    #####################################

    # OPERATOR METHODS

    #####################################

    def _on_update_status(self, _):
        """Various health checks of the charm."""
        if not self.unit.is_leader():
            self.unit.status = ActiveStatus()
            return

        if not self.grafana.is_ready():
            status_message = "Grafana is not ready yet"
            self.unit.status = WaitingStatus(status_message)
            return

        provided = {'grafana': self.version}
        logger.info("Grafana provider is available")
        logger.info("Providing : {}".format(provided))
        if not self._stored.provider_ready:
            self._stored.provider_ready = True
            self.grafana_provider = GrafanaSourceProvider(self, 'grafana-source',
                                                          'grafana', self.version)
            self.framework.observe(self.grafana_provider.on.grafana_sources_changed,
                                   self.on_grafana_source_changed)
            self.framework.observe(self.grafana_provider.on.grafana_sources_to_delete_changed,
                                   self.on_grafana_source_broken)
            self.grafana_provider.ready()

        # self._check_high_availability()
        self.unit.status = ActiveStatus()

    @property
    def version(self):
        """Grafana version."""
        info = self.grafana.build_info
        if info:
            return info.get('version', None)
        return None


if __name__ == '__main__':
    main(GrafanaCharm, use_juju_for_storage=True)
