import hashlib
import textwrap
import unittest

from ops.testing import Harness
from ops.model import (
    TooManyRelatedAppsError,
    ActiveStatus,
)
from charm import (
    GrafanaK8s,
    HA_NOT_READY_STATUS,
    HA_READY_STATUS,
    SINGLE_NODE_STATUS,
    get_container,
)

BASE_CONFIG = {
    'port': 3000,
    'datasource_mount_path': '/etc/grafana/provisioning/datasources',
    'config_ini_mount_path': '/etc/grafana',
    'grafana_log_level': 'info',
}


class GrafanaCharmTest(unittest.TestCase):

    def setUp(self) -> None:
        self.harness = Harness(GrafanaK8s)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.harness.add_oci_resource('grafana-image')

    def test__grafana_source_data(self):

        self.harness.set_leader(True)
        self.harness.update_config(BASE_CONFIG)
        self.assertEqual(self.harness.charm.datastore.sources, {})

        rel_id = self.harness.add_relation('grafana-source', 'prometheus')
        self.harness.add_relation_unit(rel_id, 'prometheus/0')
        self.assertIsInstance(rel_id, int)

        # test that the unit data propagates the correct way
        # which is through the triggering of on_relation_changed
        self.harness.update_relation_data(rel_id,
                                          'prometheus/0',
                                          {
                                              'private-address': '192.0.2.1',
                                              'port': 1234,
                                              'source-type': 'prometheus',
                                              'source-name': 'prometheus-app',
                                          })

        expected_first_source_data = {
            'private-address': '192.0.2.1',
            'port': 1234,
            'source-name': 'prometheus-app',
            'source-type': 'prometheus',
            'isDefault': 'true',
            'unit_name': 'prometheus/0'
        }
        self.assertEqual(expected_first_source_data,
                         dict(self.harness.charm.datastore.sources[rel_id]))

        # test that clearing the relation data leads to
        # the datastore for this data source being cleared
        self.harness.update_relation_data(rel_id,
                                          'prometheus/0',
                                          {
                                              'private-address': None,
                                              'port': None,
                                          })
        self.assertEqual(None, self.harness.charm.datastore.sources.get(rel_id))

    def test__ha_database_and_status_check(self):
        """If there is a peer connection and no database (needed for HA),
        the charm should put the application in a blocked state."""

        # start charm with one peer and no database relation
        self.harness.set_leader(True)
        self.harness.update_config(BASE_CONFIG)
        self.assertEqual(self.harness.charm.unit.status,
                         ActiveStatus())

        # ensure _check_high_availability() ends up with the correct status
        status = self.harness.charm._check_high_availability()
        self.assertEqual(status, SINGLE_NODE_STATUS)

        # make sure that triggering 'update-status' hook does not
        # overwrite the current active status
        self.harness.charm.on.update_status.emit()
        self.assertEqual(self.harness.charm.unit.status,
                         ActiveStatus())

        peer_rel_id = self.harness.add_relation('grafana', 'grafana')

        # add main unit and its data
        # self.harness.add_relation_unit(peer_rel_id, 'grafana/0')
        # will trigger the grafana-changed hook
        self.harness.update_relation_data(peer_rel_id,
                                          'grafana/0',
                                          {'private-address': '10.1.2.3'})

        # add peer unit and its data
        self.harness.add_relation_unit(peer_rel_id, 'grafana/1')
        self.harness.update_relation_data(peer_rel_id,
                                          'grafana/1',
                                          {'private-address': '10.0.0.1'})

        self.assertTrue(self.harness.charm.has_peer)
        self.assertFalse(self.harness.charm.has_db)
        self.assertEqual(self.harness.charm.unit.status, HA_NOT_READY_STATUS)

        # ensure update-status hook doesn't overwrite this
        self.harness.charm.on.update_status.emit()
        self.assertEqual(self.harness.charm.unit.status,
                         HA_NOT_READY_STATUS)

        # now add the database connection and the model should
        # not have a blocked status
        db_rel_id = self.harness.add_relation('database', 'mysql')
        self.harness.add_relation_unit(db_rel_id, 'mysql/0')
        self.harness.update_relation_data(db_rel_id,
                                          'mysql/0',
                                          {
                                              'type': 'mysql',
                                              'host': '10.10.10.10:3306',
                                              'name': 'test_mysql_db',
                                              'user': 'test-admin',
                                              'password': 'super!secret!password',
                                          })
        self.assertTrue(self.harness.charm.has_db)
        self.assertEqual(self.harness.charm.unit.status, ActiveStatus())

        # ensure _check_high_availability() ends up with the correct status
        status = self.harness.charm._check_high_availability()
        self.assertEqual(status, HA_READY_STATUS)

    def test__database_relation_data(self):
        self.harness.set_leader(True)
        self.harness.update_config(BASE_CONFIG)
        self.assertEqual(self.harness.charm.datastore.database, {})

        # add relation and update relation data
        rel_id = self.harness.add_relation('database', 'mysql')
        rel = self.harness.model.get_relation('database')
        self.harness.add_relation_unit(rel_id, 'mysql/0')
        test_relation_data = {
            'type': 'mysql',
            'host': '0.1.2.3:3306',
            'name': 'my-test-db',
            'user': 'test-user',
            'password': 'super!secret!password',
        }
        self.harness.update_relation_data(rel_id,
                                          'mysql/0',
                                          test_relation_data)
        # check that charm datastore was properly set
        self.assertEqual(dict(self.harness.charm.datastore.database),
                         test_relation_data)

        # now depart this relation and ensure the datastore is emptied
        self.harness.charm.on.database_relation_broken.emit(rel)
        self.assertEqual({}, dict(self.harness.charm.datastore.database))

    def test__multiple_database_relation_handling(self):
        self.harness.set_leader(True)
        self.harness.update_config(BASE_CONFIG)
        self.assertEqual(self.harness.charm.datastore.database, {})

        # add first database relation
        self.harness.add_relation('database', 'mysql')

        # add second database relation -- should fail here
        with self.assertRaises(TooManyRelatedAppsError):
            self.harness.add_relation('database', 'mysql')
            self.harness.charm.model.get_relation('database')

    def test__multiple_source_relations(self):
        """This will test data-source config text with multiple sources.

        Specifically, it will test multiple grafana-source relations."""
        self.harness.set_leader(True)
        self.harness.update_config(BASE_CONFIG)
        self.assertEqual(self.harness.charm.datastore.sources, {})

        # add first relation
        rel_id0 = self.harness.add_relation('grafana-source', 'prometheus')
        self.harness.add_relation_unit(rel_id0, 'prometheus/0')

        # add test data to grafana-source relation
        # and test that _make_data_source_config_text() works as expected
        prom_source_data = {
            'private-address': '192.0.2.1',
            'port': 4321,
            'source-type': 'prometheus'
        }
        self.harness.update_relation_data(rel_id0, 'prometheus/0', prom_source_data)
        header_text = textwrap.dedent("""
                apiVersion: 1

                datasources:""")
        correct_config_text0 = header_text + textwrap.dedent("""
            - name: prometheus/0
              type: prometheus
              access: proxy
              url: http://192.0.2.1:4321
              isDefault: true
              editable: true
              orgId: 1""")

        generated_text = self.harness.charm._make_data_source_config_text()
        self.assertEqual(correct_config_text0 + '\n', generated_text)

        # add another source relation and check the resulting config text
        jaeger_source_data = {
            'private-address': '255.255.255.0',
            'port': 7890,
            'source-type': 'jaeger',
            'source-name': 'jaeger-application'
        }
        rel_id1 = self.harness.add_relation('grafana-source', 'jaeger')
        self.harness.add_relation_unit(rel_id1, 'jaeger/0')
        self.harness.update_relation_data(rel_id1, 'jaeger/0', jaeger_source_data)

        correct_config_text1 = correct_config_text0 + textwrap.dedent("""
            - name: jaeger-application
              type: jaeger
              access: proxy
              url: http://255.255.255.0:7890
              isDefault: false
              editable: true
              orgId: 1""")

        generated_text = self.harness.charm._make_data_source_config_text()
        self.assertEqual(correct_config_text1 + '\n', generated_text)

        # test removal of second source results in config_text
        # that is the same as the original
        self.harness.update_relation_data(rel_id1,
                                          'jaeger/0',
                                          {
                                              'private-address': None,
                                              'port': None,
                                          })
        generated_text = self.harness.charm._make_data_source_config_text()
        correct_text_after_removal = textwrap.dedent("""
            apiVersion: 1

            deleteDatasources:
            - name: jaeger-application
              orgId: 1

            datasources:
            - name: prometheus/0
              type: prometheus
              access: proxy
              url: http://192.0.2.1:4321
              isDefault: true
              editable: true
              orgId: 1""")

        self.assertEqual(correct_text_after_removal + '\n', generated_text)

        # now test that the 'deleteDatasources' is gone
        generated_text = self.harness.charm._make_data_source_config_text()
        self.assertEqual(correct_config_text0 + '\n', generated_text)

    def test__pod_spec_container_datasources(self):
        self.harness.set_leader(True)
        self.harness.update_config(BASE_CONFIG)
        self.assertEqual(self.harness.charm.datastore.sources, {})

        # add first relation
        rel_id = self.harness.add_relation('grafana-source', 'prometheus')
        self.harness.add_relation_unit(rel_id, 'prometheus/0')

        # add test data to grafana-source relation
        # and test that _make_data_source_config_text() works as expected
        prom_source_data = {
            'private-address': '192.0.2.1',
            'port': 4321,
            'source-type': 'prometheus'
        }
        self.harness.update_relation_data(rel_id, 'prometheus/0', prom_source_data)

        data_source_file_text = textwrap.dedent("""
            apiVersion: 1

            datasources:
            - name: prometheus/0
              type: prometheus
              access: proxy
              url: http://192.0.2.1:4321
              isDefault: true
              editable: true
              orgId: 1
              """)

        config_ini_file_text = textwrap.dedent("""
        [paths]
        provisioning = /etc/grafana/provisioning

        [log]
        mode = console
        level = {0}
        """).format(
            self.harness.model.config['grafana_log_level'],
        )

        expected_container_files_spec = [
            {
                'name': 'grafana-datasources',
                'mountPath': self.harness.model.config['datasource_mount_path'],
                'files': [{
                    'path': 'datasources.yaml',
                    'content': data_source_file_text,
                }],
            },
            {
                'name': 'grafana-config-ini',
                'mountPath': self.harness.model.config['config_ini_mount_path'],
                'files': [{
                    'path': 'grafana.ini',
                    'content': config_ini_file_text,
                }]
            }
        ]
        pod_spec, _ = self.harness.get_pod_spec()
        container = get_container(pod_spec, 'grafana')
        actual_container_files_spec = container['volumeConfig']
        self.assertEqual(expected_container_files_spec,
                         actual_container_files_spec)

    def test__access_sqlite_storage_location(self):
        expected_path = '/var/lib/grafana'
        actual_path = self.harness.charm.meta.storages['sqlitedb'].location
        self.assertEqual(expected_path, actual_path)

    def test__config_ini_without_database(self):
        self.harness.update_config(BASE_CONFIG)
        expected_config_text = textwrap.dedent("""
        [paths]
        provisioning = /etc/grafana/provisioning

        [log]
        mode = console
        level = {0}
        """).format(
            self.harness.model.config['grafana_log_level'],
        )

        actual_config_text = self.harness.charm._make_config_ini_text()
        self.assertEqual(expected_config_text, actual_config_text)

    def test__config_ini_with_database(self):
        self.harness.set_leader(True)
        self.harness.update_config(BASE_CONFIG)

        # add database relation and update relation data
        rel_id = self.harness.add_relation('database', 'mysql')
        self.harness.add_relation_unit(rel_id, 'mysql/0')
        test_relation_data = {
            'type': 'mysql',
            'host': '0.1.2.3:3306',
            'name': 'my-test-db',
            'user': 'test-user',
            'password': 'super!secret!password',
        }
        self.harness.update_relation_data(rel_id,
                                          'mysql/0',
                                          test_relation_data)

        # test the results of _make_config_ini_text()
        expected_config_text = textwrap.dedent("""
        [paths]
        provisioning = /etc/grafana/provisioning

        [log]
        mode = console
        level = {0}

        [database]
        type = mysql
        host = 0.1.2.3:3306
        name = my-test-db
        user = test-user
        password = super!secret!password
        url = mysql://test-user:super!secret!password@0.1.2.3:3306/my-test-db""").format(
            self.harness.model.config['grafana_log_level'],
        )

        actual_config_text = self.harness.charm._make_config_ini_text()
        self.assertEqual(expected_config_text, actual_config_text)

    def test__duplicate_source_names(self):
        self.harness.set_leader(True)
        self.harness.update_config(BASE_CONFIG)
        self.assertEqual(self.harness.charm.datastore.sources, {})

        # add first relation
        p_rel_id = self.harness.add_relation('grafana-source', 'prometheus')
        p_rel = self.harness.model.get_relation('grafana-source', p_rel_id)
        self.harness.add_relation_unit(p_rel_id, 'prometheus/0')

        # add test data to grafana-source relation
        prom_source_data0 = {
            'private-address': '192.0.2.1',
            'port': 4321,
            'source-type': 'prometheus',
            'source-name': 'duplicate-source-name'
        }
        self.harness.update_relation_data(p_rel_id, 'prometheus/0', prom_source_data0)
        expected_source_data = {
            'private-address': '192.0.2.1',
            'port': 4321,
            'source-name': 'duplicate-source-name',
            'source-type': 'prometheus',
            'isDefault': 'true',
            'unit_name': 'prometheus/0'
        }
        self.assertEqual(dict(self.harness.charm.datastore.sources[p_rel_id]),
                         expected_source_data)

        # add second source with the same name as the first source
        g_rel_id = self.harness.add_relation('grafana-source', 'graphite')
        self.harness.add_relation_unit(g_rel_id, 'graphite/0')

        graphite_source_data0 = {
            'private-address': '192.12.23.34',
            'port': 4321,
            'source-type': 'graphite',
            'source-name': 'duplicate-source-name'
        }
        self.harness.update_relation_data(g_rel_id, 'graphite/0', graphite_source_data0)
        self.assertEqual(None, self.harness.charm.datastore.sources.get(g_rel_id))
        self.assertEqual(1, len(self.harness.charm.datastore.sources))

        # now remove the relation and ensure datastore source-name is removed
        self.harness.charm.on.grafana_source_relation_broken.emit(p_rel)
        self.assertEqual(None, self.harness.charm.datastore.sources.get(p_rel_id))
        self.assertEqual(0, len(self.harness.charm.datastore.sources))

    def test__idempotent_datasource_file_hash(self):
        self.harness.set_leader(True)
        self.harness.update_config(BASE_CONFIG)

        rel_id = self.harness.add_relation('grafana-source', 'prometheus')
        self.harness.add_relation_unit(rel_id, 'prometheus/0')
        self.assertIsInstance(rel_id, int)

        # test that the unit data propagates the correct way
        # which is through the triggering of on_relation_changed
        self.harness.update_relation_data(rel_id,
                                          'prometheus/0',
                                          {
                                              'private-address': '192.0.2.1',
                                              'port': 1234,
                                              'source-type': 'prometheus',
                                              'source-name': 'prometheus-app',
                                          })

        # get a hash of the created file and check that it matches the pod spec
        pod_spec, _ = self.harness.get_pod_spec()
        container = get_container(pod_spec, 'grafana')
        hash_text = hashlib.md5(
            container['volumeConfig'][0]['files'][0]['content'].encode()).hexdigest()
        self.assertEqual(container['envConfig']['DATASOURCES_YAML'], hash_text)

        # test the idempotence of the call by re-configuring the pod spec
        self.harness.charm.configure_pod()
        self.assertEqual(container['envConfig']['DATASOURCES_YAML'], hash_text)
