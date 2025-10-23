#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
import json
import logging
from pathlib import Path
from typing import Optional, Tuple

import requests
import yaml
from asyncstdlib import functools
from pytest_operator.plugin import OpsTest
from urllib.parse import urlparse
from workload import Grafana
from juju.unit import Unit
from tenacity import retry, stop_after_attempt, wait_exponential, wait_fixed

logger = logging.getLogger(__name__)


@functools.cache
async def grafana_password(ops_test: OpsTest, app_name: str) -> str:
    """Get the admin password . Memoize it to reduce turnaround time.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of application

    Returns:
        admin password as a string
    """
    leader: Optional[Unit] = None
    for unit in ops_test.model.applications[app_name].units:  # type: ignore
        is_leader = await unit.is_leader_from_status()
        if is_leader:
            leader = unit
            break

    assert leader
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
    assert ops_test.model
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


async def create_org(ops_test: OpsTest, app_name: str, unit_num: int, org_name: str) -> dict:
    """Create Organisation.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of Grafana application
        unit_num: integer number of a Grafana juju unit
        org_name: string name of Org.

    Returns:
        Oranisation created.
    """
    host = await unit_address(ops_test, app_name, unit_num)
    pw = await grafana_password(ops_test, app_name)
    grafana = Grafana(host=host, pw=pw)
    org = await grafana.create_org(name=org_name)
    return org


async def get_org(ops_test: OpsTest, app_name: str, unit_num: int, org_name: str) -> dict:
    """Fetch Organisation.

    Args:
        ops_test: pytest-operator plugin
        app_name: string name of Grafana application
        unit_num: integer number of a Grafana juju unit
        org_name: string name of Org.

    Returns:
        Oranisation.
    """
    host = await unit_address(ops_test, app_name, unit_num)
    pw = await grafana_password(ops_test, app_name)
    grafana = Grafana(host=host, pw=pw)
    org = await grafana.fetch_org(name=org_name)
    return org


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
    return str(rc), value, stderr.strip()


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


def get_traces(tempo_host: str, service_name="tracegen-otlp_http", tls=True):
    """Get traces directly from Tempo REST API."""
    url = f"{'https' if tls else 'http'}://{tempo_host}:3200/api/search?tags=service.name={service_name}"
    req = requests.get(
        url,
        verify=False,
    )
    assert req.status_code == 200
    traces = json.loads(req.text)["traces"]
    return traces


@retry(stop=stop_after_attempt(15), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_traces_patiently(tempo_host, service_name="tracegen-otlp_http", tls=True):
    """Get traces directly from Tempo REST API, but also try multiple times.

    Useful for cases when Tempo might not return the traces immediately (its API is known for returning data in
    random order).
    """
    traces = get_traces(tempo_host, service_name=service_name, tls=tls)
    assert len(traces) > 0
    return traces


async def get_application_ip(ops_test: OpsTest, app_name: str) -> str:
    """Get the application IP address."""
    assert ops_test.model
    status = await ops_test.model.get_status()
    app = status["applications"][app_name]
    return app.public_address

async def get_traefik_url(ops_test: OpsTest, traefik_app_name: str = "traefik"):
    """Get the URL for the Traefik app, as provided by the show-external-endpoints action."""
    assert ops_test.model, "ops_test.model is not initialized"
    
    app = ops_test.model.applications.get(traefik_app_name)
    assert app
    assert app.units

    external_endpoints_action = await app.units[0].run_action("show-external-endpoints")
    external_endpoints_action_results = (await external_endpoints_action.wait()).results
    external_endpoints = yaml.safe_load(external_endpoints_action_results["external-endpoints"])
    return external_endpoints[traefik_app_name]["url"]

@retry(
    wait=wait_fixed(15),
    stop=stop_after_attempt(10),
)
def fetch_with_retry(url: str, expected_status: int, follow_redirects: bool = True) -> requests.Response:
    response = requests.get(url, verify=False, allow_redirects=follow_redirects)
    if response.status_code != expected_status:
        raise AssertionError(f"Expected status {expected_status}, got {response.status_code}")
    return response

class ModelConfigChange:
    """Context manager for temporarily changing a model config option."""

    def __init__(self, ops_test: OpsTest, config: dict):
        self.ops_test = ops_test
        self.change_to = config.copy()

    async def __aenter__(self):
        """On entry, the config is set to the user provided custom values."""
        assert self.ops_test.model
        config = await self.ops_test.model.get_config()
        self.revert_to = {k: config[k] for k in self.change_to.keys()}
        await self.ops_test.model.set_config(self.change_to)
        return self

    async def __aexit__(self, exc_type, exc_value, exc_traceback):
        """On exit, the modified config options are reverted to their original values."""
        assert self.ops_test.model
        await self.ops_test.model.set_config(self.revert_to)
