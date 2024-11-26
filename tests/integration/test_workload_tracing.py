#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
from pathlib import Path

import pytest
import yaml
from helpers import (
    oci_image,
    check_grafana_is_ready,
    deploy_tempo_cluster,
    get_traces_patiently,
    get_application_ip,
)

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = "grafana"
TEMPO_APP_NAME = "tempo"
RESOURCES = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
    "litestream-image": oci_image("./charmcraft.yaml", "litestream-image"),
}


async def test_setup_env(ops_test):
    await ops_test.model.set_config({"logging-config": "<root>=WARNING; unit=DEBUG"})


@pytest.mark.abort_on_fail
async def test_workload_tracing_is_present(ops_test, grafana_charm):
    logger.info("deploying tempo cluster")
    await deploy_tempo_cluster(ops_test)

    logger.info("deploying local charm")
    await ops_test.model.deploy(
        grafana_charm, resources=RESOURCES, application_name=APP_NAME, trust=True
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME], status="active", timeout=300, wait_for_exact_units=1
    )

    await check_grafana_is_ready(ops_test, APP_NAME, 0)
    # we relate _only_ workload tracing not to confuse with charm traces
    await ops_test.model.add_relation(
        "{}:workload-tracing".format(APP_NAME), "{}:tracing".format(TEMPO_APP_NAME)
    )
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active")

    # Verify workload traces from grafana are ingested into Tempo
    assert await get_traces_patiently(
        await get_application_ip(ops_test, TEMPO_APP_NAME),
        service_name=f"{APP_NAME}",
        tls=False,
    )
