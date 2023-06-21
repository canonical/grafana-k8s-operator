#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
import asyncio
import grp
import logging
import subprocess
from pathlib import Path
from typing import Tuple

import juju.utils
import yaml
from asyncstdlib import functools
from pytest_operator.plugin import OpsTest
from urllib.parse import urlparse
from workload import Grafana

logger = logging.getLogger(__name__)


async def block_until_leader_elected(ops_test: OpsTest, app_name: str):
    async def is_leader_elected():
        units = ops_test.model.applications[app_name].units
        return any([await units[i].is_leader_from_status() for i in range(len(units))])

    await juju.utils.block_until_with_coroutine(is_leader_elected)


@functools.cache
async def grafana_password(ops_test: OpsTest, app_name: str) -> str:
    """Get the admin password . Memoize it to reduce turnaround time.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of application

    Returns:
        admin password as a string
    """
    leader = None  # type: Unit
    for unit in ops_test.model.applications[app_name].units:
        is_leader = await unit.is_leader_from_status()
        if is_leader:
            leader = unit
            break

    action = await leader.run_action("get-admin-password")
    action = await action.wait()
    return action.results["admin-password"]


async def unit_address(ops_test: OpsTest, app_name: str, unit_num: int) -> str:
    """Find unit address for any application.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of application
        unit_num: integer number of a juju unit

    Returns:
        unit address as a string
    """
    status = await ops_test.model.get_status()
    return status["applications"][app_name]["units"]["{}/{}".format(app_name, unit_num)]["address"]


async def check_grafana_is_ready(ops_test: OpsTest, app_name: str, unit_num: int) -> bool:
    """Check if Grafana server is up with good database status.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of Grafana application
        unit_num: integer number of a Grafana juju unit

    Returns:
        True if Grafana is responsive else False
    """
    host = await unit_address(ops_test, app_name, unit_num)
    pw = await grafana_password(ops_test, app_name)
    grafana = Grafana(host=host, pw=pw)
    is_ready = await grafana.is_ready()
    assert is_ready
    return is_ready


async def get_grafana_settings(ops_test: OpsTest, app_name: str, unit_num: int) -> dict:
    """Fetch Grafana settings.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of Grafana application
        unit_num: integer number of a Grafana juju unit

    Returns:
        Grafana YAML configuration in string format.
    """
    host = await unit_address(ops_test, app_name, unit_num)
    pw = await grafana_password(ops_test, app_name)
    grafana = Grafana(host=host, pw=pw)
    grafana = Grafana(host=host)
    settings = await grafana.settings()
    return settings


async def get_grafana_health(ops_test: OpsTest, app_name: str, unit_num: int) -> dict:
    """Fetch Grafana health data.

    Returns:
        Empty :dict: if it is not up, otherwise a dict containing basic API health
    """
    host = await unit_address(ops_test, app_name, unit_num)
    pw = await grafana_password(ops_test, app_name)
    grafana = Grafana(host=host, pw=pw)
    grafana = Grafana(host=host)
    health = await grafana.health()
    return health


async def get_grafana_datasources(ops_test: OpsTest, app_name: str, unit_num: int) -> list:
    """Fetch all Grafana rules.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of Grafana application
        unit_num: integer number of a Grafana juju unit

    Returns:
        a list of datasources
    """
    host = await unit_address(ops_test, app_name, unit_num)
    pw = await grafana_password(ops_test, app_name)
    grafana = Grafana(host=host, pw=pw)
    datasources = await grafana.datasources()
    return datasources


def get_datasource_for(suffix: str, datasources: list) -> dict:
    """Extract a single datasource from the list of all.

    Args:
        suffix: a string representing the app name in the config
        datasources: a list of datasources
    Returns:
        a datasource config dict
    """
    assert datasources, "'datasources' argument cannot be empty"

    datasource_filtered = [d for d in datasources if d["name"].endswith(suffix)]
    if not datasource_filtered:
        raise ValueError("No data source was found for suffix {}".format(suffix))

    return datasource_filtered.pop()


async def get_grafana_dashboards(ops_test: OpsTest, app_name: str, unit_num: int) -> list:
    """Find a dashboard by searching.

    This method finds a dashboard through the search API. It isn't
    possible to return the JSON for all dashboards, so we need to
    look through a query and fetch them.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of Grafana application
        unit_num: integer number of a Juju unit

    Returns:
        a list of dashboards
    """
    host = await unit_address(ops_test, app_name, unit_num)
    pw = await grafana_password(ops_test, app_name)
    grafana = Grafana(host=host, pw=pw)
    dashboards = await grafana.dashboards_all()
    return dashboards


async def get_dashboard_by_search(
    ops_test: OpsTest, app_name: str, unit_num: int, query_string: str
) -> dict:
    """Find a dashboard by searching.

    This method finds a dashboard through the search API. It isn't
    possible to return the JSON for all dashboards, so we need to
    look through a query and fetch them.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of Grafana application
        unit_num: integer number of a Juju unit
        query_string: the search string to use

    Returns:
        a dashboard as a dict
    """
    host = await unit_address(ops_test, app_name, unit_num)
    pw = await grafana_password(ops_test, app_name)
    grafana = Grafana(host=host, pw=pw)
    dashboards = await grafana.dashboard_search(query_string)

    dashboard_json = await grafana.fetch_dashboard(dashboards[0]["uid"])
    return dashboard_json


