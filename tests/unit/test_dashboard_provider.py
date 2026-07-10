# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import copy
import dataclasses
import json
import unittest
import uuid
from unittest.mock import patch

import pytest
import yaml
from charms.grafana_k8s.v0.grafana_dashboard import (
    CharmedDashboard,
    GrafanaDashboardProvider,
    InvalidDirectoryPathError,
)
from cosl import LZMABase64
from ops.charm import CharmBase
from ops.framework import StoredState
from ops.testing import Context, Harness, Model, Relation, State

if "unittest.util" in __import__("sys").modules:
    # Show full diff in self.assertEqual.
    __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

RELATION_TEMPLATES_DATA = {
    "file:first": {
        "charm": "provider-tester",
        "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4ABnAGFdAD2IioaUXFVrEu9eEJyRf99sCsBItFjkmWby27QUlLkEOLcnhduY4+mCN01d1q200x5gz1Apuivvaa7GnxNV4yiVBn3QjP2OBr0vK+YIyoLqYOFFTVApImfM8MR4BO6WQAAAAAAAZwA0Rx1MbSEAAX1o+lt++R+2830BAAAAAARZWg==",
        "inject_dropdowns": True,
        "dashboard_alt_uid": "6291687b37603a46",
        "juju_topology": {
            "model": "testing",
            "model_uuid": "abcdefgh-1234",
            "application": "provider-tester",
            "unit": "provider-tester/0",
        },
    },
    "file:other": {
        "charm": "provider-tester",
        "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4ABoAGJdAD2IioaUXFVrEu9eFYCcHnOClmJwFGpUF9+f4scQVLIVh0dGRthp7VR8CepwuMuYM/ENRpca4OEO01DyoSAoNKyvNYzdITZDhBzuG6/HGZIDoZL34cJn3QP2kFr4HMRCtAAAAAAAmGsLclsH64QAAX5przhUpR+2830BAAAAAARZWg==",
        "inject_dropdowns": True,
        "dashboard_alt_uid": "a44939b79a5ba1d4",
        "juju_topology": {
            "model": "testing",
            "model_uuid": "abcdefgh-1234",
            "application": "provider-tester",
            "unit": "provider-tester/0",
        },
    },
}

MANUAL_TEMPLATE_DATA = {
    "file:manual": {
        "charm": "provider-tester",
        "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4ABoAGRdAD2IioaUXFVrEu9eEzLJAYcoJaoKeAoA9UD/AQKJqydHHoSE4tSLR65Xmqkzo/Sw/nNZImWBh5mIcpaLjVmjkrOlu9xza7tlno4m4n26CTdZOjfkAc3UD48RvzIVxS7j8POwIAAAEJtP70FL2ooAAYABaQAAADxRq6axxGf7AgAAAAAEWVo=",
        "inject_dropdowns": True,
        "dashboard_alt_uid": "0b73d01f7b214e98",
        "juju_topology": {
            "application": "provider-tester",
            "model": "testing",
            "model_uuid": "abcdefgh-1234",
            "unit": "provider-tester/0",
        },
    }
}


MANUAL_TEMPLATE_DATA_NO_DROPDOWNS = {
    "file:manual": {
        "charm": "provider-tester",
        "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+Wj4ABoAGRdAD2IioaUXFVrEu9eEzLJAYcoJaoKeAoA9UD/AQKJqydHHoSE4tSLR65Xmqkzo/Sw/nNZImWBh5mIcpaLjVmjkrOlu9xza7tlno4m4n26CTdZOjfkAc3UD48RvzIVxS7j8POwIAAAEJtP70FL2ooAAYABaQAAADxRq6axxGf7AgAAAAAEWVo=",
        "inject_dropdowns": False,
        "dashboard_alt_uid": "0b73d01f7b214e98",
        "juju_topology": {},
    }
}


CONSUMER_META = """
name: provider-tester
containers:
  grafana-tester:
provides:
  grafana-dashboard:
    interface: grafana_dashboard
"""


class ProviderCharm(CharmBase):
    _stored = StoredState()

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.provider = GrafanaDashboardProvider(self)

        self._stored.set_default(valid_events=0)  # available data sources
        self._stored.set_default(invalid_events=0)

        self.framework.observe(
            self.provider.on.dashboard_status_changed,
            self._on_dashboard_status_changed,
        )

    def _on_dashboard_status_changed(self, event):
        if event.valid:
            self._stored.valid_events += 1
        elif event.error_message:
            self._stored.invalid_events += 1


