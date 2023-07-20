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

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
grafana = SimpleNamespace(name="grafana", scale=2, hostname="grafana.local")
grafana_resources = {
    "grafana-image": oci_image("./metadata.yaml", "grafana-image"),
    "litestream-image": oci_image("./metadata.yaml", "litestream-image"),
}


@pytest.mark.xfail
async def test_deploy(ops_test, grafana_charm):
    await asyncio.gather(
        ops_test.model.deploy(
            grafana_charm,
            resources=grafana_resources,
            application_name=grafana.name,
            num_units=2,
            trust=True,
            config={"web_external_url": f"http://{grafana.hostname}"},
        ),
        ops_test.model.deploy(
            "ch:self-signed-certificates",
            application_name="ca",
            channel="edge",
        ),
    )
    await ops_test.model.add_relation(f"{grafana.name}:certificates", "ca")

    await asyncio.gather(
        ops_test.model.wait_for_idle(
            apps=[grafana.name],
            wait_for_units=2,
            raise_on_error=False,
            timeout=1200,
        ),
        ops_test.model.wait_for_idle(
            apps=["ca"],
            wait_for_units=1,
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
    grafana_ip_addrs = [
        await unit_address(ops_test, grafana.name, i) for i in range(grafana.scale)
    ]
    for grafana_ip in grafana_ip_addrs:
        cmd = [
            "sh",
            "-c",
            f"echo | openssl s_client -showcerts -servername {grafana_ip}:3000 -connect {grafana_ip}:3000 2>/dev/null | openssl x509 -inform pem -noout -text",
        ]
        retcode, stdout, stderr = await ops_test.run(*cmd)
        assert grafana.hostname in stdout


@pytest.mark.abort_on_fail
async def test_https_reachable(ops_test: OpsTest, temp_dir):
    """Make sure grafana's https endpoint is reachable using curl and ca cert."""
    await ops_test.model.wait_for_idle(
        status="active", raise_on_error=False, timeout=1200, idle_period=30
    )
    for i in range(grafana.scale):
        unit_name = f"{grafana.name}/{i}"
        # Save CA cert locally
        # juju show-unit grafana/0 --format yaml | yq '.grafana/0."relation-info"[0]."local-unit".data.ca' > /tmp/cacert.pem
        cmd = [
            "sh",
            "-c",
            f'juju show-unit {unit_name} --format yaml | yq \'.{unit_name}."relation-info"[1]."local-unit".data.ca\'',
        ]
        retcode, stdout, stderr = await ops_test.run(*cmd)
        cert = stdout
        cert_path = temp_dir / "local.cert"
        with open(cert_path, "wt") as f:
            f.writelines(cert)

        # Confirm alertmanager TLS endpoint reachable
        # curl --fail-with-body --capath /tmp --cacert /tmp/cacert.pem https://grafana.local:3000/-/ready
        response = await curl(
            ops_test,
            cert_dir=temp_dir,
            cert_path=cert_path,
            ip_addr=await unit_address(ops_test, grafana.name, i),
            mock_url=f"https://{grafana.hostname}:3000/-/ready",
        )
        assert "Found" in response


@pytest.mark.abort_on_fail
async def test_https_still_reachable_after_refresh(ops_test: OpsTest, grafana_charm, temp_dir):
    """Make sure grafana's https endpoint is still reachable after an upgrade."""
    await ops_test.model.applications[grafana.name].refresh(path=grafana_charm)
    await ops_test.model.wait_for_idle(
        status="active", raise_on_error=False, timeout=600, idle_period=30
    )
    await ops_test.model.wait_for_idle(status="active")
    await test_https_reachable(ops_test, temp_dir)