def oci_image(metadata_file: str, image_name: str) -> str:
    """Find upstream source for a container image.

    Args:
        metadata_file: string path of metadata YAML file relative
            to top level charm directory
        image_name: OCI container image string name as defined in
            metadata.yaml file

    Returns:
        upstream image source

    Raises:
        FileNotFoundError: if metadata_file path is invalid
        ValueError: if upstream source for image name can not be found
    """
    metadata = yaml.safe_load(Path(metadata_file).read_text())

    resources = metadata.get("resources", {})
    if not resources:
        raise ValueError("No resources found")

    image = resources.get(image_name, {})
    if not image:
        raise ValueError("{} image not found".format(image_name))

    upstream_source = image.get("upstream-source", "")
    if not upstream_source:
        raise ValueError("Upstream source not found")

    return upstream_source


async def get_config_values(ops_test, app_name) -> dict:
    """Return the app's config, but filter out keys that do not have a value."""
    config = await ops_test.model.applications[app_name].get_config()
    return {key: str(config[key]["value"]) for key in config if "value" in config[key]}


async def get_grafana_environment_variable(
    ops_test: OpsTest, app_name: str, container_name: str, env_var: str
) -> Tuple[str, str, str]:
    # tear the actual value out of /proc since it's an env variable for the process itself
    rc, stdout, stderr = await ops_test.juju(
        "ssh",
        "--container",
        f"{container_name}",
        f"{app_name}/0",
        "xargs",
        "-0",
        "-L1",
        "-a",
        "/proc/$(pgrep grafana)/environ",
        "echo",
        f"${env_var}",
    )

    # If we do find one, split it into parts around `foo=bar` and return the value
    value = next(iter([env for env in stdout.splitlines() if env_var in env])).split("=")[-1] or ""
    return rc, value, stderr.strip


def uk8s_group() -> str:
    try:
        # Classically confined microk8s
        uk8s_group = grp.getgrnam("microk8s").gr_name
    except KeyError:
        # Strictly confined microk8s
        uk8s_group = "snap_microk8s"
    return uk8s_group


async def reenable_metallb() -> str:
    # Set up microk8s metallb addon, needed by traefik
    logger.info("(Re)-enabling metallb")
    cmd = [
        "sh",
        "-c",
        "ip -4 -j route get 2.2.2.2 | jq -r '.[] | .prefsrc'",
    ]
    result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    ip = result.stdout.decode("utf-8").strip()

    logger.info("First, disable metallb, just in case")
    try:
        cmd = ["sg", uk8s_group(), "-c", "microk8s disable metallb"]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as e:
        print(e)
        raise

    await asyncio.sleep(30)  # why? just because, for now

    logger.info("Now enable metallb")
    try:
        cmd = ["sg", uk8s_group(), "-c", f"microk8s enable metallb:{ip}-{ip}"]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as e:
        print(e)
        raise

    await asyncio.sleep(30)  # why? just because, for now
    return ip


async def deploy_literal_bundle(ops_test: OpsTest, bundle: str):
    run_args = [
        "juju",
        "deploy",
        "--trust",
        "-m",
        ops_test.model_name,
        str(ops_test.render_bundle(bundle)),
    ]

    retcode, stdout, stderr = await ops_test.run(*run_args)
    assert retcode == 0, f"Deploy failed: {(stderr or stdout).strip()}"
    logger.info(stdout)


async def curl(ops_test: OpsTest, *, cert_dir: str, cert_path: str, ip_addr: str, mock_url: str):
    p = urlparse(mock_url)

    # Tell curl to resolve the mock url as traefik's IP (to avoid using a custom DNS
    # server). This is needed because the certificate issued by the CA would have that same
    # hostname as the subject, and for TLS to succeed, the target url's hostname must match
    # the one in the certificate.
    rc, stdout, stderr = await ops_test.run(
        "curl",
        "-s",
        "--fail-with-body",
        "--resolve",
        f"{p.hostname}:{p.port or 443}:{ip_addr}",
        "--capath",
        cert_dir,
        "--cacert",
        cert_path,
        mock_url,
    )
    logger.info("%s: %s", mock_url, (rc, stdout, stderr))
    assert rc == 0, (
        f"curl exited with rc={rc} for {mock_url}; "
        "non-zero return code means curl encountered a >= 400 HTTP code"
    )
    return stdout


class ModelConfigChange:
    """Context manager for temporarily changing a model config option."""

    def __init__(self, ops_test: OpsTest, config: dict):
        self.ops_test = ops_test
        self.change_to = config.copy()

    async def __aenter__(self):
        """On entry, the config is set to the user provided custom values."""
        config = await self.ops_test.model.get_config()
        self.revert_to = {k: config[k] for k in self.change_to.keys()}
        await self.ops_test.model.set_config(self.change_to)
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        """On exit, the modified config options are reverted to their original values."""
        await self.ops_test.model.set_config(self.revert_to)
