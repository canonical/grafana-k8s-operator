#!/usr/bin/env python3
# Copyright 2023 Canonical
# See LICENSE file for licensing details.

import json
import logging
from pathlib import Path
import sh
import pytest
import yaml
from helpers import oci_image
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
    "litestream-image": oci_image("./charmcraft.yaml", "litestream-image"),
}


@pytest.mark.skip_if_deployed
@pytest.mark.abort_on_fail
async def test_deploy(ops_test, grafana_charm):
    await ops_test.model.deploy(
        grafana_charm,
        resources=grafana_resources,
        application_name="grafana",
        trust=True,
    )
    # python-libjuju supports noble only tarting with v3.5.2, so deploying manually
    sh.juju.deploy("self-signed-certificates", "ca", channel="1/stable")  # type: ignore[reportAttributeAccessIssue]

    await ops_test.model.add_relation("grafana:receive-ca-cert", "ca")
    await ops_test.model.wait_for_idle(
        apps=["grafana", "ca"],
        status="active",
        raise_on_blocked=False,
        raise_on_error=False,
        timeout=1000,
    )


@pytest.mark.abort_on_fail
async def test_certs_created(ops_test: OpsTest):
    """Make sure charm code creates necessary files for cert verification."""
    unit_name = "grafana/0"

    # Get relation cert
    cmd = [
        "sh",
        "-c",
        f'juju show-unit {unit_name} --format yaml | yq \'.{unit_name}."relation-info".[] | select (.endpoint=="receive-ca-cert") | ."application-data".certificates\'',
    ]
    retcode, stdout, stderr = await ops_test.run(*cmd)
    relation_certs = "".join(json.loads(stdout.rstrip()))

    # Get pushed cert
    received_cert_path = "/usr/local/share/ca-certificates/trusted-ca-cert.crt"
    rc, stdout, stderr = await ops_test.juju(
        "ssh", "--container", "grafana", unit_name, "cat", f"{received_cert_path}"
    )
    # Line ends have to be cleaned for comparison
    received_certs = stdout.replace("\r\n", "\n").rstrip()

    # Get trusted certs
    trusted_certs_path = "/etc/ssl/certs/ca-certificates.crt"
    rc, stdout, stderr = await ops_test.juju(
        "ssh", "--container", "grafana", unit_name, "cat", f"{trusted_certs_path}"
    )
    # Line ends have to be cleaned for comparison
    trusted_certs = stdout.replace("\r\n", "\n").rstrip()

    assert relation_certs == received_certs
    assert received_certs in trusted_certs


@pytest.mark.abort_on_fail
async def test_certs_available_after_refresh(ops_test: OpsTest, grafana_charm):
    """Make sure trusted certs are available after update."""
    assert ops_test.model
    await ops_test.model.applications["grafana"].refresh(path=grafana_charm)  # type: ignore
    await ops_test.model.wait_for_idle(
        status="active", raise_on_error=False, timeout=600, idle_period=30
    )
    await ops_test.model.wait_for_idle(status="active")
    await test_certs_created(ops_test)
