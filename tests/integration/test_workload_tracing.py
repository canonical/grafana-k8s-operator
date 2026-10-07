#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging
from pathlib import Path

import jubilant
import pytest
import yaml
from helpers import oci_image
from requests import request
from pytest_operator.plugin import OpsTest
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
RESOURCES = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
}

TEMPO_APP = "tempo"
TEMPO_WORKER_APP = "tempo-worker"
SEAWEEDFS_APP = "seaweedfs-tempo"
PIPELINE_APPS = ("grafana", TEMPO_APP, TEMPO_WORKER_APP, SEAWEEDFS_APP)


@retry(stop=stop_after_attempt(30), wait=wait_fixed(10))
async def check_traces_from_app(tempo_ip: str, app: str):
    response = request(
        "GET", f"http://{tempo_ip}:3200/api/search", params={"juju_application": app}
    )
    traces = json.loads(response.text)["traces"]
    assert traces


def pipeline_is_settled(status: jubilant.Status, *apps: str) -> bool:
    """Report whether the given apps are active and all their unit agents are idle."""
    return jubilant.all_active(status, *apps) and jubilant.all_agents_idle(status, *apps)


@pytest.mark.abort_on_fail
async def test_workload_tracing_is_present(ops_test: OpsTest, grafana_charm: str):
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)

    # GIVEN a model with grafana, tempo, and an S3 backend
    juju.deploy(
        charm=grafana_charm,
        app="grafana",
        resources=RESOURCES,
        trust=True,
    )
    juju.deploy(charm="tempo-coordinator-k8s", app=TEMPO_APP, channel="2/edge", trust=True)
    juju.deploy(charm="tempo-worker-k8s", app=TEMPO_WORKER_APP, channel="2/edge", trust=True)
    # seaweedfs-k8s stands in for s3-integrator plus a real S3 backend: it renders the
    # s3 credentials relation itself (endpoint and placeholder keys) and creates one
    # bucket per relation, so no extra bucket or credential setup is needed.
    juju.deploy(charm="seaweedfs-k8s", app=SEAWEEDFS_APP, channel="edge")
    juju.wait(
        lambda status: pipeline_is_settled(status, SEAWEEDFS_APP),
        delay=5,
        timeout=600,
    )
    juju.integrate(f"{TEMPO_APP}:s3", f"{SEAWEEDFS_APP}:s3-credentials")
    juju.integrate(f"{TEMPO_APP}:tempo-cluster", f"{TEMPO_WORKER_APP}:tempo-cluster")

    # Wait for the tempo cluster itself (coordinator, worker, S3 backend) to fully
    # settle *before* wiring up workload-tracing to avoid 502s.
    juju.wait(
        lambda status: pipeline_is_settled(status, TEMPO_APP, TEMPO_WORKER_APP, SEAWEEDFS_APP),
        delay=5,
        timeout=600,
    )

    # WHEN we add relations to send traces to tempo
    juju.integrate("grafana:workload-tracing", f"{TEMPO_APP}:tracing")
    juju.wait(
        lambda status: pipeline_is_settled(status, *PIPELINE_APPS),
        delay=10,
        timeout=1200,
    )

    # THEN traces arrive in tempo
    tempo_ip = juju.status().apps[TEMPO_APP].units[f"{TEMPO_APP}/0"].address
    await check_traces_from_app(tempo_ip=tempo_ip, app="grafana")
