# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest

import pytest
from charms.grafana_k8s.v1.grafana_source import GrafanaSourceConsumer
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Harness

SOURCE_DATA = {
    "model": "test-model",
    "model_uuid": "abcdef",
    "application": "prometheus",
    "type": "prometheus",
}

OTHER_SOURCE_DATA = {
    "model": "test-model",
    "model_uuid": "abcdef",
    "application": "other",
    "type": "prometheus",
}


def generate_source_name(source_data):
    return "juju_{}_{}_{}".format(
        source_data["model"], source_data["model_uuid"], source_data["application"]
    )


class GrafanaCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._stored.set_default(source_events=0)  # available data sources
        self._stored.set_default(source_delete_events=0)

        self.grafana_uid = "grafana-1234"
        self.grafana_url = "http://ingress"
        self.grafana_consumer = GrafanaSourceConsumer(
            self,
            grafana_uid=self.grafana_uid,
            grafana_base_url=self.grafana_url,
            relation_name="grafana-source",
        )
        self.framework.observe(self.grafana_consumer.on.sources_changed, self.source_events)
        self.framework.observe(
            self.grafana_consumer.on.sources_to_delete_changed,
            self.source_delete_events,
        )

    def source_by_rel_id(self, rel_id):
        d = self.grafana_consumer.get_peer_data("sources")
        return d[str(rel_id)]

    def source_events(self, _):
        self._stored.source_events += 1

    def source_delete_events(self, _):
        self._stored.source_delete_events += 1

    @property
    def version(self):
        return "2.0.0"

    @property
    def peers(self):
        """Fetch the peer relation."""
        return self.model.get_relation("grafana")


