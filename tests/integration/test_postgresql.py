#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

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
async def test_postgresql_backend(ops_test: OpsTest, grafana_charm: str):
    assert ops_test.model
    juju = jubilant.Juju(model=ops_test.model.name)

    # GIVEN a model with grafana, pgbouncer, and postgresql charms
    juju.deploy(
        charm=grafana_charm,
        app="grafana",
        resources=RESOURCES,
        trust=True,
    )
    juju.deploy(
        charm="pgbouncer-k8s",
        app="pgbouncer",
        channel="1/stable",
        trust=True,
    )
    juju.deploy(
        charm="postgresql-k8s",
        app="postgresql",
        channel="14/stable",
        trust=True,
    )

    # WHEN pgbouncer is related to grafana and postgresql
    juju.integrate("grafana:pgsql", "pgbouncer:pgsql")
    juju.integrate("pgbouncer:backend-database", "postgresql:database")

    # THEN all charms settle in active/idle
    juju.wait(jubilant.all_active, delay=10, timeout=1200)
