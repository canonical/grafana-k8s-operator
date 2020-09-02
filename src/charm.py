#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO: refactor _set_pod_spec to call smaller "pod update" functions for
#       various things -- e.g. configure database or datasource
# TODO: add config.ini to set_pod_spec and ensure the persistent storage
#       matches what is defined in metadata.yaml
# TODO: CONFIRM: 'update-status' hook only sets a maintenance mode and
#       _set_pod_spec() is the only thing that will set the application
#       or unit into an active state
# TODO: create actions that will help users. e.g. "upload-dashboard"

import logging
import textwrap

# from oci_image import OCIImageResource, OCIImageResourceError
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus, BlockedStatus

log = logging.getLogger()


# These are the required and optional relation data fields
# In other words, when relating to this charm, these are the fields
# that will be processed by this charm.
# TODO: had these defined as sets for faster lookup than lists,
#       but if I'm iterating over them more often, maybe they should be lists
REQUIRED_DATASOURCE_FIELDS = {
    'host',  # the hostname/IP of the data source server
    'port',  # the port of the data source server
    'source-type',  # the data source type (e.g. prometheus)
}

OPTIONAL_DATASOURCE_FIELDS = {
    'source-name',  # a human-readable name of the source
}

# https://grafana.com/docs/grafana/latest/administration/configuration/#database
REQUIRED_DATABASE_FIELDS = {
    'type',  # mysql, postgres or sqlite3 (sqlite3 doesn't work for HA)
    'host',  # in the form '<url_or_ip>:<port>', e.g. 127.0.0.1:3306
    'name',
    'user',
    'password',
}

# verify with Grafana documentation to ensure fields have valid values
# as this charm will not directly handle these cases
# TODO: fill up with optional fields - leaving blank for now
OPTIONAL_DATABASE_FIELDS = set()

VALID_DATABASE_TYPES = {'mysql', 'postgres', 'sqlite3'}

# statuses
APPLICATION_ACTIVE_STATUS = ActiveStatus('Grafana pod ready.')

# There are three app states w.r.t. HA
# 1) Blocked status if we have peers and no DB
# 2) HA available status if we have peers and DB
# 3) Running in non-HA mode
HA_NOT_READY_STATUS = \
    BlockedStatus('Need database relation for HA.')
HA_READY_STATUS = \
    MaintenanceStatus('Grafana ready for HA.')
SINGLE_NODE_STATUS = \
    MaintenanceStatus('Grafana ready on single node.')


