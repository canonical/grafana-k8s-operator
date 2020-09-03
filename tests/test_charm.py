import importlib
import pathlib
import shutil
import sys
import tempfile
import textwrap
import unittest

from ops.testing import Harness
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
    BlockedStatus,
    TooManyRelatedAppsError
)
from charm import (
    GrafanaK8s,
    APPLICATION_ACTIVE_STATUS,
    HA_NOT_READY_STATUS,
    HA_READY_STATUS,
    SINGLE_NODE_STATUS,
    get_container,
)

# TODO: should these tests be written in a way that doesn't require
#       the harness to be built each time?

BASE_CONFIG = {
    'advertised_port': 3000,
    'grafana_image_path': 'grafana/grafana:latest',
    'grafana_image_username': '',
    'grafana_image_password': '',
    'datasource_mount_path': '/etc/grafana/provisioning/datasources',
    'config_ini_mount_path': '/etc/grafana'
}

MISSING_IMAGE_PASSWORD_CONFIG = {
    'advertised_port': 3000,
    'grafana_image_path': 'grafana/grafana:latest',
    'grafana_image_username': 'test-user',
    'grafana_image_password': '',
}

MISSING_IMAGE_CONFIG = {
    'advertised_port': 3000,
    'grafana_image_path': '',
    'grafana_image_username': '',
    'grafana_image_password': '',
}


