#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO: set pod spec
# TODO: create actions that will help users. e.g. "upload-dashboard"
# TODO: does the database need to be an "Interface Object" or can this
#       charm be completely free of interfaces?
#       ** My current implementation does not have any interfaces
# TODO: refactor "defer" logic to follow jameinel's suggestion:
#       https://github.com/canonical/operator/issues/392#issuecomment-682096246
# TODO: get OCI image resource working with ops.lib since this import fails
#       on initial charm install hook

import logging
import textwrap

# import setuppath  # noqa:F401
from oci_image import OCIImageResource, OCIImageResourceError
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

        # get container image
        self.grafana_image = OCIImageResource(self, 'grafana-image')

        # -- standard hooks
        self.framework.observe(self.on.config_changed, self.on_config_changed)

        # -- grafana-source relation observations
        self.framework.observe(self.on['grafana-source'].relation_changed,
                               self.on_grafana_source_changed)
        self.framework.observe(self.on['grafana-source'].relation_departed,
                               self.on_grafana_source_departed)

        # -- grafana (peer) relation observations
        self.framework.observe(self.on['grafana'].relation_joined,
                               self.on_peer_joined)

        # -- database relation observations
        self.framework.observe(self.on['database'].relation_joined,
                               self.on_database_joined)
        self.framework.observe(self.on['database'].relation_changed,
                               self.on_database_changed)
        self.framework.observe(self.on['database'].relation_departed,
                               self.on_database_departed)

        # -- initialize states --
        self.datastore.set_default(sources=dict())  # available data sources
        self.datastore.set_default(database=dict())  # db configuration

    @property
    def has_peer(self) -> bool:
        return len(self.model.relations['grafana']) > 0

    @property
    def has_db(self) -> bool:
        return len(self.model.relations['database']) > 0

    def on_config_changed(self, event):
        """Sets the pod spec if any configuration has changed."""
        log.debug('on_config_changed() -- setting pod spec')
        if not self.unit.is_leader():
            log.debug("{} is not leader. Cannot set pod spec.".format(
                self.unit.name
            ))
            return
        self._set_pod_spec()

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
            log.debug(f"{self.unit.name} is not leader. Cannot set app data.")
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

        # TODO: test this unit's status
        self.unit.status = \
            MaintenanceStatus('Grafana ready for configuration')

        # TODO: real configuration -- set_pod_spec

    def on_grafana_source_departed(self, event):
        """When a grafana-source is removed, delete from the datastore."""
        if self.unit.is_leader():
            self._remove_source_from_datastore(event.relation.id)

    def on_peer_joined(self, event):
        """Checks if HA is possible and sets model status to reflect this.

        This event handler's primary goal is to ensure Grafana HA
        is possible since it needs a proper database connection.
        (e.g. MySQL or Postgresql)
        """
        if not self.unit.is_leader():
            log.debug('{} is not leader. '.format(self.unit.name) +
                      'Skipping on_peer_joined() handler')
            return

        # checking self.has_peer in case this is a deferred
        # event and the original peer has been departed
        if not self.has_peer:
            self.unit.status = \
                MaintenanceStatus('Grafana ready for configuration')
            return

        # if there is a new peer relation but no database
        # relation, we need to enter a blocked state.
        if not self.has_db:
            log.warning('No database relation provided to Grafana cluster. '
                        'Please add database (e.g. MySQL) before proceeding.')
            self.unit.status = \
                BlockedStatus('Need database relation for HA Grafana.')

            # Keep deferring this event until a database relation has joined
            # To unit test this, we may need to manually emit from the harness
            event.defer()
            return

        # let Juju operators know that HA is now possible
        self.unit.status = MaintenanceStatus('HA ready for configuration')

    def on_peer_config_changed(self, event):
        """Configure update configuration if necessary."""
        # TODO: https://grafana.com/docs/grafana/latest/tutorials/ha_setup/
        #       According to these docs ^, as long as we have a DB, HA should
        #       work out of the box if we are OK with "Sticky Sessions"
        #       but having "Stateless Sessions" will require more work

    def on_peer_config_departed(self, event):
        """A database relation is no longer required."""
        # TODO

    def on_database_joined(self, event):
        # TODO: do we need to make sure DB schema matches what Grafana needs?
        pass

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

        # add the new database relation data to the datastore
        self.datastore.database.update({
            field: value for field, value in database_fields.items()
            if value is not None
        })

        # TODO: set pod spec

    def on_database_departed(self, event):
        """Removes database connection info from datastore."""
        print('IN DATABASE DEPARTED')
        if not self.unit.is_leader():
            log.debug('{} is not leader. '.format(self.unit.name) +
                      'Skipping on_database_departed() handler')
            return

        # remove the existing database info from datastore
        self.datastore.database = dict()

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

    def _build_pod_spec(self):
        """Builds the pod spec based on available info in datastore`."""

        try:
            image_details = self.grafana_image.fetch()
        except OCIImageResourceError as e:
            self.unit.status = e.status
            return

        # this will set the baseline spec of the pod without
        # worrying about `grafana-source` or `database` relations
        spec = {
            'containers': [{
                'name': self.model.app.name,
                'imageDetails': {
                    'imagePath': 'grafana/grafana:latest'
                },
                'ports': [{
                    'containerPort': self.model.config['advertised_port'],
                    'protocol': 'TCP'
                }],
                'readinessProbe': {
                    'httpGet': {
                        'path': '/api/health',
                        'port': self.model.config['advertised_port']
                    },
                    # TODO: should these be in the config
                    'initialDelaySeconds': 10,
                    'timeoutSeconds': 30
                }
            }]
        }

        return spec

    def _set_pod_spec(self):
        """Set Juju / Kubernetes pod spec built from `_build_pod_spec()`."""
        self.unit.status = MaintenanceStatus('Setting pod spec.')
        self.model.pod.set_spec(self._build_pod_spec())
        self.unit.status = ActiveStatus('Pod ready.')


if __name__ == '__main__':
    main(GrafanaK8s)
