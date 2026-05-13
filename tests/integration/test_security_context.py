#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for non-root container security context compliance."""

import logging
from pathlib import Path

import lightkube
import pytest
import yaml
from helpers import (
    assert_security_context,
    generate_container_securitycontext_map,
    get_pod_names,
    oci_image,
)
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
CONTAINERS_SECURITY_CONTEXT_MAP = generate_container_securitycontext_map(METADATA)

grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
}


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest, grafana_charm):
    """Deploy the grafana charm and wait for active status."""
    await ops_test.model.deploy(
        grafana_charm,
        resources=grafana_resources,
        application_name="grafana",
        trust=True,
    )
    await ops_test.model.wait_for_idle(
        apps=["grafana"],
        status="active",
        timeout=600,
    )


@pytest.mark.parametrize("container_name", list(CONTAINERS_SECURITY_CONTEXT_MAP.keys()))
async def test_container_security_context(
    ops_test: OpsTest,
    container_name: str,
) -> None:
    """Test container security context is correctly set.

    Verify that container spec defines the security context with correct
    user ID and group ID.
    """
    lightkube_client = lightkube.Client()
    pod_name = get_pod_names(ops_test.model_name, "grafana")[0]
    assert_security_context(
        lightkube_client,
        pod_name,
        container_name,
        CONTAINERS_SECURITY_CONTEXT_MAP,
        ops_test.model_name,
    )
