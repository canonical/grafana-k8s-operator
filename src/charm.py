#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import hashlib
import textwrap
import yaml

import config
from oci_image import OCIImageResource, OCIImageResourceError
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus, BlockedStatus
from grafana_server import Grafana
from grafana_provider import MonitoringProvider

logger = logging.getLogger()


GRAFANA_CONFIG_INI = "/etc/grafana/grafana-config.ini"
GRAFANA_DATASOURCE_PATH = "/etc/grafana/provisioning/datasources/datasources.yaml"


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

        # -- initialize states --
        self._stored.set_default(sources=dict())  # available data sources
        self._stored.set_default(source_names=set())  # unique source names
        self._stored.set_default(sources_to_delete=set())
        self._stored.set_default(database=dict())  # db configuration
        self._stored.set_default(provider_ready=False)
        self._stored.set_default(grafana_config_hash=None)

        # -- get image information
        self.image = OCIImageResource(self, 'grafana-image')

        # -- standard hooks
        self.framework.observe(self.on.grafana_pebble_ready, self._setup_pebble_layers)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.update_status, self._on_update_status)
        self.framework.observe(self.on.stop, self._on_stop)

        # -- grafana (peer) relation observations
        self.framework.observe(self.on['grafana'].relation_changed,
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
            self.grafana_provider = MonitoringProvider(self,
                                                       'monitoring', 'grafana', self.version)
            self.framework.observe(self.grafana_provider.on.sources_changed,
                                   self._on_config_changed())

    @property
    def has_peer(self) -> bool:
        rel = self.model.get_relation('grafana')
        return len(rel.units) > 0 if rel is not None else False

    @property
    def has_db(self) -> bool:
        """Only consider a DB connection if we have config info."""
        return len(self._stored.database) > 0

    def _on_stop(self, _):
        """Go into maintenance state if the unit is stopped."""
        self.unit.status = MaintenanceStatus('Pod is terminating.')

    def _on_config_changed(self, event):
        logger.info("Handling config change")
        container = self.unit.get_container("grafana")

        missing_config = self._check_config()
        if missing_config:
            logger.error('Incomplete Configuration: {}. '
                         'Application will be blocked.'.format(missing_config))
            self.unit.status = \
                BlockedStatus('Missing configuration: {}'.format(missing_config))
            return

        grafana_config_ini, grafana_datasources = self._grafana_config()
        config_ini_hash = str(hashlib.md5(str(grafana_config_ini).encode('utf-8')))
        if not self._stored.grafana_config_ini_hash == config_ini_hash:
            self._stored.grafana_config_ini_hash = config_ini_hash

        datasources_hash = str(hashlib.md5(str(grafana_datasources).encode('utf-8')))
        if not self._stored.grafana_datasources_hash == datasources_hash:
            self._stored.grafana_datasources_hash = datasources_hash
            container.push(GRAFANA_DATASOURCE_PATH, grafana_datasources)
            logger.info("Pushed new configuation")

        layer = self._grafana_layer()
        plan = container.get_plan()
        if plan.services != layer["services"]:
            container.add_layer("grafana", layer, combine=True)

            if container.get_service("prometheus").is_running():
                container.stop("prometheus")

            container.start("prometheus")
            logger.info("Restarted prometheus container")

        self.app.status = ActiveStatus()
        self.unit.status = ActiveStatus()

    def _on_update_status(self, _):
        """Various health checks of the charm."""
        provided = {'grafana': self.version}
        if provided:
            logger.debug("Grafana provider is available")
            logger.debug("Providing : {}".format(provided))
            if not self._stored.provider_ready:
                self._stored.provider_ready = True
        self._check_high_availability()

    def on_grafana_source_changed(self, event):
        pass

    def on_grafana_source_broken(self, event):
        """When a grafana-source is removed, delete from the _stored."""
        pass

    def on_peer_changed(self, _):
        # TODO: https://grafana.com/docs/grafana/latest/tutorials/ha_setup/
        #       According to these docs ^, as long as we have a DB, HA should
        #       work out of the box if we are OK with "Sticky Sessions"
        #       but having "Stateless Sessions" could require more config

        # if the config changed, set a new pod spec
        self._check_high_availability()

    def on_peer_departed(self, _):
        """Sets pod spec with new info."""
        # TODO: setting pod spec shouldn't do anything now,
        #       but if we ever need to change config based peer units,
        #       we will want to make sure configure_pod() is called
        self.configure_pod()

    def on_database_changed(self, event):
        """Sets configuration information for database connection."""
        if not self.unit.is_leader():
            return

        if event.unit is None:
            logger.warning("event unit can't be None when setting db config.")
            return

        # save the necessary configuration of this database connection
        database_fields = \
            {field: event.relation.data[event.unit].get(field) for field in
             config.REQUIRED_DATABASE_FIELDS | config.OPTIONAL_DATABASE_FIELDS}

        # if any required fields are missing, warn the user and return
        missing_fields = [field for field
                          in config.REQUIRED_DATABASE_FIELDS
                          if database_fields.get(field) is None]
        if len(missing_fields) > 0:
            logger.error("Missing required data fields for related database "
                      "relation: {}".format(missing_fields))
            return

        # check if the passed database type is not in VALID_DATABASE_TYPES
        if database_fields['type'] not in VALID_DATABASE_TYPES:
            logger.error('Grafana can only accept databases of the following '
                      'types: {}'.format(VALID_DATABASE_TYPES))
            return

        # add the new database relation data to the _stored
        self._stored.database.update({
            field: value for field, value in database_fields.items()
            if value is not None
        })
        self.configure_pod()

    def on_database_broken(self, _):
        """Removes database connection info from _stored.

        We are guaranteed to only have one DB connection, so clearing
        _stored.database is all we need for the change to be propagated
        to the pod spec."""
        if not self.unit.is_leader():
            return

        # remove the existing database info from _stored
        self._stored.database = dict()

        # set pod spec because _stored config has changed
        self.configure_pod()

    def _remove_source_from_datastore(self, rel_id):
        """Remove the grafana-source from the _stored.

        Once removed from the _stored, this datasource will not
        part of the next pod spec."""
        logger.info('Removing all data for relation: {}'.format(rel_id))
        removed_source = self._stored.sources.pop(rel_id, None)
        if removed_source is None:
            logger.warning('Could not remove source for relation: {}'.format(
                rel_id))
        else:
            # free name from charm's set of source names
            # and save to set which will be used in set_pod_spec
            self._stored.source_names.remove(removed_source['source-name'])
            self._stored.sources_to_delete.add(removed_source['source-name'])

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

    def _make_delete_datasources_config_text(self) -> str:
        """Generate text of data sources to delete."""
        if not self._stored.sources_to_delete:
            return "\n"

        delete_datasources_text = textwrap.dedent("""
        deleteDatasources:""")
        for name in self._stored.sources_to_delete:
            delete_datasources_text += textwrap.dedent("""
            - name: {}
              orgId: 1""".format(name))

        # clear _stored.sources_to_delete and return text result
        self._stored.sources_to_delete.clear()
        return delete_datasources_text + '\n\n'

    def _make_data_source_config_text(self) -> str:
        """Build config based on Data Sources section of provisioning docs."""
        # get starting text for the config file and sources to delete
        delete_text = self._make_delete_datasources_config_text()
        config_text = textwrap.dedent("""
        apiVersion: 1
        """)
        config_text += delete_text
        if self._stored.sources:
            config_text += "datasources:"
        for rel_id, source_info in self._stored.sources.items():
            # TODO: handle more optional fields and verify that current
            #       defaults are what we want (e.g. "access")
            config_text += textwrap.dedent("""
                - name: {0}
                  type: {1}
                  access: proxy
                  url: http://{2}:{3}
                  isDefault: {4}
                  editable: true
                  orgId: 1""").format(
                source_info['source-name'],
                source_info['source-type'],
                source_info['private-address'],
                source_info['port'],
                source_info['isDefault'],
            )

        # check if there these are empty
        return config_text + '\n'

    def _grafana_config(self):
        return self._make_config_ini_text(), self._make_data_source_config_text()

    def _make_config_ini_text(self):
        """Create the text of the config.ini file.

        More information about this can be found in the Grafana docs:
        https://grafana.com/docs/grafana/latest/administration/configuration/
        """

        config_text = textwrap.dedent("""
        [paths]
        provisioning = /etc/grafana/provisioning

        [logger]
        mode = console
        level = {0}
        """.format(
            self.model.config['grafana_log_level'],
        ))

        # if there is a database available, add that information
        if self._stored.database:
            db_config = self._stored.database
            config_text += textwrap.dedent("""
            [database]
            type = {0}
            host = {1}
            name = {2}
            user = {3}
            password = {4}
            url = {0}://{3}:{4}@{1}/{2}""".format(
                db_config['type'],
                db_config['host'],
                db_config['name'],
                db_config['user'],
                db_config['password'],
            ))
        return config_text

    def _grafana_layer(self):
        """Construct the pebble layer`."""

        # config = self.model.config

        # get image details using OCI image helper library
        try:
            self.image.fetch()
        except OCIImageResourceError:
            logger.exception('An error occurred while fetching the image info')
            self.unit.status = BlockedStatus('Error fetching image information')
            return {}

        layer = {
            "summary": "Grafana layer",
            "description": "Pebble layer configuration for Grafana",
            "services": {
                "grafana": {
                    "override": "replace",
                    "summary": "grafana dashboard",
                    "command": self._command(),
                    "startup": "enabled"
                }
            }
        }

        return layer

    def _setup_pebble_layers(self, event):
        """Set Pebble layer built from `_grafana_layer()`."""

        # check for valid high availability (or single node) configuration
        self._check_high_availability()

        # in the case where we have peers but no DB connection,
        # don't set the pebble layer until it is resolved
        if self.unit.status == BlockedStatus('Need database relation for HA.'):
            logger.error('Application is in a blocked state. '
                      'Please resolve before pebble layer can be set.')
            return

        if not self.unit.is_leader():
            self.unit.status = ActiveStatus()
            return

        # general spec component updates
        self.unit.status = MaintenanceStatus('Setting up containers.')
        # container = event.workload

        layer_spec = self._grafana_layer()
        if not layer_spec:
            return
        self._update_layer_data_source_config_file(layer_spec)
        self._update_layer_config_ini_file(layer_spec)

        # set the pod spec with Juju
        self.model.pod.set_spec(layer_spec)
        self.unit.status = ActiveStatus()

    def _check_config(self):
        """Identify missing but required items in configuration
        :returns: list of missing configuration items (configuration keys)
        """
        logger.debug('Checking Config')
        # config = self.model.config

        # This is a noop for now -- keeping for an example
        return []

    @property
    def version(self):
        """Grafana version."""
        grafana = Grafana("localhost", str(self.model.config['port']))
        info = grafana.build_info()
        if info:
            return info.get('version', None)
        return None

    @property
    def provides(self):
        grafana = Grafana("localhost", str(self.model.config['port']))
        info = grafana.build_info()
        if info:
            provided = {
                'provides': {'grafana': info['version']}
            }
        else:
            provided = {}
        return provided


if __name__ == '__main__':
    main(GrafanaCharm)