class GrafanaCharmTest(unittest.TestCase):

    def test__grafana_source_data(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        harness.update_config(BASE_CONFIG)
        self.assertEqual(harness.charm.datastore.sources, {})

        rel_id = harness.add_relation('grafana-source', 'prometheus')
        harness.add_relation_unit(rel_id, 'prometheus/0')
        self.assertIsInstance(rel_id, int)
        rel = harness.charm.model.get_relation('grafana-source')

        # test that the unit data propagates the correct way
        # which is through the triggering of on_relation_changed
        harness.update_relation_data(rel_id,
                                     'prometheus/0',
                                     {
                                         'host': '192.0.2.1',
                                         'port': 1234,
                                         'source-type': 'prometheus',
                                         'source-name': 'prometheus-app',
                                     })

        expected_first_source_data = {
                'host': '192.0.2.1',
                'port': 1234,
                'source-name': 'prometheus-app',
                'source-type': 'prometheus',
                'isDefault': 'true',
                'unit_name': 'prometheus/0'
        }
        self.assertEqual(expected_first_source_data,
                         dict(harness.charm.datastore.sources[rel_id]))

        # test that clearing the relation data leads to
        # the datastore for this data source being cleared
        harness.update_relation_data(rel_id,
                                     'prometheus/0',
                                     {
                                         'host': None,
                                         'port': None,
                                     })
        self.assertEqual(None, harness.charm.datastore.sources.get(rel_id))

    def test__ha_database_and_status_check(self):
        """If there is a peer connection and no database (needed for HA),
        the charm should put the application in a blocked state."""

        # TODO: this is becoming quite a long test -- possibly break it up

        # start charm with one peer and no database relation
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        harness.update_config(BASE_CONFIG)
        self.assertEqual(harness.charm.unit.status,
                         APPLICATION_ACTIVE_STATUS)

        # ensure _check_high_availability() ends up with the correct status
        status = harness.charm._check_high_availability()
        self.assertEqual(status, SINGLE_NODE_STATUS)

        # make sure that triggering 'update-status' hook does not
        # overwrite the current active status
        harness.charm.on.update_status.emit()
        self.assertEqual(harness.charm.unit.status,
                         APPLICATION_ACTIVE_STATUS)

        peer_rel_id = harness.add_relation('grafana', 'grafana')

        # add main unit and its data
        # harness.add_relation_unit(peer_rel_id, 'grafana/0')
        # will trigger the grafana-changed hook
        harness.update_relation_data(peer_rel_id,
                                     'grafana/0',
                                     {'private-address': '10.1.2.3'})

        # add peer unit and its data
        harness.add_relation_unit(peer_rel_id, 'grafana/1')
        harness.update_relation_data(peer_rel_id,
                                     'grafana/1',
                                     {'private-address': '10.0.0.1'})

        self.assertTrue(harness.charm.has_peer)
        self.assertFalse(harness.charm.has_db)
        self.assertEqual(harness.charm.unit.status, HA_NOT_READY_STATUS)
        self.assertEqual(harness.charm.app.status, HA_NOT_READY_STATUS)

        # ensure update-status hook doesn't overwrite this
        harness.charm.on.update_status.emit()
        self.assertEqual(harness.charm.unit.status,
                         HA_NOT_READY_STATUS)

        # now add the database connection and the model should
        # not have a blocked status
        db_rel_id = harness.add_relation('database', 'mysql')
        harness.add_relation_unit(db_rel_id, 'mysql/0')
        harness.update_relation_data(db_rel_id,
                                     'mysql/0',
                                     {
                                         'type': 'mysql',
                                         'host': '10.10.10.10:3306',
                                         'name': 'test_mysql_db',
                                         'user': 'test-admin',
                                         'password': 'super!secret!password',
                                     })
        self.assertTrue(harness.charm.has_db)
        self.assertEqual(harness.charm.app.status, APPLICATION_ACTIVE_STATUS)
        self.assertEqual(harness.charm.unit.status, APPLICATION_ACTIVE_STATUS)

        # ensure _check_high_availability() ends up with the correct status
        status = harness.charm._check_high_availability()
        self.assertEqual(status, HA_READY_STATUS)

    def test__database_relation_data(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        harness.update_config(BASE_CONFIG)
        self.assertEqual(harness.charm.datastore.database, {})

        # add relation and update relation data
        rel_id = harness.add_relation('database', 'mysql')
        rel = harness.charm.model.get_relation('database')
        harness.add_relation_unit(rel_id, 'mysql/0')
        test_relation_data = {
             'type': 'mysql',
             'host': '0.1.2.3:3306',
             'name': 'my-test-db',
             'user': 'test-user',
             'password': 'super!secret!password',
        }
        harness.update_relation_data(rel_id,
                                     'mysql/0',
                                     test_relation_data)
        # check that charm datastore was properly set
        self.assertEqual(dict(harness.charm.datastore.database),
                         test_relation_data)

        # now depart this relation and ensure the datastore is emptied
        harness.charm.on.database_relation_departed.emit(rel)
        self.assertEqual({}, dict(harness.charm.datastore.database))

    def test__multiple_database_relation_handling(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        harness.update_config(BASE_CONFIG)
        self.assertEqual(harness.charm.datastore.database, {})

        # add first database relation
        harness.add_relation('database', 'mysql')

        # add second database relation -- should fail here
        with self.assertRaises(TooManyRelatedAppsError):
            harness.add_relation('database', 'mysql')
            harness.charm.model.get_relation('database')

    def test__multiple_source_relations(self):
        """This will test data-source config text with multiple sources.

        Specifically, it will test multiple grafana-source relations."""
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        harness.update_config(BASE_CONFIG)
        self.assertEqual(harness.charm.datastore.sources, {})

        # add first relation
        rel_id0 = harness.add_relation('grafana-source', 'prometheus')
        harness.add_relation_unit(rel_id0, 'prometheus/0')

        # add test data to grafana-source relation
        # and test that _make_data_source_config_text() works as expected
        prom_source_data = {
            'host': '192.0.2.1',
            'port': 4321,
            'source-type': 'prometheus'
        }
        harness.update_relation_data(rel_id0, 'prometheus/0', prom_source_data)
        header_text = textwrap.dedent("""
                apiVersion: 1

                datasources:""")
        correct_config_text0 = header_text + textwrap.dedent("""
            - name: prometheus/0
              type: prometheus
              access: proxy
              url: http://192.0.2.1:4321
              isDefault: true
              editable: false""")
        generated_text = harness.charm._make_data_source_config_text()
        self.assertEqual(correct_config_text0, generated_text)

        # add another source relation and check the resulting config text
        jaeger_source_data = {
            'host': '255.255.255.0',
            'port': 7890,
            'source-type': 'jaeger',
            'source-name': 'jaeger-application'
        }
        rel_id1 = harness.add_relation('grafana-source', 'jaeger')
        rel = harness.model.get_relation('grafana-source', rel_id1)
        harness.add_relation_unit(rel_id1, 'jaeger/0')
        harness.update_relation_data(rel_id1, 'jaeger/0', jaeger_source_data)

        correct_config_text1 = correct_config_text0 + textwrap.dedent("""
            - name: jaeger-application
              type: jaeger
              access: proxy
              url: http://255.255.255.0:7890
              isDefault: false
              editable: false""")
        generated_text = harness.charm._make_data_source_config_text()
        self.assertEqual(correct_config_text1, generated_text)

        # test removal of second source results in config_text
        # that is the same as the original
        harness.charm.on.grafana_source_relation_departed.emit(rel)
        generated_text = harness.charm._make_data_source_config_text()
        self.assertEqual(correct_config_text0, generated_text)

    def test__check_config_missing_image_path(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.update_config(MISSING_IMAGE_PASSWORD_CONFIG)

        # test the return value of _check_config
        missing = harness.charm._check_config()
        expected = ['grafana_image_password']
        self.assertEqual(missing, expected)

    def test__check_config_missing_password(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.update_config(MISSING_IMAGE_CONFIG)

        # test the return value of _check_config
        missing = harness.charm._check_config()
        expected = ['grafana_image_path']
        self.assertEqual(missing, expected)

    def test__pod_spec_container_datasources(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        harness.update_config(BASE_CONFIG)
        self.assertEqual(harness.charm.datastore.sources, {})

        # add first relation
        rel_id = harness.add_relation('grafana-source', 'prometheus')
        harness.add_relation_unit(rel_id, 'prometheus/0')

        # add test data to grafana-source relation
        # and test that _make_data_source_config_text() works as expected
        prom_source_data = {
            'host': '192.0.2.1',
            'port': 4321,
            'source-type': 'prometheus'
        }
        harness.update_relation_data(rel_id, 'prometheus/0', prom_source_data)

        data_source_file_text = textwrap.dedent("""
            apiVersion: 1

            datasources:
            - name: prometheus/0
              type: prometheus
              access: proxy
              url: http://192.0.2.1:4321
              isDefault: true
              editable: false""")

        config_ini_file_text = textwrap.dedent("""
        [paths]
        data = /var/lib/grafana
        """)

        expected_container_files_spec = [
            {
                'name': 'grafana-data-sources',
                'mountPath': harness.model.config['datasource_mount_path'],
                'files': {
                    'datasources.yaml': data_source_file_text,
                },
            },
            {
                'name': 'grafana-config-ini',
                'mountPath': harness.model.config['config_ini_mount_path'],
                'files': {
                    'config.ini': config_ini_file_text
                }
            }
        ]
        pod_spec = harness.get_pod_spec()[0]
        container = get_container(pod_spec, 'grafana')
        actual_container_files_spec = container['files']
        self.assertEqual(expected_container_files_spec,
                         actual_container_files_spec)

    def test__access_sqlite_storage_location(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        expected_path = '/var/lib/grafana'
        actual_path = harness.charm.meta.storages['sqlitedb'].location
        self.assertEqual(expected_path, actual_path)

    def test__config_ini_without_database(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        expected_config_text = textwrap.dedent("""
        [paths]
        data = /var/lib/grafana
        """)

        actual_config_text = harness.charm._make_config_ini_text()
        self.assertEqual(expected_config_text, actual_config_text)

    def test__config_ini_with_database(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        harness.update_config(BASE_CONFIG)

        # add database relation and update relation data
        rel_id = harness.add_relation('database', 'mysql')
        # rel = harness.charm.model.get_relation('database')
        harness.add_relation_unit(rel_id, 'mysql/0')
        test_relation_data = {
            'type': 'mysql',
            'host': '0.1.2.3:3306',
            'name': 'my-test-db',
            'user': 'test-user',
            'password': 'super!secret!password',
        }
        harness.update_relation_data(rel_id,
                                     'mysql/0',
                                     test_relation_data)

        # test the results of _make_config_ini_text()
        expected_config_text = textwrap.dedent("""
        [paths]
        data = /var/lib/grafana
        
        [database]
        type = mysql
        host = 0.1.2.3:3306
        name = my-test-db
        user = test-user
        password = super!secret!password
        url = mysql://test-user:super!secret!password@0.1.2.3:3306/my-test-db""")

        actual_config_text = harness.charm._make_config_ini_text()
        self.assertEqual(expected_config_text, actual_config_text)
