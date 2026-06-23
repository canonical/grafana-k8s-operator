#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import logging

import pytest

from helpers import check_grafana_is_ready, oci_image

logger = logging.getLogger(__name__)

GRAFANA_APP_NAME = "grafana"
SECRET_NAME = "smtp-config"
CONFIG_PATH = "/etc/grafana/grafana-config.ini"

grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
}



@pytest.fixture(scope="module")
async def smtp_secret(ops_test):
    """Create a Juju secret and grant it to the Grafana charm."""
    secret = await ops_test.model.add_secret(
        SECRET_NAME,
        ["password=my-smtp-password",],
    )
    await ops_test.model.grant_secret(SECRET_NAME, GRAFANA_APP_NAME)
    yield secret.split(":")[-1]


async def read_grafana_config(ops_test) -> str:
    """Read the Grafana config file from the workload container."""
    rc, stdout, stderr = await ops_test.juju(
        "ssh",
        "--container",
        "grafana",
        f"{GRAFANA_APP_NAME}/0",
        "cat",
        CONFIG_PATH,
    )
    assert rc == 0, f"Failed to read grafana config: {stderr}"
    return stdout

async def test_deploy_grafana(ops_test, grafana_charm):
    await ops_test.model.deploy(
        grafana_charm,
        resources=grafana_resources,
        application_name=GRAFANA_APP_NAME,
        trust=True,
    )
    await ops_test.model.wait_for_idle(
        apps=[GRAFANA_APP_NAME],
        status="active",
        timeout=1200,
        idle_period=30,
        raise_on_error=False,
    )


async def test_secret_url_is_resolved_in_config(ops_test, smtp_secret, tmp_path):
    """Verify that a secret:// URL in custom_config is replaced by the secret value."""
    # Create a local INI file and pass it using the @file syntax
    config_file = tmp_path / "smtp-config.ini"
    config_file.write_text(
        "[smtp]\n"
        "enabled = true\n"
        f"password = secret://{smtp_secret}/password\n"
    )
    await ops_test.model.applications[GRAFANA_APP_NAME].set_config(
        {"custom_config": f"@{config_file}"}
    )

    await ops_test.model.wait_for_idle(
        apps=[GRAFANA_APP_NAME],
        status="active",
        timeout=1200,
        idle_period=30,
        raise_on_error=True,
    )

    await check_grafana_is_ready(ops_test, GRAFANA_APP_NAME, 0)

    config = await read_grafana_config(ops_test)
    assert "secret://" not in config, "Secret URL was not resolved in grafana config"
    assert "my-smtp-password" in config, "Secret value not present in grafana config"


async def test_invalid_secret_url_blocks(ops_test):
    """Verify that an invalid secret:// URL causes the charm to block."""
    custom_config = "[smtp]\npassword = secret://bad-url\n"
    await ops_test.model.applications[GRAFANA_APP_NAME].set_config(
        {"custom_config": custom_config}
    )

    await ops_test.model.wait_for_idle(
        apps=[GRAFANA_APP_NAME],
        status="blocked",
        timeout=1200,
        idle_period=30,
        raise_on_error=False,
    )

    status = await ops_test.model.get_status()
    app = status["applications"][GRAFANA_APP_NAME]
    assert app["units"][f"{GRAFANA_APP_NAME}/0"]["workload-status"]["current"] == "blocked"
