import importlib
import pathlib
import shutil
import sys
import tempfile
import textwrap
import unittest
import yaml

from ops.testing import Harness
from ops.model import ActiveStatus, MaintenanceStatus, BlockedStatus, TooManyRelatedAppsError
from charm import GrafanaK8s


# TODO: should these tests be written in a way that doesn't require
#       the harness to be built each time?
class GrafanaCharmTest(unittest.TestCase):

    def test__grafana_source_data(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
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
                                         'source-type': 'prometheus'
                                     })
        self.assertEqual(
            {
                'host': '192.0.2.1',
                'port': 1234,
                'source-name': 'prometheus/0',
                'source-type': 'prometheus',
                'isDefault': 'true',
            },
            dict(harness.charm.datastore.sources[rel_id])
        )

        # test that clearing the relation data leads to
        # the datastore for this data source being cleared
        harness.update_relation_data(rel_id,
                                     'prometheus/0',
                                     {
                                         'host': None,
                                         'port': None,
                                     })
        self.assertEqual(None, harness.charm.datastore.sources.get(rel_id))

    def test__ha_database_check(self):
        """If there is a peer connection and no database (needed for HA),
        the charm should put the application in a blocked state."""

        # start charm with one peer and no database relation
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        peer_rel_id = harness.add_relation('grafana', 'grafana')
        peer_rel = harness.charm.model.get_relation('grafana')
        harness.add_relation_unit(peer_rel_id, 'grafana/1')
        self.assertTrue(harness.charm.has_peer)
        self.assertFalse(harness.charm.has_db)
        blocked_status = \
            BlockedStatus('Need database relation for HA Grafana.')
        self.assertEqual(harness.model.unit.status, blocked_status)

        # now add the database connection and the model should
        # not have a blocked status
        db_rel_id = harness.add_relation('database', 'mysql')
        harness.add_relation_unit(db_rel_id, 'mysql/0')

        # TODO: this is sort of a manual defer (and works) but I don't like it
        #       related issue: https://github.com/canonical/operator/issues/392
        harness.charm.on.grafana_relation_joined.emit(peer_rel)
        self.assertTrue(harness.charm.has_db)
        maintenance_status = MaintenanceStatus('HA ready for configuration')
        # TODO: defer doesn't seem to work as expected here
        self.assertEqual(harness.model.unit.status, maintenance_status)

    def test__add_then_remove_peer_status_check(self):
        """Ensure that adding and removing peer results in correct status."""
        # TODO: this might require the test harness to properly defer
        #       events, but could be tested with manual event.emit()s
        #       as seen in the above test case

    def test__database_relation_data(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
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
        print(harness._get_backend_calls())
        self.assertEqual({}, dict(harness.charm.datastore.database))

    def test__multiple_database_relation_handling(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        self.assertEqual(harness.charm.datastore.database, {})

        # add first database relation
        harness.add_relation('database', 'mysql')

        # add second database relation -- should fail here
        with self.assertRaises(TooManyRelatedAppsError):
            harness.add_relation('database', 'mysql')
            harness.charm.model.get_relation('database')

    def test__make_data_source_config_text(self):
        harness = Harness(GrafanaK8s)
        self.addCleanup(harness.cleanup)
        harness.begin()
        harness.set_leader(True)
        self.assertEqual(harness.charm.datastore.sources, {})

        # add first relation
        rel_id0 = harness.add_relation('grafana-source', 'prometheus')
        harness.add_relation_unit(rel_id0, 'prometheus/0')

        # add test data to grafana-source relation
        # and test that _make_data_source_config_text() works as expected
        test_source_data = {
             'host': '192.0.2.1',
             'port': 1234,
             'source-type': 'prometheus'
        }
        harness.update_relation_data(rel_id0, 'prometheus/0', test_source_data)
        correct_config_text0 = textwrap.dedent("""
            apiVersion: 1
            
            datasources:
            - name: prometheus/0
              type: prometheus
              access: proxy
              url: http://192.0.2.1:1234
              isDefault: true
              editable: false""")
        generated_text = harness.charm._make_data_source_config_text()
        self.assertEqual(correct_config_text0, generated_text)

        # add another grafana-source and check the resulting config text
        rel_id1 = harness.add_relation('grafana-source', 'prometheus')
        harness.add_relation_unit(rel_id1, 'prometheus/1')
        harness.update_relation_data(rel_id1, 'prometheus/1', test_source_data)

        correct_config_text1 = correct_config_text0 + textwrap.dedent("""
            - name: prometheus/1
              type: prometheus
              access: proxy
              url: http://192.0.2.1:1234
              isDefault: false
              editable: false""")
        generated_text = harness.charm._make_data_source_config_text()
        self.assertEqual(correct_config_text1, generated_text)