class TestSourceConsumer(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def setUp(self):
        meta = open("charmcraft.yaml")
        self.harness = Harness(GrafanaCharm, meta=meta)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()
        self.harness.add_relation("grafana", "grafana-k8s")

    def setup_charm_relations(self, multi=False):
        """Create relations used by test cases.

        Args:
            multi: a boolean indicating if multiple relations must be
            created.
        """
        rel_ids = []
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        rel_id = self.harness.add_relation("grafana-source", "provider")
        rel_ids.append(rel_id)
        self.harness.update_relation_data(
            rel_id,
            "provider",
            {
                "grafana_source_data": json.dumps(SOURCE_DATA),
            },
        )
        self.harness.add_relation_unit(rel_id, "provider/0")
        self.harness.update_relation_data(
            rel_id, "provider/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        self.assertEqual(self.harness.charm._stored.source_events, 2)

        if multi:
            rel_id = self.harness.add_relation("grafana-source", "other-provider")
            rel_ids.append(rel_id)
            self.harness.update_relation_data(
                rel_id,
                "other-provider",
                {
                    "grafana_source_data": json.dumps(OTHER_SOURCE_DATA),
                },
            )
            self.harness.add_relation_unit(rel_id, "other-provider/0")
            self.harness.update_relation_data(
                rel_id, "other-provider/0", {"grafana_source_host": "2.3.4.5:9090"}
            )
            self.assertEqual(self.harness.charm._stored.num_events, 4)

        return rel_ids

    def validate_sources(self, sources):
        for source in sources:
            self.assertIn("source_name", source)
            self.assertIn("source_type", source)
            self.assertIn("url", source)

    def test_consumer_notifies_on_new_sources(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://1.2.3.4:9090",
            "unit": "prometheus/0",
        }

        sources = self.harness.charm.source_by_rel_id(rel_id)[0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 2)

    def test_consumer_notifies_on_new_sources_with_url_without_path(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "http://1.2.3.4:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://1.2.3.4:9090",
            "unit": "prometheus/0",
        }

        sources = self.harness.charm.source_by_rel_id(rel_id)[0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 2)

    def test_consumer_notifies_on_new_sources_with_url_with_path(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "http://1.2.3.4:9090/some/path"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://1.2.3.4:9090/some/path",
            "unit": "prometheus/0",
        }

        sources = self.harness.charm.source_by_rel_id(rel_id)[0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 2)

    def test_consumer_noop_if_data_is_empty_sources(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)

        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(rel_id, "prometheus", {"sources": "{}"})

        with pytest.raises(KeyError):
            self.harness.charm.source_by_rel_id(rel_id)
        self.assertEqual(self.harness.charm._stored.source_events, 1)

    def test_consumer_handles_multiple_relations(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://1.2.3.4:9090",
            "unit": "prometheus/0",
        }
        sources = self.harness.charm.source_by_rel_id(rel_id)[0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 2)

        other_rel_id = self.harness.add_relation("grafana-source", "other-source")
        self.harness.update_relation_data(
            other_rel_id,
            "other-source",
            {"grafana_source_data": json.dumps(OTHER_SOURCE_DATA)},
        )
        self.harness.add_relation_unit(other_rel_id, "other-source/0")
        self.harness.update_relation_data(
            other_rel_id, "other-source/0", {"grafana_source_host": "2.3.4.5:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(OTHER_SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://2.3.4.5:9090",
            "unit": "other-source/0",
        }
        sources = self.harness.charm.source_by_rel_id(other_rel_id)[0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 4)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 2)

    def test_consumer_handles_missing_grafana_source_host(self):
        # GIVEN a grafana-source relation with 2 provider units
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.add_relation_unit(rel_id, "prometheus/1")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        # WHEN they both publish a grafana_source_host
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        self.harness.update_relation_data(
            rel_id, "prometheus/1", {"grafana_source_host": "1.2.3.4:9090"}
        )
        # THEN there are no sources to delete
        self.assertFalse(self.harness.charm.grafana_consumer.get_peer_data("sources_to_delete"))

        # WHEN one unit, no longer publishes its grafana_source_host, e.g. on ingress ready event
        self.harness.update_relation_data(rel_id, "prometheus/1", {"grafana_source_host": ""})
        # THEN it's source_name is added to sources_to_delete
        expected_sources_to_delete = f"{generate_source_name(SOURCE_DATA)}_1"
        self.assertTrue(
            self.harness.charm.grafana_consumer.get_peer_data("sources_to_delete"),
            expected_sources_to_delete,
        )

    def test_consumer_handles_source_removal(self):
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 0)
        self.assertEqual(self.harness.charm._stored.source_events, 0)
        self.harness.set_leader(True)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://1.2.3.4:9090",
            "unit": "prometheus/0",
        }
        sources = self.harness.charm.source_by_rel_id(rel_id)[0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 2)

        other_rel_id = self.harness.add_relation("grafana-source", "other-source")
        self.harness.update_relation_data(
            other_rel_id,
            "other-source",
            {"grafana_source_data": json.dumps(OTHER_SOURCE_DATA)},
        )
        self.harness.add_relation_unit(other_rel_id, "other-source/0")
        self.harness.update_relation_data(
            other_rel_id, "other-source/0", {"grafana_source_host": "2.3.4.5:9090"}
        )
        completed_data = {
            "source_name": "{}_0".format(generate_source_name(OTHER_SOURCE_DATA)),
            "source_type": "prometheus",
            "url": "http://2.3.4.5:9090",
            "unit": "other-source/0",
        }
        sources = self.harness.charm.source_by_rel_id(other_rel_id)[0]

        self.assertIsNotNone(sources)
        self.assertEqual(dict(sources), completed_data)
        self.assertEqual(self.harness.charm._stored.source_events, 4)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources), 2)

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)  # type: ignore

        self.harness.charm.on["grafana-source"].relation_departed.emit(rel)
        self.assertEqual(self.harness.charm._stored.source_delete_events, 1)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources_to_delete), 1)

    def test_consumer_noop_on_source_removal_if_not_leader(self):
        self.harness.set_leader(False)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)  # type: ignore
        self.harness.charm.on["grafana-source"].relation_broken.emit(rel)
        self.assertEqual(self.harness.charm._stored.source_delete_events, 0)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources_to_delete), 0)

    def test_consumer_data_is_usable_after_upgrade(self):
        original_source_data = {
            "rel_id": [
                {
                    "source-name": "shouldconvert",
                    "source-type": "prometheus",
                    "unit": "prometheus/0",
                    "url": "1.2.3.4",
                }
            ]
        }
        compatible_source_data = {
            "rel_id": [
                {
                    "source-name": "shouldconvert",
                    "source_name": "shouldconvert",
                    "source-type": "prometheus",
                    "source_type": "prometheus",
                    "unit": "prometheus/0",
                    "url": "1.2.3.4",
                }
            ]
        }
        self.harness.set_leader(True)
        self.harness.charm.grafana_consumer._stored.sources = original_source_data
        self.harness.charm.grafana_consumer.upgrade_keys()
        # GrafanaConsumer.sources() actually puts them into a list without rel_id, which is
        # used only for tracking, so we don't check for an exact match in this lookup
        self.assertEqual(
            self.harness.charm.grafana_consumer.sources, compatible_source_data["rel_id"]
        )

    def test_consumer_noop_on_source_removal_if_bad_rel_id(self):
        self.harness.set_leader(False)
        rel_id = self.harness.add_relation("grafana-source", "prometheus")

        rel = self.harness.charm.framework.model.get_relation("grafana-source", rel_id)  # type: ignore

        self.harness.charm.on["grafana-source"].relation_broken.emit(rel)
        self.assertEqual(self.harness.charm._stored.source_delete_events, 0)
        self.assertEqual(len(self.harness.charm.grafana_consumer.sources_to_delete), 0)


