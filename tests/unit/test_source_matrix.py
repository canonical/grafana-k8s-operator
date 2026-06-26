# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Matrix coverage for the grafana-source datasource topology.

This mirrors the test matrix agreed for issue #49 (canonical/mimir-operators):

    2 ingress x 2 TLS x 2 scale x 2 mode = 16 cases

The invariant being proven is that the datasource COUNT and the UID SHAPE depend only on
``(provider mode, scale)``. Ingress and TLS only ever change the URL *string* (host and
``http``/``https`` scheme); they never change how many datasources are created nor the
shape of their UIDs.

These run as consumer-side scenario tests: for each cell we synthesise the relation data
that a provider in that configuration would publish, feed it to the real
``GrafanaSourceConsumer`` (via ``GrafanaCharm``), and assert the resulting datasources.
"""

import itertools
import json

import pytest
from ops.testing import Relation, State

MODEL = "M"
MODEL_UUID = "U"
APP = "A"
APP_UID = "juju_{}_{}_{}".format(MODEL, MODEL_UUID, APP)

SOURCE_DATA = {
    "model": MODEL,
    "model_uuid": MODEL_UUID,
    "application": APP,
    "type": "prometheus",
}


def _scheme(tls: bool) -> str:
    return "https" if tls else "http"


def _app_url(tls: bool, ingress: bool) -> str:
    scheme = _scheme(tls)
    if ingress:
        return "{}://{}.ingress.example.com".format(scheme, APP)
    return "{}://{}.{}.svc.cluster.local:9090".format(scheme, APP, MODEL)


def _unit_url(tls: bool, ingress: bool, unit_idx: int) -> str:
    scheme = _scheme(tls)
    if ingress:
        return "{}://{}-{}.ingress.example.com".format(scheme, APP, unit_idx)
    return "{}://{}-{}.pod.local:9090".format(scheme, APP, unit_idx)


def _stored_sources(out, peer_relation) -> list:
    """Flatten the consumer's stored sources (across relations) from peer data."""
    peer_out = out.get_relation(peer_relation.id)
    stored = json.loads(peer_out.local_app_data.get("sources", "{}"))
    return [source for sources in stored.values() for source in sources]


def _make_relation(mode: str, scale: int, tls: bool, ingress: bool) -> Relation:
    remote_app_data = {"grafana_source_data": json.dumps(SOURCE_DATA)}
    remote_units_data = {}

    if mode == "app":
        remote_app_data["grafana_source_app_host"] = _app_url(tls, ingress)
        # In app mode units do not advertise their own address.
        for i in range(scale):
            remote_units_data[i] = {"grafana_source_host": ""}
    else:  # unit mode
        for i in range(scale):
            remote_units_data[i] = {"grafana_source_host": _unit_url(tls, ingress, i)}

    return Relation(
        "grafana-source",
        remote_app_name=APP,
        remote_app_data=remote_app_data,
        remote_units_data=remote_units_data,
    )


# Build the full 16-row matrix.
MATRIX = list(
    itertools.product(
        (False, True),  # ingress
        (False, True),  # tls
        (1, 2),  # scale
        ("app", "unit"),  # mode
    )
)


@pytest.mark.parametrize("ingress,tls,scale,mode", MATRIX)
def test_datasource_matrix(ctx, peer_relation, containers, ingress, tls, scale, mode):
    # GIVEN a provider relation configured for this matrix cell
    datasource = _make_relation(mode, scale, tls, ingress)
    state = State(leader=True, containers=containers, relations={datasource, peer_relation})

    # WHEN relation-changed fires
    out = ctx.run(ctx.on.relation_changed(datasource), state)

    local_app_data = out.get_relation(datasource.id).local_app_data
    published_unit_uids = json.loads(local_app_data["datasource_uids"])
    published_app_uid = local_app_data.get("app_datasource_uid", "")
    sources = _stored_sources(out, peer_relation)

    if mode == "app":
        # COUNT and UID SHAPE depend only on (mode, scale): app mode -> always exactly
        # one datasource, regardless of scale/ingress/TLS, with a UID that has NO unit
        # number.
        assert len(sources) == 1
        assert sources[0]["source_name"] == APP_UID
        assert sources[0]["unit"] is None
        assert published_app_uid == APP_UID
        assert published_unit_uids == {}
        # Ingress/TLS only change the URL string.
        assert sources[0]["url"] == _app_url(tls, ingress)
    else:
        # unit mode -> exactly `scale` datasources, each keyed by unit number.
        assert len(sources) == scale
        expected_names = {"{}_{}".format(APP_UID, i) for i in range(scale)}
        assert {s["source_name"] for s in sources} == expected_names
        assert published_app_uid == ""
        assert published_unit_uids == {
            "{}/{}".format(APP, i): "{}_{}".format(APP_UID, i) for i in range(scale)
        }
        # Ingress/TLS only change the URL string.
        urls = {s["url"] for s in sources}
        assert urls == {_unit_url(tls, ingress, i) for i in range(scale)}


@pytest.mark.parametrize("ingress,tls,scale", itertools.product((False, True), (False, True), (1, 2)))
def test_app_uid_is_stable_across_reconciles(ctx, peer_relation, containers, ingress, tls, scale):
    # The app-level UID is derived only from Juju topology, so re-running the consumer
    # reconcile (as happens on/after a leader re-election) never changes it. This is the
    # core guarantee from issue #49.
    datasource = _make_relation("app", scale, tls, ingress)
    state = State(leader=True, containers=containers, relations={datasource, peer_relation})

    out = ctx.run(ctx.on.relation_changed(datasource), state)
    first = out.get_relation(datasource.id).local_app_data["app_datasource_uid"]

    # Re-run reconcile against the resulting state.
    out2 = ctx.run(ctx.on.relation_changed(out.get_relation(datasource.id)), out)
    second = out2.get_relation(datasource.id).local_app_data["app_datasource_uid"]

    assert first == second == APP_UID
    assert "_0" not in second