@patch.object(uuid, "uuid4", new=lambda: "12345678")
class TestDashboardProvider(unittest.TestCase):
    def setUp(self):
        patcher = patch("charms.grafana_k8s.v0.grafana_dashboard._resolve_dir_against_charm_path")
        self.mock_resolve_dir = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_resolve_dir.return_value = "./tests/unit/dashboard_templates"
        self.harness = Harness(ProviderCharm, meta=CONSUMER_META)
        self.harness._backend.model_name = "testing"
        self.harness._backend.model_uuid = "abcdefgh-1234"
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.harness.set_leader(True)

    def test_provider_sets_dashboard_data(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )

        self.assertDictEqual(
            {
                "templates": RELATION_TEMPLATES_DATA,
                "uuid": "12345678",
            },
            data,
        )

    def test_provider_can_remove_programmatically_added_dashboards(self):
        self.harness.charm.provider.add_dashboard("third")

        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )

        expected_data_builtin_dashboards = {
            "templates": copy.deepcopy(RELATION_TEMPLATES_DATA),
            "uuid": "12345678",
        }

        expected_data = copy.deepcopy(expected_data_builtin_dashboards)
        expected_templates = expected_data["templates"]
        expected_templates["prog:uC2Arx+2"] = {  # type: ignore
            "charm": "provider-tester",
            "content": "/Td6WFoAAATm1rRGAgAhARYAAAB0L+WjAQAEdGhpcmQAAAAAtr5hbOrisy0AAR0FuC2Arx+2830BAAAAAARZWg==",
            "inject_dropdowns": True,
            "dashboard_alt_uid": "9f3746a8f16304dd",
            "juju_topology": {
                "model": "testing",
                "model_uuid": "abcdefgh-1234",
                "application": "provider-tester",
                "unit": "provider-tester/0",
            },
        }

        self.assertDictEqual(expected_data, actual_data)
        self.harness.charm.provider.remove_non_builtin_dashboards()
        self.assertEqual(
            expected_data_builtin_dashboards,
            json.loads(
                self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
            ),
        )

    def test_provider_cannot_remove_builtin_dashboards(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )

        expected_data = {
            "templates": RELATION_TEMPLATES_DATA,
            "uuid": "12345678",
        }

        self.assertDictEqual(expected_data, actual_data)

        self.harness.charm.provider.remove_non_builtin_dashboards()
        self.assertEqual(
            expected_data,
            json.loads(
                self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
            ),
        )

    def test_provider_destroys_old_data_on_rescan(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        expected_data = {
            "templates": RELATION_TEMPLATES_DATA,
            "uuid": "12345678",
        }
        self.assertDictEqual(expected_data, actual_data)

        self.harness.charm.provider._dashboards_path = "./tests/unit/manual_dashboards"
        self.harness.charm.provider._reinitialize_dashboard_data()
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        expected_data = {
            "templates": MANUAL_TEMPLATE_DATA,
            "uuid": "12345678",
        }
        self.assertDictEqual(expected_data, actual_data)

    def test_provider_can_rescan_and_avoid_dropdowns(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        expected_data = {
            "templates": RELATION_TEMPLATES_DATA,
            "uuid": "12345678",
        }
        self.assertDictEqual(expected_data, actual_data)

        self.harness.charm.provider._dashboards_path = "./tests/unit/manual_dashboards"
        self.harness.charm.provider._reinitialize_dashboard_data(inject_dropdowns=False)
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        expected_data = {
            "templates": MANUAL_TEMPLATE_DATA_NO_DROPDOWNS,
            "uuid": "12345678",
        }
        self.assertDictEqual(expected_data, actual_data)

    def test_provider_empties_data_on_exception(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        expected_data = {
            "templates": RELATION_TEMPLATES_DATA,
            "uuid": "12345678",
        }
        self.assertDictEqual(expected_data, actual_data)

        self.mock_resolve_dir.side_effect = InvalidDirectoryPathError("foo", "bar")
        self.harness.charm.provider._reinitialize_dashboard_data()
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        empty_data = {
            "templates": {},
            "uuid": "12345678",
        }
        self.assertDictEqual(empty_data, actual_data)

    def test_provider_clears_data_on_empty_dir(self):
        rel_id = self.harness.add_relation("grafana-dashboard", "other_app")
        self.harness.add_relation_unit(rel_id, "other_app/0")
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        expected_data = {
            "templates": RELATION_TEMPLATES_DATA,
            "uuid": "12345678",
        }
        self.assertDictEqual(expected_data, actual_data)

        self.harness.charm.provider._dashboards_path = "./tests/unit/empty_dashboards"
        self.harness.charm.provider._reinitialize_dashboard_data()
        actual_data = json.loads(
            self.harness.get_relation_data(rel_id, self.harness.model.app.name)["dashboards"]
        )
        empty_data = {
            "templates": {},
            "uuid": "12345678",
        }
        self.assertDictEqual(empty_data, actual_data)


# A dashboard we compress ourselves so the tests can assert byte-fidelity of the
# pass-through path (input bytes == published bytes == decompresses to this dict).
SAMPLE_DASHBOARD = {"title": "precompressed", "panels": [], "uid": "abc123"}
ANOTHER_DASHBOARD = {"title": "another", "panels": [], "uid": "def456"}

# Scenario tests for the relation-scoped, pass-through delta API (ADR-0001, item 4).
#
# These cover ``add_dashboard_precompressed`` and ``remove_dashboard`` on
# ``GrafanaDashboardProvider``: verbatim (no re-compress) pass-through,
# caller-controlled keying, selective keyed removal, and the guarantee that
# neither method triggers the O(N) directory rescan/re-compress performed by
# ``reload_dashboards``.

MODEL = Model(name="testing", uuid="abcdefgh-1234")


@pytest.fixture(autouse=True)
def _fixed_uuid():
    """Freeze the databag uuid so template comparisons are deterministic."""
    with patch.object(uuid, "uuid4", new=lambda: "12345678"):
        yield


@pytest.fixture(autouse=True)
def _fixed_dashboards_dir():
    """Point the provider at the built-in fixture dir so ``file:`` dashboards exist."""
    with patch(
        "charms.grafana_k8s.v0.grafana_dashboard._resolve_dir_against_charm_path",
        return_value="./tests/unit/dashboard_templates",
    ):
        yield


@pytest.fixture
def ctx():
    return Context(ProviderCharm, meta=yaml.safe_load(CONSUMER_META), app_name="provider-tester")


@pytest.fixture
def relation():
    return Relation("grafana-dashboard", interface="grafana_dashboard", remote_app_name="other_app")


def _templates(state, relation):
    """Extract the published dashboard templates from a relation's local app databag."""
    databag = state.get_relation(relation.id).local_app_data["dashboards"]
    return json.loads(databag)["templates"]


# 1 + 2: byte-fidelity pass-through and caller-controlled keying/schema parity.
def test_precompressed_content_is_stored_verbatim(ctx, relation):
    encoded = LZMABase64.compress(json.dumps(SAMPLE_DASHBOARD))
    state_in = State(leader=True, model=MODEL, relations={relation})

    with ctx(ctx.on.relation_created(relation), state_in) as mgr:
        mgr.charm.provider.add_dashboard_precompressed("rel_5__my-dash", encoded)
        state_out = mgr.run()

    templates = _templates(state_out, relation)
    assert "prog:rel_5__my-dash" in templates
    entry = templates["prog:rel_5__my-dash"]

    # Verbatim: the published content is byte-identical to what we passed in ...
    assert entry["content"] == encoded
    # ... and it still decompresses back to the original dashboard.
    assert json.loads(LZMABase64.decompress(entry["content"])) == SAMPLE_DASHBOARD

    # Schema parity with the rest of the databag.
    assert entry["charm"] == "provider-tester"
    assert entry["inject_dropdowns"] is True
    assert entry["juju_topology"] == {
        "model": "testing",
        "model_uuid": "abcdefgh-1234",
        "application": "provider-tester",
        "unit": "provider-tester/0",
    }
    assert entry["dashboard_alt_uid"] == CharmedDashboard._generate_alt_uid(
        "provider-tester", "prog:rel_5__my-dash"
    )


# 3: inject_dropdowns=False -> empty topology.
def test_precompressed_without_dropdowns_has_empty_topology(ctx, relation):
    encoded = LZMABase64.compress(json.dumps(SAMPLE_DASHBOARD))
    state_in = State(leader=True, model=MODEL, relations={relation})

    with ctx(ctx.on.relation_created(relation), state_in) as mgr:
        mgr.charm.provider.add_dashboard_precompressed(
            "rel_5__my-dash", encoded, inject_dropdowns=False
        )
        state_out = mgr.run()

    entry = _templates(state_out, relation)["prog:rel_5__my-dash"]
    assert entry["inject_dropdowns"] is False
    assert entry["juju_topology"] == {}


# 4: keyed removal is selective and idempotent.
def test_remove_dashboard_is_selective(ctx, relation):
    enc_a = LZMABase64.compress(json.dumps(SAMPLE_DASHBOARD))
    enc_b = LZMABase64.compress(json.dumps(ANOTHER_DASHBOARD))
    state_in = State(leader=True, model=MODEL, relations={relation})

    with ctx(ctx.on.relation_created(relation), state_in) as mgr:
        mgr.charm.provider.add_dashboard_precompressed("rel_5__a", enc_a)
        mgr.charm.provider.add_dashboard_precompressed("rel_6__b", enc_b)
        state_mid = mgr.run()

    templates = _templates(state_mid, relation)
    assert "prog:rel_5__a" in templates
    assert "prog:rel_6__b" in templates
    # The built-in file: dashboards are also present.
    assert "file:first" in templates
    assert "file:other" in templates

    # Carry the state forward: the second event must reference the relation object
    # that lives in the (mutated) output state, not the original input object.
    relation_mid = state_mid.get_relation(relation.id)
    with ctx(ctx.on.relation_changed(relation_mid), state_mid) as mgr:
        mgr.charm.provider.remove_dashboard("rel_5__a")
        state_out = mgr.run()

    templates = _templates(state_out, relation)
    assert "prog:rel_5__a" not in templates
    # Only the requested key was removed; everything else remains.
    assert "prog:rel_6__b" in templates
    assert "file:first" in templates
    assert "file:other" in templates


def test_remove_unknown_dashboard_is_noop(ctx, relation):
    state_in = State(leader=True, model=MODEL, relations={relation})

    with ctx(ctx.on.relation_created(relation), state_in) as mgr:
        state_before = mgr.run()
    before = _templates(state_before, relation)

    relation_before = state_before.get_relation(relation.id)
    with ctx(ctx.on.relation_changed(relation_before), state_before) as mgr:
        # Removing a key that was never added must not raise or change the databag.
        mgr.charm.provider.remove_dashboard("does-not-exist")
        state_out = mgr.run()

    assert _templates(state_out, relation) == before


# 5 + no-rescan: the delta path must not decompress, re-compress, or rescan the dir.
def test_delta_path_does_not_decompress_recompress_or_rescan(ctx, relation):
    # Compute the input BEFORE spying so the spies only observe library calls.
    encoded = LZMABase64.compress(json.dumps(SAMPLE_DASHBOARD))
    state_in = State(leader=True, model=MODEL, relations={relation})

    with patch.object(
        LZMABase64, "compress", wraps=LZMABase64.compress
    ) as mock_compress, patch.object(
        LZMABase64, "decompress", wraps=LZMABase64.decompress
    ) as mock_decompress, patch.object(
        CharmedDashboard,
        "load_dashboards_from_dir",
        wraps=CharmedDashboard.load_dashboards_from_dir,
    ) as mock_load_dir:
        with ctx(ctx.on.relation_changed(relation), state_in) as mgr:
            mgr.charm.provider.add_dashboard_precompressed("rel_5__my-dash", encoded)
            mgr.charm.provider.remove_dashboard("rel_5__my-dash")
            mgr.run()

    # The optimization guarantee: no payload re-compress, no decompress ...
    mock_compress.assert_not_called()
    mock_decompress.assert_not_called()
    # ... and no whole-directory rescan (the O(N) path).
    mock_load_dir.assert_not_called()


def test_precompressed_add_does_not_disturb_file_dashboards(ctx, relation):
    encoded = LZMABase64.compress(json.dumps(SAMPLE_DASHBOARD))
    state_in = State(leader=True, model=MODEL, relations={relation})

    # First, publish the built-in file: dashboards without any delta.
    with ctx(ctx.on.relation_created(relation), state_in) as mgr:
        state_before = mgr.run()
    before_file_entries = {
        k: v for k, v in _templates(state_before, relation).items() if k.startswith("file:")
    }

    # Then add a precompressed delta and confirm the file: entries are untouched.
    relation_before = state_before.get_relation(relation.id)
    with ctx(ctx.on.relation_changed(relation_before), state_before) as mgr:
        mgr.charm.provider.add_dashboard_precompressed("rel_5__my-dash", encoded)
        state_out = mgr.run()

    after_file_entries = {
        k: v for k, v in _templates(state_out, relation).items() if k.startswith("file:")
    }
    assert before_file_entries == after_file_entries


# 6: empty-arg guard.
def test_empty_key_raises(ctx, relation):
    encoded = LZMABase64.compress(json.dumps(SAMPLE_DASHBOARD))
    state_in = State(leader=True, model=MODEL, relations={relation})

    with ctx(ctx.on.relation_created(relation), state_in) as mgr:
        with pytest.raises(ValueError):
            mgr.charm.provider.add_dashboard_precompressed("", encoded)
        mgr.run()


def test_empty_content_raises(ctx, relation):
    state_in = State(leader=True, model=MODEL, relations={relation})

    with ctx(ctx.on.relation_created(relation), state_in) as mgr:
        with pytest.raises(ValueError):
            mgr.charm.provider.add_dashboard_precompressed("rel_5__my-dash", "")
        mgr.run()


# 7: leadership: a non-leader mutates internal state but does not publish; once
# leadership is gained the accumulated delta is flushed to the databag.
def test_non_leader_does_not_publish_but_leader_flushes(ctx, relation):
    encoded = LZMABase64.compress(json.dumps(SAMPLE_DASHBOARD))
    state_in = State(leader=False, model=MODEL, relations={relation})

    # As a non-leader the delta is accepted internally but NOT written to the databag.
    with ctx(ctx.on.relation_changed(relation), state_in) as mgr:
        mgr.charm.provider.add_dashboard_precompressed("rel_5__my-dash", encoded)
        state_non_leader = mgr.run()

    assert "dashboards" not in state_non_leader.get_relation(relation.id).local_app_data

    # Carrying that same (internally-updated) state into a leader run and triggering
    # a publish flushes the accumulated delta to the databag. This also proves the
    # delta survived in the charm's stored state across the leadership transition.
    leader_state = dataclasses.replace(state_non_leader, leader=True)
    relation_carried = leader_state.get_relation(relation.id)
    with ctx(ctx.on.relation_changed(relation_carried), leader_state) as mgr:
        mgr.charm.provider.update_dashboards()
        state_leader = mgr.run()

    assert "prog:rel_5__my-dash" in _templates(state_leader, relation)


# 8: republishing the same key+content does not churn the databag uuid.
def test_idempotent_republish_does_not_change_uuid(ctx, relation):
    encoded = LZMABase64.compress(json.dumps(SAMPLE_DASHBOARD))
    state_in = State(leader=True, model=MODEL, relations={relation})

    with ctx(ctx.on.relation_created(relation), state_in) as mgr:
        mgr.charm.provider.add_dashboard_precompressed("rel_5__my-dash", encoded)
        state_first = mgr.run()
    first = json.loads(state_first.get_relation(relation.id).local_app_data["dashboards"])

    # Adding the identical key+content again is a no-op on the databag: the
    # _upset guard skips the write, so the uuid is unchanged even though uuid4
    # would now return a different value.
    relation_first = state_first.get_relation(relation.id)
    with patch.object(uuid, "uuid4", new=lambda: "99999999"):
        with ctx(ctx.on.relation_changed(relation_first), state_first) as mgr:
            mgr.charm.provider.add_dashboard_precompressed("rel_5__my-dash", encoded)
            state_second = mgr.run()
    second = json.loads(state_second.get_relation(relation.id).local_app_data["dashboards"])

    assert first["uuid"] == second["uuid"]
    assert first["templates"] == second["templates"]