class TestAppLevelSourceConsumer(unittest.TestCase):
    """Coverage for application-level (load-balanced) datasources.

    These tests exercise the HA case from the bug report: a provider that advertises a
    single, load-balanced address in its application databag should yield exactly one
    datasource whose UID does NOT contain a unit number, so it is stable across leader
    re-elections.
    """

    def setUp(self):
        meta = open("charmcraft.yaml")
        self.harness = Harness(GrafanaCharm, meta=meta)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_leader(True)
        self.harness.begin()
        self.harness.add_relation("grafana", "grafana-k8s")

    def _setup_app_source(self, app_host="http://prometheus.test-model.svc.cluster.local:9090"):
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id,
            "prometheus",
            {
                "grafana_source_data": json.dumps(SOURCE_DATA),
                "grafana_source_app_host": app_host,
            },
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        return rel_id

    def test_app_level_source_created_without_unit_number(self):
        # (a) app data only -> exactly one app-level datasource, UID has no unit number
        rel_id = self._setup_app_source()
        sources = self.harness.charm.source_by_rel_id(rel_id)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["source_name"], generate_source_name(SOURCE_DATA))
        self.assertIsNone(sources[0]["unit"])
        self.assertEqual(
            sources[0]["url"], "http://prometheus.test-model.svc.cluster.local:9090"
        )

    def test_app_level_uid_published_back_to_provider(self):
        # (e) app_datasource_uid is published back; per-unit map is empty
        rel_id = self._setup_app_source()
        app_data = self.harness.get_relation_data(rel_id, self.harness.model.app.name)
        self.assertEqual(app_data["app_datasource_uid"], generate_source_name(SOURCE_DATA))
        self.assertEqual(json.loads(app_data["datasource_uids"]), {})

    def test_both_app_and_unit_sources_created(self):
        # (c) both app and unit data -> N + 1 datasources
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id,
            "prometheus",
            {
                "grafana_source_data": json.dumps(SOURCE_DATA),
                "grafana_source_app_host": "http://prometheus.test-model.svc.cluster.local:9090",
            },
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        sources = self.harness.charm.source_by_rel_id(rel_id)
        names = sorted(s["source_name"] for s in sources)
        self.assertEqual(
            names,
            sorted(
                [
                    generate_source_name(SOURCE_DATA),
                    "{}_0".format(generate_source_name(SOURCE_DATA)),
                ]
            ),
        )

    def test_unit_to_app_migration_deletes_old_unit_source(self):
        # (d) on unit->app transition, the old per-unit UID is scheduled for deletion
        rel_id = self.harness.add_relation("grafana-source", "prometheus")
        self.harness.update_relation_data(
            rel_id, "prometheus", {"grafana_source_data": json.dumps(SOURCE_DATA)}
        )
        self.harness.add_relation_unit(rel_id, "prometheus/0")
        self.harness.update_relation_data(
            rel_id, "prometheus/0", {"grafana_source_host": "1.2.3.4:9090"}
        )
        # coherence check: one per-unit source exists
        self.assertEqual(
            self.harness.charm.source_by_rel_id(rel_id)[0]["source_name"],
            "{}_0".format(generate_source_name(SOURCE_DATA)),
        )

        # WHEN the provider switches to app mode (clears unit host, sets app host)
        self.harness.update_relation_data(
            rel_id,
            "prometheus",
            {"grafana_source_app_host": "http://prometheus.test-model.svc.cluster.local:9090"},
        )
        self.harness.update_relation_data(rel_id, "prometheus/0", {"grafana_source_host": ""})

        # THEN the old per-unit source is scheduled for deletion and the app source remains
        sources = self.harness.charm.source_by_rel_id(rel_id)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["source_name"], generate_source_name(SOURCE_DATA))
        self.assertIn(
            "{}_0".format(generate_source_name(SOURCE_DATA)),
            self.harness.charm.grafana_consumer.sources_to_delete,
        )

    def test_app_uid_stable_across_leader_reelection(self):
        # (f) the app-level UID does not depend on any unit, so re-running reconcile
        # (as happens on/after a leader re-election) leaves the UID unchanged.
        rel_id = self._setup_app_source()
        first = self.harness.charm.source_by_rel_id(rel_id)[0]["source_name"]

        # Simulate a leader re-election: leadership churns and sources are re-derived.
        self.harness.set_leader(False)
        self.harness.set_leader(True)
        self.harness.charm.grafana_consumer.update_sources()

        second = self.harness.charm.source_by_rel_id(rel_id)[0]["source_name"]
        self.assertEqual(first, second)
        self.assertNotIn("_0", second)

    def test_app_source_survives_unit_departure(self):
        # The app-level datasource is load-balanced and must survive a single provider
        # unit departing (it is only removed when the whole relation is broken).
        rel_id = self._setup_app_source()
        self.assertEqual(len(self.harness.charm.source_by_rel_id(rel_id)), 1)

        # WHEN a provider unit departs
        self.harness.remove_relation_unit(rel_id, "prometheus/0")

        # THEN the app-level source is preserved and not scheduled for deletion
        sources = self.harness.charm.source_by_rel_id(rel_id)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["source_name"], generate_source_name(SOURCE_DATA))
        self.assertNotIn(
            generate_source_name(SOURCE_DATA),
            self.harness.charm.grafana_consumer.sources_to_delete,
        )

