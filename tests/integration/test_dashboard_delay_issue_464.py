#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Reproducer for https://github.com/canonical/grafana-k8s-operator/issues/464.

The issue reports that dashboards provided over the `grafana-dashboard`
relation take a very long time (or never) to show up in Grafana, and that
`juju debug-log` shows repeated:

    level=fatal msg="1:5: parse error: unexpected character: '$'"

The reporter's topology relates `redis-k8s` and `discourse-k8s` to
`opentelemetry-collector-k8s`, which then forwards dashboards to Grafana
over `grafana-dashboard`. This test mirrors that with `redis-k8s` (which,
unlike `discourse-k8s`, reaches active status standalone, without needing
postgresql/oauth/nginx-route):

    redis-k8s --[grafana-dashboard]--> opentelemetry-collector-k8s \\
        --[grafana-dashboard]--> grafana-k8s

It then:

  * polls the Grafana HTTP API until the dashboard shows up (or a timeout
    is hit), reporting how long it took;
  * scans `juju debug-log` for the "parse error" signature from the issue.

Two scenarios are parametrized:

  * ``test_dashboard_forwarding[known-good-*]`` deploys grafana-k8s from a
    channel (default: `dev/edge` and `12.4/edge`, overridable with
    `--grafana-channel`) and asserts the bug is NOT observed.
  * ``test_dashboard_forwarding[known-bad]`` deploys the exact revision
    from the original bug report (grafana-k8s revision 162, `2/edge`
    channel) and asserts the bug IS observed, i.e. that our reproduction
    strategy is valid and would actually catch a regression.

Run explicitly against one channel:

    uv run pytest tests/integration/test_dashboard_delay_issue_464.py \\
        --grafana-channel=dev/edge -k known-good

    uv run pytest tests/integration/test_dashboard_delay_issue_464.py \\
        --grafana-channel=12.4/edge -k known-good

    uv run pytest tests/integration/test_dashboard_delay_issue_464.py -k known-bad
