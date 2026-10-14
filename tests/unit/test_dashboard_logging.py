# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""The dashboard library must not log once per dashboard or per panel.

ops forwards every log record to Juju with a `juju-log` hook tool call (a fork), whatever
its level, so per-item logging costs seconds per hook on charms handling hundreds of
dashboards. These tests pin the number of records to one summary per operation: each one
runs with a single item and with many, and expects the same number of records.
"""

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from charms.grafana_k8s.v0.grafana_dashboard import (
    _MAX_LOGGED_EXAMPLES,
    CharmedDashboard,
    GrafanaDashboardAggregator,
    GrafanaDashboardConsumer,
    _examples,
)
from cosl import DashboardPath40UID, LZMABase64
from ops import CharmBase
from ops.testing import Context, PeerRelation, Relation, State

LIB_LOGGER = "charms.grafana_k8s.v0.grafana_dashboard"
# Larger than _MAX_LOGGED_EXAMPLES, so that the summaries also get truncated.
MANY = _MAX_LOGGED_EXAMPLES * 4
SIZES = [1, MANY]


# ---------------------------------------------------------------------------- helpers


def _lib_records(caplog: pytest.LogCaptureFixture) -> List[logging.LogRecord]:
    return [r for r in caplog.records if r.name == LIB_LOGGER]


def _juju_log_lines(ctx: Context, needle: str) -> List[Any]:
    """The `juju-log` calls whose message contains `needle`: the actual cost in production."""
    return [line for line in ctx.juju_log if needle in line.message]


def _write_dashboards(path: Path, uids: List[str]) -> None:
    for i, uid in enumerate(uids):
        (path / f"dashboard_{i}.json").write_text(json.dumps({"title": f"D{i}", "uid": uid}))


def _load(path: Path) -> Dict[str, Any]:
    return CharmedDashboard.load_dashboards_from_dir(
        dashboards_path=path,
        charm_name="my-charm",
        charm_dir=path,
        inject_dropdowns=False,
        juju_topology={},
    )


def _stored_dashboard(uid: str, relation_id: str, version: Optional[int] = None) -> dict:
    """A dashboard as stored by `GrafanaDashboardConsumer` in the peer databag."""
    dashboard: Dict[str, Any] = {"uid": uid, "title": f"Dashboard {uid}", "panels": []}
    if version is not None:
        dashboard["version"] = version
    content = LZMABase64.compress(json.dumps(dashboard))
    return {
        "id": f"grafana-dashboard:{relation_id}/{uid}",
        "original_id": uid,
        "content": content,
        "template": {"charm": "test-charm", "content": content},
    }


class DashboardConsumerTesterCharm(CharmBase):
    """Minimal consumer charm, so that tests do not depend on the Grafana charm."""

    def __init__(self, framework):
        super().__init__(framework)
        self.consumer = GrafanaDashboardConsumer(self)

    @property
    def peers(self):
        return self.model.get_relation("grafana")


CONSUMER_META = {
    "name": "dashboard-consumer-tester",
    "requires": {"grafana-dashboard": {"interface": "grafana_dashboard"}},
    "peers": {"grafana": {"interface": "grafana_peers"}},
}


class DashboardAggregatorTesterCharm(CharmBase):
    """Minimal aggregator charm (like cos-proxy), bridging reactive charms to Grafana."""

    def __init__(self, framework):
        super().__init__(framework)
        self.aggregator = GrafanaDashboardAggregator(self)


AGGREGATOR_META = {
    "name": "dashboard-aggregator-tester",
    "requires": {"dashboards": {"interface": "grafana-dashboard"}},
    "provides": {"downstream-grafana-dashboard": {"interface": "grafana_dashboard"}},
}


@pytest.fixture
def consumer_ctx() -> Context:
    return Context(DashboardConsumerTesterCharm, meta=CONSUMER_META)


@pytest.fixture
def aggregator_ctx() -> Context:
    return Context(DashboardAggregatorTesterCharm, meta=AGGREGATOR_META)


def _peer_state(stored: Dict[str, List[dict]]) -> State:
    peer = PeerRelation("grafana", local_app_data={"dashboards": json.dumps(stored)})
    return State(leader=True, relations={peer})


# ---------------------------------------------------------------------------- _examples


@pytest.mark.parametrize(
    "items, expected",
    [
        ([], ""),
        (["a", "b"], "a, b"),
        (list(range(_MAX_LOGGED_EXAMPLES)), ", ".join(map(str, range(_MAX_LOGGED_EXAMPLES)))),
        (
            list(range(_MAX_LOGGED_EXAMPLES + 1)),
            ", ".join(map(str, range(_MAX_LOGGED_EXAMPLES))) + ", ... (1 more)",
        ),
        (
            list(range(MANY)),
            ", ".join(map(str, range(_MAX_LOGGED_EXAMPLES)))
            + f", ... ({MANY - _MAX_LOGGED_EXAMPLES} more)",
        ),
    ],
    ids=["empty", "few", "exactly-max", "max-plus-one", "many"],
)
def test_examples_truncates_long_lists(items, expected):
    assert _examples(items) == expected


# ---------------------------------------------------------------------------- provider


@pytest.mark.parametrize("n", SIZES)
@pytest.mark.parametrize("keep_uid", [True, False], ids=["kept-uid", "replaced-uid"])
def test_load_dashboards_from_dir_logs_a_single_summary(tmp_path, caplog, n, keep_uid):
    # GIVEN n dashboards whose uids are either valid "Path40" uids (kept) or not (replaced)
    uids = [
        DashboardPath40UID.generate("other-charm", f"d{i}") if keep_uid else f"u{i}"
        for i in range(n)
    ]
    _write_dashboards(tmp_path, uids)

    # WHEN they are loaded
    with caplog.at_level(logging.DEBUG, logger=LIB_LOGGER):
        result = _load(tmp_path)

    # THEN all of them are loaded, with their uid kept or replaced
    assert len(result) == n
    loaded_uids = {
        json.loads(LZMABase64.decompress(d["content"]))["uid"] for d in result.values()
    }
    assert (loaded_uids == set(uids)) is keep_uid

    # AND a single DEBUG summary is logged with the counts, whatever the number of dashboards
    records = _lib_records(caplog)
    assert len(records) == 1
    assert records[0].levelno == logging.DEBUG
    kept, replaced = records[0].args[-2:]  # type: ignore[index]
    assert (kept, replaced) == ((n, 0) if keep_uid else (0, n))


@pytest.mark.parametrize(
    "not_a_dict",
    [["a", "list"], "a string", 42, None],
    ids=["list", "string", "number", "null"],
)
def test_load_dashboards_from_dir_skips_non_dict_dashboards(tmp_path, caplog, not_a_dict):
    # GIVEN valid dashboards and a valid JSON file that is not an object
    _write_dashboards(tmp_path, ["u0", "u1"])
    (tmp_path / "not_a_dict.json").write_text(json.dumps(not_a_dict))

    # WHEN they are loaded
    with caplog.at_level(logging.ERROR, logger=LIB_LOGGER):
        result = _load(tmp_path)

    # THEN the invalid file is skipped (instead of raising) and the valid ones are loaded
    assert result.keys() == {"file:dashboard_0", "file:dashboard_1"}

    # AND exactly one error mentions it
    records = _lib_records(caplog)
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR
    assert "not_a_dict.json" in records[0].getMessage()


# ---------------------------------------------------------------------------- templating


@pytest.mark.parametrize("n", SIZES)
@pytest.mark.parametrize(
    "panel, existing_templates, level",
    [
        ({"datasource": {"type": "unknown-type"}}, False, logging.DEBUG),
        ({"datasource": 42}, False, logging.ERROR),
        ({"datasource": 42}, True, logging.ERROR),
    ],
    ids=["unrecognized-type", "unknown-format", "unknown-format-existing-templates"],
)
def test_template_panels_logs_a_single_summary(caplog, n, panel, existing_templates, level):
    # GIVEN n panels that cannot be templated
    panels = [copy.deepcopy(panel) for _ in range(n)]

    # WHEN they are templated
    with caplog.at_level(logging.DEBUG, logger=LIB_LOGGER):
        result = CharmedDashboard._template_panels(panels, {}, [], existing_templates, {})

    # THEN they are left untouched
    assert result == [panel] * n

    # AND a single record is logged, whatever the number of panels
    records = _lib_records(caplog)
    assert len(records) == 1
    assert records[0].levelno == level


@pytest.mark.parametrize("n", SIZES)
def test_inject_labels_logs_a_single_summary(caplog, n):
    # GIVEN a dashboard with n panels whose datasource format is unknown
    dashboard = {"panels": [{"datasource": 42, "targets": [{"expr": "up"}]} for _ in range(n)]}
    transformer = MagicMock()

    # WHEN topology labels are injected
    with caplog.at_level(logging.DEBUG, logger=LIB_LOGGER):
        result = CharmedDashboard._inject_labels(json.dumps(dashboard), {"model": "m"}, transformer)

    # THEN the panels are skipped: no expression is transformed and the dashboard is unchanged
    transformer.inject_label_matchers.assert_not_called()
    assert json.loads(result) == dashboard

    # AND a single error is logged, whatever the number of panels
    records = _lib_records(caplog)
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR


# ---------------------------------------------------------------------------- consumer


def _missing_version(n: int) -> Dict[str, List[dict]]:
    return {"1": [_stored_dashboard(f"dash{i}", "1") for i in range(n)]}


def _missing_uid(n: int) -> Dict[str, List[dict]]:
    return {"1": [_stored_dashboard("", "1", version=1) for _ in range(n)]}


def _duplicated(n: int) -> Dict[str, List[dict]]:
    return {
        rel_id: [_stored_dashboard(f"dash{i}", rel_id, version=1) for i in range(n)]
        for rel_id in ("1", "2")
    }


@pytest.mark.parametrize("n", SIZES)
@pytest.mark.parametrize(
    "build_stored, needle, level, expected_dashboards",
    [
        (_missing_version, "'.version'", "WARNING", lambda n: n),
        (_missing_uid, "'.uid'", "ERROR", lambda n: 0),
        (_duplicated, "deduplicated", "WARNING", lambda n: n),
    ],
    ids=["missing-version", "missing-uid", "duplicated-uid"],
)
def test_consumer_dashboards_logs_a_single_summary(
    consumer_ctx, n, build_stored, needle, level, expected_dashboards
):
    # GIVEN n stored dashboards with the same problem
    state = _peer_state(build_stored(n))

    # WHEN the consumer's dashboards are read
    with consumer_ctx(consumer_ctx.on.update_status(), state) as mgr:
        dashboards = mgr.charm.consumer.dashboards

    # THEN the dashboards are returned (or omitted) as before
    assert len(dashboards) == expected_dashboards(n)

    # AND a single juju-log call reports the problem, whatever the number of dashboards
    lines = _juju_log_lines(consumer_ctx, needle)
    assert len(lines) == 1
    assert lines[0].level == level


@pytest.mark.parametrize("n", SIZES)
def test_get_dashboards_from_relation_logs_a_single_summary(consumer_ctx, n):
    # GIVEN n stored dashboards without '.version'
    state = _peer_state(_missing_version(n))

    # WHEN the dashboards of that relation are read
    with consumer_ctx(consumer_ctx.on.update_status(), state) as mgr:
        dashboards = mgr.charm.consumer.get_dashboards_from_relation(1)

    # THEN all of them are returned, with a single warning
    assert len(dashboards) == n
    lines = _juju_log_lines(consumer_ctx, "'.version'")
    assert len(lines) == 1
    assert lines[0].level == "WARNING"


def test_to_external_object_without_collector_logs_right_away(consumer_ctx):
    # GIVEN a stored dashboard without '.version'
    dashboard = _stored_dashboard("dash0", "1")

    # WHEN it is converted without passing a collector (the behaviour before the summaries)
    with consumer_ctx(consumer_ctx.on.update_status(), _peer_state({})) as mgr:
        obj = mgr.charm.consumer._to_external_object("1", dashboard)

    # THEN it falls back to version 0 and warns immediately
    assert obj["dashboard_version"] == 0
    lines = _juju_log_lines(consumer_ctx, "'.version'")
    assert len(lines) == 1
    assert lines[0].level == "WARNING"


# ---------------------------------------------------------------------------- aggregator


@pytest.mark.parametrize("n", SIZES)
def test_aggregator_logs_a_single_summary(aggregator_ctx, n):
    # GIVEN a reactive charm sending n dashboards without templating data
    requests = {
        f"request_{i}": json.dumps({"dashboard": {"title": f"D{i}"}}) for i in range(n)
    }
    relation = Relation("dashboards", remote_units_data={0: requests})
    state = State(leader=True, relations={relation})

    # WHEN the aggregator handles the relation change
    aggregator_ctx.run(aggregator_ctx.on.relation_changed(relation, remote_unit=0), state)

    # THEN a single juju-log call reports it, whatever the number of dashboards
    lines = _juju_log_lines(aggregator_ctx, "templating")
    assert len(lines) == 1
    assert lines[0].level == "DEBUG"
