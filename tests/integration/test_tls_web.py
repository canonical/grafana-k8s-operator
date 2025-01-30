#!/usr/bin/env python3
# Copyright 2023 Canonical
# See LICENSE file for licensing details.

import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from helpers import curl, oci_image, unit_address
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
grafana = SimpleNamespace(name="grafana", scale=2)
grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
    "litestream-image": oci_image("./charmcraft.yaml", "litestream-image"),
}


@pytest.mark.abort_on_fail
async def test_deploy(ops_test, grafana_charm):
    await asyncio.gather(
        ops_test.model.deploy(
            grafana_charm,
            resources=grafana_resources,
            application_name=grafana.name,
            num_units=2,
            trust=True,
        ),
        ops_test.model.deploy(
            "self-signed-certificates",
            application_name="ca",
            channel="edge",
        ),
    )
    await ops_test.model.add_relation(f"{grafana.name}:certificates", "ca")

    await asyncio.gather(
        ops_test.model.wait_for_idle(
            apps=[grafana.name],
            raise_on_error=False,
            timeout=1200,
            wait_for_exact_units=2,
        ),
        ops_test.model.wait_for_idle(
            apps=["ca"],
            raise_on_error=False,
            timeout=600,
        ),
    )


@pytest.mark.abort_on_fail
async def test_tls_files_created(ops_test: OpsTest):
    """Make sure charm code created web-config, cert and key files."""
    # juju ssh --container alertmanager am/0 ls /etc/alertmanager/
    config_path = "/etc/grafana/"
    for i in range(grafana.scale):
        unit_name = f"{grafana.name}/{i}"
        rc, stdout, stderr = await ops_test.juju(
            "ssh", "--container", "grafana", unit_name, "ls", f"{config_path}"
        )
        logger.info("%s: contents of %s: %s", unit_name, config_path, stdout or stderr)


@pytest.mark.abort_on_fail
async def test_server_cert(ops_test: OpsTest):
    """Inspect server cert and confirm `X509v3 Subject Alternative Name` field is as expected."""
    # echo \
    #   | openssl s_client -showcerts -servername $IPADDR:9093 -connect $IPADDR:9093 2>/dev/null \
    #   | openssl x509 -inform pem -noout -text
    for i in range(grafana.scale):
        grafana_ip = await unit_address(ops_test, grafana.name, i)
        cmd = [
            "sh",
            "-c",
            f"echo | openssl s_client -showcerts -servername {grafana_ip}:3000 -connect {grafana_ip}:3000 | openssl x509 -inform pem -noout -text",
        ]
        retcode, stdout, stderr = await ops_test.run(*cmd)
        fqdn = (
            f"{grafana.name}-{i}.{grafana.name}-endpoints.{ops_test.model_name}.svc.cluster.local"
        )
        assert fqdn in stdout, stderr


@pytest.mark.abort_on_fail
async def test_https_reachable(ops_test: OpsTest, temp_dir):
    """Make sure grafana's https endpoint is reachable using curl and ca cert."""
    assert ops_test.model
    await ops_test.model.wait_for_idle(
        status="active", raise_on_error=False, timeout=1200, idle_period=30
    )
    for i in range(grafana.scale):
        unit_name = f"{grafana.name}/{i}"
        # Save CA cert locally
        # juju show-unit grafana/0 | yq '.grafana/0."relation-info".[] | select (.endpoint=="certificates") | .application-data.[]' | jq '.[0].ca' -r
        cmd = [
            "sh",
            "-c",
            f"juju show-unit {unit_name} --format yaml | yq '.{unit_name}.\"relation-info\".[] | select (.endpoint==\"certificates\") | .application-data.[]' | jq '.[0].ca' -r",
        ]
        retcode, stdout, stderr = await ops_test.run(*cmd)
        cert = stdout
        cert_path = temp_dir / "local.cert"
        with open(cert_path, "wt") as f:
            f.writelines(cert)

        # Confirm alertmanager TLS endpoint reachable
        # curl --fail-with-body --capath /tmp --cacert /tmp/cacert.pem https://grafana.local:3000/-/ready
        fqdn = (
            f"{grafana.name}-{i}.{grafana.name}-endpoints.{ops_test.model_name}.svc.cluster.local"
        )
        response = await curl(
            ops_test,
            cert_dir=temp_dir,
            cert_path=cert_path,
            ip_addr=await unit_address(ops_test, grafana.name, i),
            mock_url=f"https://{fqdn}:3000/-/ready",
        )
        assert "Found" in response


@pytest.mark.abort_on_fail
async def test_https_still_reachable_after_refresh(ops_test: OpsTest, grafana_charm, temp_dir):
    """Make sure grafana's https endpoint is still reachable after an upgrade."""
    assert ops_test.model
    await ops_test.model.applications[grafana.name].refresh(path=grafana_charm)  # type: ignore
    await ops_test.model.wait_for_idle(
        status="active", raise_on_error=False, timeout=600, idle_period=30
    )
    await ops_test.model.wait_for_idle(status="active")
    await test_https_reachable(ops_test, temp_dir)