"""

import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

import jubilant
import pytest
import pytest_jubilant
import requests
from urllib3 import make_headers

logger = logging.getLogger(__name__)

GRAFANA_APP = "grafana"
REDIS_APP = "redis"
OTELCOL_APP = "otelcol"

# otelcol needs a base matching the grafana-k8s channel under test, since old
# grafana-k8s revisions (e.g. rev 162) predate the ubuntu@26.04 bases used by
# otelcol's `dev/edge` / `0.130/*` channels.
OTELCOL_CHANNEL_FOR_BASE = {
    "ubuntu@20.04": "1/edge",
    "ubuntu@22.04": "1/edge",
    "ubuntu@24.04": "2/edge",
    "ubuntu@26.04": "dev/edge",
}

PARSE_ERROR_RE = re.compile(r"parse error: unexpected character: '\$'")

DASHBOARD_POLL_TIMEOUT = 600
DASHBOARD_POLL_INTERVAL = 10


@pytest.fixture
def juju(request: pytest.FixtureRequest, juju_factory: "pytest_jubilant.JujuFactory"):
    """Function-scoped Juju model, one per parametrized scenario.

    Overrides pytest-jubilant's module-scoped `juju` fixture: each entry in
    `grafana_deployment` deploys its own `grafana`/`redis`/`otelcol` apps, so
    reusing a single module-scoped model across parametrized cases would
    hit "application already exists" errors.
    """
    deployment: GrafanaDeployment = request.getfixturevalue("grafana_deployment")
    suffix = deployment.id.replace(".", "").replace("known-good-", "kg-").replace("known-bad", "kb")
    return juju_factory.get_juju(suffix=suffix)


@dataclass
class GrafanaDeployment:
    """Describes how to deploy grafana-k8s for a given test scenario."""

    id: str
    expect_bug: bool
    channel: Optional[str] = None
    revision: Optional[int] = None
    base: str = "ubuntu@24.04"


def pytest_generate_tests(metafunc):
    if "grafana_deployment" in metafunc.fixturenames:
        good_channels = [
            c.strip()
            for c in metafunc.config.getoption("--grafana-channel").split(",")
            if c.strip()
        ]
        deployments = [
            GrafanaDeployment(
                id=f"known-good-{c.replace('/', '-').replace('.', '')}",
                expect_bug=False,
                channel=c,
                base="ubuntu@26.04",
            )
            for c in good_channels
        ] + [
            GrafanaDeployment(
                id="known-bad",
                expect_bug=True,
                channel="2/edge",
                revision=162,
                base="ubuntu@24.04",
            ),
        ]
        metafunc.parametrize(
            "grafana_deployment", deployments, ids=[d.id for d in deployments], indirect=True
        )


@pytest.fixture
def grafana_deployment(request) -> GrafanaDeployment:
    return request.param


def get_admin_password(juju: jubilant.Juju, app: str) -> str:
    last_error = None
    for _ in range(10):
        try:
            task = juju.run(f"{app}/0", "get-admin-password")
            return task.results["admin-password"]
        except jubilant.TaskError as e:
            last_error = e
            time.sleep(5)
    raise last_error


def get_unit_address(juju: jubilant.Juju, app: str) -> str:
    status = juju.status()
    return status.apps[app].units[f"{app}/0"].address


def search_dashboards(juju: jubilant.Juju, app: str, password: str, query: str = "") -> list:
    address = get_unit_address(juju, app)
    if not address:
        logger.warning("No address yet for %s/0, skipping this poll", app)
        return []
    headers = make_headers(basic_auth=f"admin:{password}")
    uri = f"http://{address}:3000/api/search"
    last_error = None
    for _ in range(3):
        try:
            resp = requests.get(uri, headers=headers, params={"query": query}, timeout=10)
            resp.raise_for_status()
            return [d for d in resp.json() if d.get("type") == "dash-db"]
        except requests.exceptions.RequestException as e:
            last_error = e
            time.sleep(5)
    logger.warning("Failed to reach Grafana search API: %s", last_error)
    return []


def count_parse_errors(juju: jubilant.Juju) -> int:
    log = juju.cli("debug-log", "--replay", "--no-tail", "--limit", "20000")
    return len(PARSE_ERROR_RE.findall(log))


def test_dashboard_forwarding(juju: jubilant.Juju, grafana_deployment: GrafanaDeployment):
    """Deploy redis-k8s -> otelcol -> grafana-k8s and check for issue #464's symptoms."""
    deploy_kwargs = {"trust": True}
    if grafana_deployment.channel:
        deploy_kwargs["channel"] = grafana_deployment.channel
    if grafana_deployment.revision is not None:
        deploy_kwargs["revision"] = grafana_deployment.revision

    logger.info("Deploying grafana-k8s: %s", deploy_kwargs)
    juju.deploy("grafana-k8s", app=GRAFANA_APP, **deploy_kwargs)
    juju.deploy("redis-k8s", app=REDIS_APP, channel="latest/edge", trust=True)

    otelcol_channel = OTELCOL_CHANNEL_FOR_BASE[grafana_deployment.base]
    juju.deploy(
        "opentelemetry-collector-k8s",
        app=OTELCOL_APP,
        channel=otelcol_channel,
        trust=True,
    )

    juju.wait(
        lambda status: jubilant.all_active(status, GRAFANA_APP, REDIS_APP, OTELCOL_APP),
        timeout=600,
        error=jubilant.any_error,
    )

    juju.integrate(f"{REDIS_APP}:grafana-dashboard", f"{OTELCOL_APP}:grafana-dashboards-consumer")
    juju.integrate(f"{GRAFANA_APP}:grafana-dashboard", f"{OTELCOL_APP}:grafana-dashboards-provider")
    juju.wait(
        lambda status: jubilant.all_active(status, GRAFANA_APP, REDIS_APP, OTELCOL_APP),
        timeout=300,
    )

    password = get_admin_password(juju, GRAFANA_APP)

    start = time.time()
    found = False
    elapsed = 0.0
    while elapsed < DASHBOARD_POLL_TIMEOUT:
        dashboards = search_dashboards(juju, GRAFANA_APP, password)
        if dashboards:
            found = True
            break
        time.sleep(DASHBOARD_POLL_INTERVAL)
        elapsed = time.time() - start

    parse_errors = count_parse_errors(juju)
    logger.info(
        "Dashboard found=%s after %.1fs; parse errors in debug-log=%d",
        found,
        elapsed,
        parse_errors,
    )

    bug_observed = (not found) or (parse_errors > 0)

    if grafana_deployment.expect_bug:
        if not bug_observed:
            pytest.fail(
                "Expected to reproduce https://github.com/canonical/grafana-k8s-operator/"
                "issues/464 with the known-bad revision, but no delay/missing dashboard "
                "or parse errors were observed. The reproduction strategy may no longer "
                "be valid, or the environment doesn't match the original report."
            )
        logger.info(
            "Issue #464 reproduced as expected on the known-bad revision "
            "(found=%s, parse_errors=%d).",
            found,
            parse_errors,
        )
        return

    # known-good scenario: bug should NOT be observed
    if not found:
        pytest.fail(
            f"No redis dashboard appeared in Grafana after {DASHBOARD_POLL_TIMEOUT}s "
            f"(parse errors seen in debug-log: {parse_errors}). "
            "This reproduces https://github.com/canonical/grafana-k8s-operator/issues/464."
        )

    if parse_errors:
        pytest.fail(
            f"Dashboard eventually appeared after {elapsed:.1f}s, but "
            f"{parse_errors} 'parse error: unexpected character: $' entries were "
            "found in juju debug-log, matching the symptom reported in "
            "https://github.com/canonical/grafana-k8s-operator/issues/464."
        )

    logger.info(
        "Dashboard appeared after %.1fs with no parse errors: issue not reproduced.", elapsed
    )
