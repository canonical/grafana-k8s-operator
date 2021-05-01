#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import logging
import hashlib
import os
import yaml

from io import StringIO
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus, BlockedStatus, WaitingStatus

import grafana_config
from grafana_server import Grafana
from grafana_provider import GrafanaProvider


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
        self._stored.set_default(database=dict())  # db configuration
        self._stored.set_default(provider_ready=False)
        self._stored.set_default(grafana_config_ini_hash=None)
        self._stored.set_default(grafana_datasources_hash=None)

        # -- standard hooks
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.grafana_pebble_ready, self._on_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.update_status, self._on_update_status)
        self.framework.observe(self.on.stop, self._on_stop)

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

        # -- grafana-source relation observations
        if self._stored.provider_ready:
            self.grafana_provider = GrafanaProvider(self, 'grafana-source',
                                                    'grafana', self.version)
            self.framework.observe(self.grafana_provider.on.grafana_sources_changed,
                                   self._on_grafana_source_changed)
            self.framework.observe(self.grafana_provider.on.grafana_sources_to_delete_changed,
                                   self._on_grafana_source_broken)

    def _on_pebble_ready(self, event):
        logger.info("PEBBLE READY")
        self._on_config_changed(event)

    def _on_grafana_source_changed(self, event):
        """When a grafana-source is added or modified, update the config"""

        logger.debug("Source changed")
        if not self.grafana.is_ready():
            event.defer()
        self._on_config_changed(event)

    def _on_grafana_source_broken(self, event):
        """When a grafana-source is removed, update the config"""

        logger.debug("Source removed")
        if not self.grafana.is_ready():
            event.defer()
        self._on_config_changed(event)

    def _on_start(self, event):
        """Start Grafana

        This event handler is deferred if starting Grafana
        fails so we wait until it's ready
        """

        if not self.unit.is_leader():
            return

        if not self.grafana.is_ready():
            status_message = "Waiting for Grafana"
            self.unit.status = WaitingStatus(status_message)
            logger.debug(status_message)
            event.defer()
            return

        self._on_update_status(event)
        self.unit.status = ActiveStatus()

    def _on_stop(self, _):
        """Go into maintenance state if the unit is stopped."""
        self.unit.status = MaintenanceStatus('Application is terminating.')

    def _on_config_changed(self, event):
        logger.info("Handling config change")

        missing_config = self._check_config()
        if missing_config:
            logger.error('Incomplete Configuration: {}. '
                         'Application will be blocked.'.format(missing_config))
            self.unit.status = \
                BlockedStatus('Missing configuration: {}'.format(missing_config))
            return

        grafana_config_ini = self._generate_grafana_config()
        config_ini_hash = hashlib.md5(str(grafana_config_ini).encode('utf-8')).hexdigest()
        logger.info("config_ini_hash: {}".format(config_ini_hash))
        if not self._stored.grafana_config_ini_hash == config_ini_hash:
            logger.info("_stored config_ini_hash is {}".format(self._stored.grafana_config_ini_hash))
            self._stored.grafana_config_ini_hash = config_ini_hash
            logger.info("_stored config_ini_hash is {}".format(self._stored.grafana_config_ini_hash))
            self._update_grafana_config_ini(grafana_config_ini)
            logger.info("Pushed new grafana base configuration")

        grafana_datasources = self._generate_datasource_config()
        datasources_hash = hashlib.md5(str(grafana_datasources).encode('utf-8')).hexdigest()
        logger.info("datasource_hash: {}".format(datasources_hash))
        if not self._stored.grafana_datasources_hash == datasources_hash:
            logger.info("_stored datasource_hash: {}".format(self._stored.grafana_datasources_hash))
            self._stored.grafana_datasources_hash = datasources_hash
            logger.info("_stored datasource_hash: {}".format(self._stored.grafana_datasources_hash))
            self._update_datasource_config(grafana_datasources)
            logger.info("Pushed new datasource configuration")

        self._restart_grafana()

    def _check_config(self):
        """Identify missing but required items in configuration
        :returns: list of missing configuration items (configuration keys)
        """
        logger.info('Checking Config')
        # config = self.model.config

        # This is a noop for now -- keeping for an example
        return []

    def _generate_datasource_config(self):
        if not self._stored.provider_ready:
            return ""
        datasources_dict = {"apiVersion": 1, "datasources": [], "deleteDatasources": []}

        for source_info in self.grafana_provider.sources():
            logger.info("SOURCE INFO")
            logger.info(source_info)
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

    def _generate_grafana_config(self):
        if self.has_db:
            return self._generate_database_config()
        else:
            return self._generate_init_database_config()

    def _update_datasource_config(self, config):
        container = self.unit.get_container(SERVICE)

        datasources_path = os.path.join(
            grafana_config.DATASOURCE_PATH, "datasources", "datasources.yaml"
        )
        logger.info("Pushing new datasources config to {}".format(container))
        logger.info(datasources_path)
        logger.info(config)
        container.push(datasources_path, config)

    def _update_grafana_config_ini(self, config):
        container = self.unit.get_container(SERVICE)

        logger.info("Pushing new config to {}".format(container))
        logger.info(grafana_config.CONFIG_PATH)
        logger.info(config)
        container.push(grafana_config.CONFIG_PATH, config)

    #####################################

    # HIGH AVAILABILITY

    #####################################

    @property
    def has_peer(self) -> bool:
        rel = self.model.get_relation('grafana')
        return len(rel.units) > 0 if rel is not None else False

    def _check_high_availability(self):
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
        # TODO: https://grafana.com/docs/grafana/latest/tutorials/ha_setup/
        #       According to these docs ^, as long as we have a DB, HA should
        #       work out of the box if we are OK with "Sticky Sessions"
        #       but having "Stateless Sessions" could require more config

        # if the config changed, set a new pod spec
        self._check_high_availability()

    def on_peer_departed(self, _):
        """Sets pod spec with new info."""
        # TODO: setting spec shouldn't do anything now,
        #       but if we ever need to change config based peer units,
        #       we will want to make sure pebble is reconfigured
        self._restart_grafana()

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
            logger.warning("event unit can't be None when setting db config.")
            return

        # save the necessary configuration of this database connection
        database_fields = {
            field: event.relation.data[event.unit].get(field)
            for field in grafana_config.REQUIRED_DATABASE_FIELDS
        }

        # if any required fields are missing, warn the user and return
        missing_fields = [
            field
            for field in grafana_config.REQUIRED_DATABASE_FIELDS
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
                field: value
                for field, value in database_fields.items()
                if value is not None
            }
        )

        logger.info("Configuring database settings ...")
        self._on_config_changed(event)

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
        self._on_config_changed(event)

    def _generate_init_database_config(self):
        config_ini = configparser.ConfigParser()

        data = StringIO()
        config_ini.write(data)
        data.seek(0)
        ret = data.read()
        data.close()
        return ret

    def _generate_database_config(self):
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

    def _restart_grafana(self):
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
            self.grafana_provider = GrafanaProvider(self, 'grafana-source',
                                                    'grafana', self.version)
            self.framework.observe(self.grafana_provider.on.grafana_sources_changed,
                                   self._on_grafana_source_changed)
            self.framework.observe(self.grafana_provider.on.grafana_sources_to_delete_changed,
                                   self._on_grafana_source_broken)
            self.grafana_provider.ready()

        # self._check_high_availability()
        self.unit.status = ActiveStatus()


    @property
    def version(self):
        """Grafana version."""
        grafana = Grafana("localhost", str(self.model.config['port']))
        info = self.grafana.build_info
        if info:
            return info.get('version', None)
        return None


if __name__ == '__main__':
    main(GrafanaCharm)
