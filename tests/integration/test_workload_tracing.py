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
from minio import Minio
from requests import request
from tenacity import retry, stop_after_attempt, wait_fixed
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
RESOURCES = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
}


@retry(stop=stop_after_attempt(10), wait=wait_fixed(10))
async def check_traces_from_app(tempo_ip: str, app: str):
    response = request(
        "GET", f"http://{tempo_ip}:3200/api/search", params={"juju_application": app}
    )
    traces = json.loads(response.text)["traces"]
    assert traces


@pytest.mark.abort_on_fail
async def test_workload_tracing_is_present(ops_test: OpsTest, grafana_charm: str):
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)
    minio_user = "accesskey"
    minio_pass = "secretkey"
    minio_bucket = "tempo"

    # GIVEN a model with grafana, otel-collector, and tempo charms
    juju.deploy(
        charm=grafana_charm,
        app="grafana",
        resources=RESOURCES,
        trust=True,
    )
    juju.deploy(charm="tempo-coordinator-k8s", app="tempo", channel="2/edge", trust=True)
    juju.deploy(charm="tempo-worker-k8s", app="tempo-worker", channel="2/edge", trust=True)
    # Set up minio and s3-integrator
    juju.deploy(
        charm="minio",
        app="minio-tempo",
        trust=True,
        config={"access-key": minio_user, "secret-key": minio_pass},
    )
    juju.deploy(charm="s3-integrator", app="s3-tempo", channel="edge")
    juju.wait(lambda status: jubilant.all_active(status, "minio-tempo"), delay=5)
    minio_address = juju.status().apps["minio-tempo"].units["minio-tempo/0"].address
    minio_client: Minio = Minio(
        f"{minio_address}:9000",
        access_key=minio_user,
        secret_key=minio_pass,
        secure=False,
    )
    if not minio_client.bucket_exists(minio_bucket):
        minio_client.make_bucket(minio_bucket)
    juju.config("s3-tempo", {"endpoint": f"{minio_address}:9000", "bucket": minio_bucket})
    juju.run(
        unit="s3-tempo/0",
        action="sync-s3-credentials",
        params={"access-key": minio_user, "secret-key": minio_pass},
    )
    juju.integrate("tempo:s3", "s3-tempo")
    juju.integrate("tempo:tempo-cluster", "tempo-worker")
    # WHEN we add relations to send traces to tempo
    juju.integrate("grafana:workload-tracing", "tempo:tracing")
    juju.wait(jubilant.all_active, delay=10, timeout=600)

    # THEN traces arrive in tempo
    tempo_ip = juju.status().apps["tempo"].units["tempo/0"].address
    await check_traces_from_app(tempo_ip=tempo_ip, app="grafana")
