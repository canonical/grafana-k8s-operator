#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the logging (LogForwarder) integration."""

import logging
from pathlib import Path

import jubilant
import pytest
import yaml
from helpers import oci_image
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
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
    juju.deploy(charm="loki-k8s", app="loki", channel="1/edge", trust=True)

    # WHEN we integrate grafana with loki via the logging relation
    juju.integrate("grafana:logging", "loki:logging")
    juju.wait(jubilant.all_active, delay=10, timeout=600)

    # THEN the integration is active
    status = juju.status()
    assert status.apps["grafana"].app_status.current == "active"
    assert status.apps["loki"].app_status.current == "active"
