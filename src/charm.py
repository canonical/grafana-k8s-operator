#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO: CONFIRM: 'update-status' hook only sets a maintenance mode and
#       _set_pod_spec() is the only thing that will set the application
#       or unit into an active state
# TODO: to ensure HA works properly, add datasource version increments
#       https://grafana.com/docs/grafana/latest/administration/provisioning/#running-multiple-grafana-instances
# TODO: create actions that will help users. e.g. "upload-dashboard"
# TODO: handle the removal of datasources in coniguration and "on_source_changed"

import logging
import textwrap
import pprint

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
            self._remove_source_from_datastore(event.relation.id, event.unit.name)
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
            self._remove_source_from_datastore(event.relation.id, event.unit.name)
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

        # add unit name so the source can be removed might be a
        # duplicate of 'source-name', but this will guarantee lookup
        datasource_fields['unit_name'] = event.unit.name

        # add the new datasource relation data to the current state
        # make sure that we can handle multiple units of the same relation
        # as well as different relations altogether
        new_source_data = {
            field: value for field, value in datasource_fields.items()
            if value is not None
        }
        if event.relation.id in self.datastore.sources:
            self.datastore.sources[event.relation.id].append(new_source_data)
        else:
            self.datastore.sources[event.relation.id] = [new_source_data]

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

    def _remove_source_from_datastore(self, rel_id, unit_name=None):
        # TODO: based on provisioning docs, we will want to add
        #       'deleteDatasource' to Grafana configuration file

        # if there is no unit supplied,
        # remove data for all units of the relation
        if unit_name is None:
            log.warning('Removing all data for relation: {}'.format(rel_id))
            self.datastore.sources.pop(rel_id)
            return

        # search for the unit that needs to be deleted
        remove_index = None
        for i, source_info in enumerate(self.datastore.sources[rel_id]):
            if source_info['unit_name'] == unit_name:
                remove_index = i
                break
        if remove_index is None:
            log.error('Could not find unit to remove: {}'.format(unit_name))
            self.unit.status = BlockedStatus()
        else:
            log.info('Removing data source unit: {}'.format(unit_name))
            del self.datastore.sources[rel_id][remove_index]

            # if this deleted all data in the relation, remove the rel_id
            if not self.datastore.sources[rel_id]:
                self.datastore.sources.pop(rel_id)

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

    def _check_config(self):
        """Get list of missing charm settings."""
        config = self.model.config
        missing = []

        if not config['grafana_image_path']:
            missing.append('grafana_image_path')

        if config['grafana_image_username'] \
                and not config['grafana_image_password']:
            missing.append('grafana_image_password')

        # TODO: does it make sense to set state directly in this function?
        if missing:
            self.unit.status = \
                BlockedStatus('Missing configuration: {}'.format(missing))

        return missing

    def _make_data_source_config_text(self):
        """Build docs based on "Data Sources section of provisioning docs."""
        # common starting config text
        config_text = textwrap.dedent("""
            apiVersion: 1

            datasources:""")
        for rel_id, sources_list in self.datastore.sources.items():
            for source_info in sources_list:
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

    def _update_pod_data_source_config_file(self, pod_spec):
        """Adds datasources to pod configuration."""
        file_text = self._make_data_source_config_text()
        data_source_file_meta = {
            'name': 'grafana-data-sources',
            'mountPath': self.model.config['datasource_mount_path'],
            'files': {
                'datasources.yaml': file_text
            }
        }
        container = get_container(pod_spec, self.app.name)
        container['files'].append(data_source_file_meta)

    def _make_config_ini_text(self):
        """Create the text of the config.ini file.

        More information about this can be found in the Grafana docs:
        https://grafana.com/docs/grafana/latest/administration/configuration/
        """

        # set default data storage path so make sure sqlite3 db is always
        # available in single node mode
        config_text = textwrap.dedent("""
        [paths]
        data = {0}
        """.format(
            self.meta.storages['sqlitedb'].location,
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
            'mountPath': self.model.config['config_ini_mount_path'],
            'files': {
                'config.ini': file_text
            }
        }
        container = get_container(pod_spec, self.app.name)
        container['files'].append(config_ini_file_meta)

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
            'version': 3,
            'containers': [{
                'name': self.app.name,
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
                },
                'files': [],
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

        # general pod spec component updates
        self.unit.status = MaintenanceStatus('Building pod spec.')
        pod_spec = self._build_pod_spec()
        self._update_pod_data_source_config_file(pod_spec)
        self._update_pod_config_ini_file(pod_spec)

        # set the pod spec with Juju
        self.model.pod.set_spec(pod_spec)
        self.app.status = APPLICATION_ACTIVE_STATUS
        self.unit.status = APPLICATION_ACTIVE_STATUS


if __name__ == '__main__':
    main(GrafanaK8s)
