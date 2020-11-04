#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import hashlib
import textwrap

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
    'private-address',  # the hostname/IP of the data source server
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

# There are three app states w.r.t. HA
# 1) Blocked status if we have peers and no DB
# 2) HA available status if we have peers and DB
# 3) Running in non-HA mode
HA_NOT_READY_STATUS = BlockedStatus('Need database relation for HA.')
HA_READY_STATUS = MaintenanceStatus('Grafana ready for HA.')
SINGLE_NODE_STATUS = MaintenanceStatus('Grafana ready on single node.')


def get_container(pod_spec, container_name):
    """Find and return the first container in pod_spec whose name is
    container_name, otherwise return None."""
    for container in pod_spec['containers']:
        if container['name'] == container_name:
            return container
    raise ValueError("Unable to find container named '{}' in pod spec".format(
        container_name))


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

        # -- get image information
        self.image = OCIImageResource(self, 'grafana-image')

        # -- standard hooks
        self.framework.observe(self.on.config_changed, self.on_config_changed)
        self.framework.observe(self.on.update_status, self.on_update_status)
        self.framework.observe(self.on.stop, self._on_stop)

        # -- grafana-source relation observations
        self.framework.observe(self.on['grafana-source'].relation_changed,
                               self.on_grafana_source_changed)
        self.framework.observe(self.on['grafana-source'].relation_broken,
                               self.on_grafana_source_broken)

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

        # -- initialize states --
        self.datastore.set_default(sources=dict())  # available data sources
        self.datastore.set_default(source_names=set())  # unique source names
        self.datastore.set_default(sources_to_delete=set())
        self.datastore.set_default(database=dict())  # db configuration

    @property
    def has_peer(self) -> bool:
        rel = self.model.get_relation('grafana')
        return len(rel.units) > 0 if rel is not None else False

    @property
    def has_db(self) -> bool:
        """Only consider a DB connection if we have config info."""
        return len(self.datastore.database) > 0

    def _on_stop(self, _):
        """Go into maintenance state if the unit is stopped."""
        self.unit.status = MaintenanceStatus('Pod is terminating.')

    def on_config_changed(self, _):
        self.configure_pod()

    def on_update_status(self, _):
        """Various health checks of the charm."""
        self._check_high_availability()

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
            log.warning("No human readable name provided for 'grafana-source' "
                        "relation. Defaulting to unit name.")

        # check if this name already exists in the current datasources
        # TODO: do we want to handle this or just throw an error?
        #       we don't want to just block this unit, but I wonder if
        #       an error will be handled properly
        if datasource_fields['source-name'] in self.datastore.source_names:
            log.error('name already taken by existing grafana-source')
            return
        else:
            self.datastore.source_names.add(datasource_fields['source-name'])

        # set the first grafana-source as the default (needed for pod config)
        # if `self.datastore.sources` is currently empty, this is the first
        # TODO: confirm that this is what we want
        if not dict(self.datastore.sources):
            datasource_fields['isDefault'] = 'true'
        else:
            datasource_fields['isDefault'] = 'false'

        # add unit name so the source can be removed might be a
        # duplicate of 'source-name', but this will guarantee lookup
        datasource_fields['unit_name'] = event.unit.name

        # add the new datasource relation data to the current state
        new_source_data = {
            field: value for field, value in datasource_fields.items()
            if value is not None
        }
        self.datastore.sources.update({event.relation.id: new_source_data})
        self.configure_pod()

    def on_grafana_source_broken(self, event):
        """When a grafana-source is removed, delete from the datastore."""
        if self.unit.is_leader():
            self._remove_source_from_datastore(event.relation.id)
        self.configure_pod()

    def on_peer_changed(self, _):
        # TODO: https://grafana.com/docs/grafana/latest/tutorials/ha_setup/
        #       According to these docs ^, as long as we have a DB, HA should
        #       work out of the box if we are OK with "Sticky Sessions"
        #       but having "Stateless Sessions" will require more config

        # if the config changed, set a new pod spec
        self.configure_pod()

    def on_peer_departed(self, _):
        """Sets pod spec with new info."""
        # TODO: setting pod spec shouldn't do much now,
        #       but if we ever need to change config based peer units,
        #       we will want to make sure configure_pod() is called
        self.configure_pod()

    def on_database_changed(self, event):
        """Sets configuration information for database connection."""
        if not self.unit.is_leader():
            log.debug('unit is not leader. '
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

        # check if the passed database type is not in VALID_DATABASE_TYPES
        if database_fields['type'] not in VALID_DATABASE_TYPES:
            log.error('Grafana can only accept databases of the following '
                      'types: {}'.format(VALID_DATABASE_TYPES))
            return

        # add the new database relation data to the datastore
        self.datastore.database.update({
            field: value for field, value in database_fields.items()
            if value is not None
        })
        self.configure_pod()

    def on_database_broken(self, _):
        """Removes database connection info from datastore.

        We are guaranteed to only have one DB connection, so clearing
        datastore.database is all we need for the change to be propagated
        to the pod spec."""
        if not self.unit.is_leader():
            log.debug('unit is not leader. '
                      'Skipping on_database_departed() handler')
            return

        # remove the existing database info from datastore
        self.datastore.database = dict()

        # set pod spec because datastore config has changed
        self.configure_pod()

    def _remove_source_from_datastore(self, rel_id):
        """Remove the grafana-source from the datastore.

        Once removed from the datastore, this datasource will not
        part of the next pod spec."""
        log.info('Removing all data for relation: {}'.format(rel_id))
        removed_source = self.datastore.sources.pop(rel_id, None)
        if removed_source is None:
            log.warning('Could not remove source for relation: {}'.format(
                rel_id))
        else:
            # free name from charm's set of source names
            # and save to set which will be used in set_pod_spec
            self.datastore.source_names.remove(removed_source['source-name'])
            self.datastore.sources_to_delete.add(removed_source['source-name'])

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

        self.unit.status = status
        return status

    def _make_delete_datasources_config_text(self) -> str:
        """Generate text of data sources to delete."""
        if not self.datastore.sources_to_delete:
            return "\n"

        delete_datasources_text = textwrap.dedent("""
        deleteDatasources:""")
        for name in self.datastore.sources_to_delete:
            delete_datasources_text += textwrap.dedent("""
            - name: {}
              orgId: 1""".format(name))

        # clear datastore.sources_to_delete and return text result
        self.datastore.sources_to_delete.clear()
        return delete_datasources_text + '\n\n'

    def _make_data_source_config_text(self) -> str:
        """Build config based on Data Sources section of provisioning docs."""
        # get starting text for the config file and sources to delete
        delete_text = self._make_delete_datasources_config_text()
        config_text = textwrap.dedent("""
        apiVersion: 1
        """)
        config_text += delete_text
        if self.datastore.sources:
            config_text += "datasources:"
        for rel_id, source_info in self.datastore.sources.items():
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

    def _update_pod_data_source_config_file(self, pod_spec):
        """Adds datasources to pod configuration."""
        file_text = self._make_data_source_config_text()
        data_source_file_meta = {
            'name': 'grafana-datasources',
            'mountPath': '/etc/grafana/provisioning/datasources',
            'files': [{
                'path': 'datasources.yaml',
                'content': file_text,
            }]
        }
        container = get_container(pod_spec, self.app.name)
        container['volumeConfig'].append(data_source_file_meta)

        # get hash string of the new file text and put into container config
        # if this changes, it will trigger a pod restart
        file_text_hash = hashlib.md5(file_text.encode()).hexdigest()
        if 'DATASOURCES_YAML' in container['envConfig'] \
                and container['envConfig']['DATASOURCES_YAML'] != file_text_hash:
            log.info('datasources.yaml hash has changed. '
                     'Triggering pod restart.')
        container['envConfig']['DATASOURCES_YAML'] = file_text_hash

    def _make_config_ini_text(self):
        """Create the text of the config.ini file.

        More information about this can be found in the Grafana docs:
        https://grafana.com/docs/grafana/latest/administration/configuration/
        """

        config_text = textwrap.dedent("""
        [paths]
        provisioning = {0}

        [log]
        mode = {1}
        level = {2}
        """.format(
            self.model.config['provisioning_path'],
            self.model.config['grafana_log_mode'],
            self.model.config['grafana_log_level'],
        ))

        # if there is a database available, add that information
        if self.datastore.database:
            db_config = self.datastore.database
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

    def _update_pod_config_ini_file(self, pod_spec):
        file_text = self._make_config_ini_text()
        config_ini_file_meta = {
            'name': 'grafana-config-ini',
            'mountPath': '/etc/grafana',
            'files': [{
                'path': 'grafana.ini',
                'content': file_text
            }]
        }
        container = get_container(pod_spec, self.app.name)
        container['volumeConfig'].append(config_ini_file_meta)

        # get hash string of the new file text and put into container config
        # if this changes, it will trigger a pod restart
        file_text_hash = hashlib.md5(file_text.encode()).hexdigest()
        if 'GRAFANA_INI' in container['envConfig'] \
                and container['envConfig']['GRAFANA_INI'] != file_text_hash:
            log.info('grafana.ini hash has changed. Triggering pod restart.')
        container['envConfig']['GRAFANA_INI'] = file_text_hash

    def _build_pod_spec(self):
        """Builds the pod spec based on available info in datastore`."""

        config = self.model.config

        # get image details using OCI image helper library
        try:
            image_info = self.image.fetch()
        except OCIImageResourceError:
            logging.exception('An error occurred while fetching the image info')
            self.unit.status = BlockedStatus('Error fetching image information')
            return {}

        spec = {
            'version': 3,
            'containers': [{
                'name': self.app.name,
                'imageDetails': image_info,
                'ports': [{
                    'containerPort': config['port'],
                    'protocol': 'TCP'
                }],
                'volumeConfig': [],
                'envConfig': {},  # used to store hashes of config file text
                'kubernetes': {
                    'readinessProbe': {
                        'httpGet': {
                            'path': '/api/health',
                            'port': config['port']
                        },
                        'initialDelaySeconds': 10,
                        'timeoutSeconds': 30
                    },
                },
            }]
        }

        return spec

    def configure_pod(self):
        """Set Juju / Kubernetes pod spec built from `_build_pod_spec()`."""

        # check for valid high availability (or single node) configuration
        self._check_high_availability()

        # in the case where we have peers but no DB connection,
        # don't set the pod spec until it is resolved
        if self.unit.status == HA_NOT_READY_STATUS:
            log.error('Application is in a blocked state. '
                      'Please resolve before pod spec can be set.')
            return

        if not self.unit.is_leader():
            self.unit.status = ActiveStatus()
            return

        # general pod spec component updates
        self.unit.status = MaintenanceStatus('Building pod spec.')
        pod_spec = self._build_pod_spec()
        if not pod_spec:
            return
        self._update_pod_data_source_config_file(pod_spec)
        self._update_pod_config_ini_file(pod_spec)

        # set the pod spec with Juju
        self.model.pod.set_spec(pod_spec)
        self.unit.status = ActiveStatus()


if __name__ == '__main__':
    main(GrafanaK8s)
