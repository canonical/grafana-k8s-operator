#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
from pathlib import Path

import yaml
from asyncstdlib import functools
from juju.unit import Unit
from pytest_operator.plugin import OpsTest
from workload import Grafana


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
        app_name: string name of Grafana application

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
        app_name: string name of Grafana application
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
    return {key: config[key]["value"] for key in config if "value" in config[key]}


async def get_grafana_environment_variable(
    ops_test: OpsTest, app_name: str, container_name: str, env_var: str
) -> str:
    rc, stdout, stderr = await ops_test.juju(
        "ssh", "--container", f"{container_name}", f"{app_name}/0", "echo", f"${env_var}"
    )
    return rc, stdout, stderr