class GrafanaK8s(CharmBase):
    """Charm to run Grafana on Kubernetes.

    This charm allows for high-availability
    (as long as a non-sqlite database relation is present).

    Developers of this charm should be aware of the Grafana provisioning docs:
    https://grafana.com/docs/grafana/latest/administration/provisioning/
    """

    datastore = StoredState()

    def __init__(self, *args):
        log.debug('Initializing charm.')
        super().__init__(*args)

        # -- standard hooks
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        self.framework.observe(self.on.update_status, self.on_update_status)

        # -- grafana-source relation observations
        self.framework.observe(self.on['grafana-source'].relation_changed,
                               self.on_grafana_source_changed)
        self.framework.observe(self.on['grafana-source'].relation_departed,
                               self.on_grafana_source_departed)

        # -- grafana (peer) relation observations
        self.framework.observe(self.on['grafana'].relation_changed,
                               self.on_peer_changed)
        # self.framework.observe(self.on['grafana'].relation_departed,
        #                        self.on_peer_departed)

        # -- database relation observations
        self.framework.observe(self.on['database'].relation_changed,
                               self.on_database_changed)
        self.framework.observe(self.on['database'].relation_departed,
                               self.on_database_departed)

        # -- initialize states --
        self.datastore.set_default(sources=dict())  # available data sources
        self.datastore.set_default(database=dict())  # db configuration

    @property
    def has_peer(self) -> bool:
        rel = self.model.get_relation('grafana')
        return len(rel.units) > 0 if rel is not None else False

    @property
    def has_db(self) -> bool:
        """Only consider a DB connection if we have config info."""
        return len(self.datastore.database) > 0

    def on_config_changed(self, event):
        self.configure_pod()

    def on_update_status(self, event):
        """Various health checks of the charm."""
        self._check_high_availability()
        # TODO: add more health checks in the future

    def on_start(self, event):
        # TODO:
        pass

    def on_grafana_source_changed(self, event):
        """ Get relation data for Grafana source and set k8s pod spec.

        This event handler (if the unit is the leader) will get data for
        an incoming grafana-source relation and make the relation data
        is available in the app's datastore object (StoredState).
        """

        # if this unit is the leader, set the required data
        # of the grafana-source in this charm's datastore
        if not self.unit.is_leader():
            log.debug("{} is not leader. Cannot set app data.".format(
                self.unit.name))
            return

        # if there is no available unit, remove data-source info if it exists
        if event.unit is None:
            self._remove_source_from_datastore(event.relation.id)
            log.warning("event unit can't be None when setting data sources.")
            return

        # dictionary of all the required/optional datasource field values
        # using this as a more generic way of getting data source fields
        datasource_fields = \
            {field: event.relation.data[event.unit].get(field) for field in
             REQUIRED_DATASOURCE_FIELDS | OPTIONAL_DATASOURCE_FIELDS}

        missing_fields = [field for field
                          in REQUIRED_DATASOURCE_FIELDS
                          if datasource_fields.get(field) is None]
        # check the relation data for missing required fields
        if len(missing_fields) > 0:
            log.error("Missing required data fields for grafana-source "
                      "relation: {}".format(missing_fields))
            self._remove_source_from_datastore(event.relation.id)
            return

        # specifically handle optional fields if necessary
        if datasource_fields['source-name'] is None:
            datasource_fields['source-name'] = event.unit.name
            log.warning("No human readable name provided for 'grafana-source'"
                        "relation. Defaulting to unit name.")

        # set the first grafana-source as the default (needed for pod config)
        # if `self.datastore.sources` is currently emtpy, this is the first
        # TODO: confirm that this is what we want
        if not dict(self.datastore.sources):
            datasource_fields['isDefault'] = 'true'
        else:
            datasource_fields['isDefault'] = 'false'

        # add the new datasource relation data to the current state
        self.datastore.sources.update({event.relation.id: {
            field: value for field, value in datasource_fields.items()
            if value is not None
        }})

        self.configure_pod()

    def on_grafana_source_departed(self, event):
        """When a grafana-source is removed, delete from the datastore."""
        if self.unit.is_leader():
            self._remove_source_from_datastore(event.relation.id)
        self.configure_pod()

    def on_peer_changed(self, event):
        # TODO: https://grafana.com/docs/grafana/latest/tutorials/ha_setup/
        #       According to these docs ^, as long as we have a DB, HA should
        #       work out of the box if we are OK with "Sticky Sessions"
        #       but having "Stateless Sessions" will require more config

        # if the config changed, set a new pod spec
        self.configure_pod()

    def on_peer_departed(self, event):
        """Sets pod spec with new info."""
        # TODO: setting pod spec shouldn't do much now,
        #       but if we ever need to change config based peer units,
        #       we will want to make sure configure_pod() is called
        self.configure_pod()

    def on_database_changed(self, event):
        """Sets configuration information for database connection."""
        if not self.unit.is_leader():
            log.debug('{} is not leader. '.format(self.unit.name) +
                      'Skipping on_database_changed() handler')
            return

        if event.unit is None:
            log.warning("event unit can't be None when setting db config.")
            return

        # save the necessary configuration of this database connection
        database_fields = \
            {field: event.relation.data[event.unit].get(field) for field in
             REQUIRED_DATABASE_FIELDS | OPTIONAL_DATABASE_FIELDS}

        # if any required fields are missing, warn the user and return
        missing_fields = [field for field
                          in REQUIRED_DATABASE_FIELDS
                          if database_fields.get(field) is None]
        if len(missing_fields) > 0:
            log.error("Missing required data fields for related database "
                      "relation: {}".format(missing_fields))
            return

        # check that the passed database type is not in VALID_DATABASE_TYPES
        if database_fields['type'] not in VALID_DATABASE_TYPES:
            log.error('Grafana can only accept databases of the following '
                      'types: {}'.format(VALID_DATABASE_TYPES))
            return

        # add the new database relation data to the datastore
        self.datastore.database.update({
            field: value for field, value in database_fields.items()
            if value is not None
        })

        # set pod spec with new database config data
        self.configure_pod()

    def on_database_departed(self, event):
        """Removes database connection info from datastore.

        Since we are guaranteed to only have one DB connection, clearing
        the datastore works. If we have multiple DB connections,
        we will datastore.database structure to look more like
        datastore.sources.
        """
        print('IN DATABASE DEPARTED')
        if not self.unit.is_leader():
            log.debug('{} is not leader. '.format(self.unit.name) +
                      'Skipping on_database_departed() handler')
            return

        # remove the existing database info from datastore
        self.datastore.database = dict()

        # set pod spec because datastore config has changed
        self.configure_pod()

    def _remove_source_from_datastore(self, rel_id):
        # TODO: based on provisioning docs, we may want to add
        #       'deleteDatasource' to Grafana configuration file
        data_source = self.datastore.sources.pop(rel_id, None)
        log.info('removing data source information from state. '
                 'host: {0}, port: {1}.'.format(
                     data_source['host'] if data_source else '',
                     data_source['port'] if data_source else '',
                 ))

    def _make_data_source_config_text(self):
        """Build docs based on "Data Sources section of provisioning docs."""
        # common starting config text
        config_text = textwrap.dedent("""
            apiVersion: 1
            
            datasources:""")
        for rel_id, source_info in self.datastore.sources.items():
            # TODO: handle more optional fields and verify that current
            #       defaults are what we want (e.g. "access")
            config_text += textwrap.dedent("""
                - name: {0}
                  type: {1}
                  access: proxy
                  url: http://{2}:{3}
                  isDefault: {4}
                  editable: false""").format(
                source_info['source-name'],
                source_info['source-type'],
                source_info['host'],
                source_info['port'],
                source_info['isDefault']
            )
        return config_text

    def _check_config(self):
        """Get list of missing charm settings."""
        config = self.model.config
        missing = []

        if config['grafana_image_username'] \
                and not config['grafana_image_password']:
            missing.append('grafana_image_password')

        # TODO: does it make sense to set state directly in this function?
        if missing:
            self.unit.status = \
                BlockedStatus('Missing configuration: {}'.format(missing))

        return missing

    def _build_pod_spec(self):
        """Builds the pod spec based on available info in datastore`."""

        # this will set the baseline spec of the pod without
        # worrying about `grafana-source` or `database` relations
        config = self.model.config

        # get image details
        image_details = {
            'imagePath': config['grafana_image_path']
        }
        if config['grafana_image_username']:
            image_details['username'] = config['grafana_image_username']
            image_details['password'] = config['grafana_image_password']

        spec = {
            'containers': [{
                'name': self.model.app.name,
                'imageDetails': image_details,
                'ports': [{
                    'containerPort': config['advertised_port'],
                    'protocol': 'TCP'
                }],
                'readinessProbe': {
                    'httpGet': {
                        'path': '/api/health',
                        'port': config['advertised_port']
                    },
                    # TODO: should these be in the config?
                    'initialDelaySeconds': 10,
                    'timeoutSeconds': 30
                }
            }]
        }

        return spec

    def configure_pod(self):
        """Set Juju / Kubernetes pod spec built from `_build_pod_spec()`."""

        # check for valid high availability (or single node) configuration
        self._check_high_availability()
        self._check_config()

        # decide whether we can set the pod spec or not
        # TODO: is this necessary?
        if isinstance(self.unit.status, BlockedStatus):
            log.error('Application is in a blocked state. '
                      'Please resolve before pod spec can be set.')
            return

        if not self.unit.is_leader():
            self.unit.status = ActiveStatus()
            return

        self.unit.status = MaintenanceStatus('Building pod spec.')
        self.model.pod.set_spec(self._build_pod_spec())
        self.app.status = APPLICATION_ACTIVE_STATUS
        self.unit.status = APPLICATION_ACTIVE_STATUS

    def _check_high_availability(self):
        """Checks whether the configuration allows for HA."""
        if self.has_peer:
            if self.has_db:
                log.info('high availability possible.')
                status = HA_READY_STATUS
            else:
                log.warning('high availability not possible '
                            'with current configuration.')
                status = HA_NOT_READY_STATUS
        else:
            log.info('running Grafana on single node.')
            status = SINGLE_NODE_STATUS

        # make sure we don't have a maintenance status overwrite
        # a currently active status
        # *note* HA_READY_STATUS and SINGLE_NODE_STATUS are
        # maintenance statuses
        if isinstance(status, MaintenanceStatus) \
                and isinstance(self.unit.status, ActiveStatus):
            return status

        # set status for *at least* the unit and possibly the app
        self.unit.status = status
        if self.unit.is_leader():
            self.app.status = status

        return status


if __name__ == '__main__':
    main(GrafanaK8s)
