#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the logging (LogForwarder) integration."""

import logging
from pathlib import Path

import jubilant
import pytest
import requests
import yaml
from helpers import oci_image
from pytest_operator.plugin import OpsTest
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]
RESOURCES = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
}


@pytest.mark.abort_on_fail
async def test_logging_integration(ops_test: OpsTest, grafana_charm: str):
    """Deploy grafana and loki, integrate via logging, and verify the relation is active."""
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)

    # GIVEN a model with grafana and loki
    juju.deploy(
        charm=grafana_charm,
        app="grafana",
        resources=RESOURCES,
        trust=True,
    )
    juju.deploy(charm="loki-k8s", app="loki", channel="dev/edge", trust=True)

    # WHEN we integrate grafana with loki via the logging relation
    juju.integrate("grafana:logging", "loki:logging")
    juju.wait(jubilant.all_active, delay=10, timeout=600)

    # THEN the integration is active
    status = juju.status()
    assert status.apps["grafana"].app_status.current == "active"
    assert status.apps["loki"].app_status.current == "active"


@retry(wait=wait_fixed(15), stop=stop_after_attempt(20))
async def test_logs_are_forwarded_to_loki(ops_test: OpsTest):
    """Verify that Grafana logs are present in Loki."""
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)

    loki_address = juju.status().apps["loki"].units["loki/0"].address
    url = f"http://{loki_address}:3100/loki/api/v1/query_range"
    response = requests.get(url, params={"query": f'{{juju_application="{APP_NAME}"}}'})
    response.raise_for_status()

    result = response.json().get("data", {}).get("result", [])
    assert len(result) > 0, f"No log entries found in Loki for {APP_NAME}"
