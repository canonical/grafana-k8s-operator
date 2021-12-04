#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
import shutil
from pathlib import Path

import pytest
from pytest_operator.plugin import OpsTest


@pytest.fixture(scope="module", autouse=True)
def copy_grafana_libraries_into_tester_charm(ops_test: OpsTest) -> None:
    """Ensure that the tester charm uses the current Grafana libraries."""
    libs = [
        Path("lib/charms/grafana_k8s/v0/", lib)
        for lib in ["grafana_dashboard.py", "grafana_source.py"]
    ]
    for lib in libs:
        Path("tests/integration/grafana-tester", lib.parent).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            lib.as_posix(), "tests/integration/grafana-tester/{}".format(lib.as_posix())
        )


@pytest.fixture(scope="module")
async def grafana_charm(ops_test: OpsTest) -> Path:
    """Grafana charm used for integration testing."""
    charm = await ops_test.build_charm(".")
    return charm


@pytest.fixture(scope="module")
async def grafana_tester_charm(ops_test: OpsTest) -> Path:
    """A charm to integration test the Grafana charm."""
    charm_path = "tests/integration/grafana-tester"
    charm = await ops_test.build_charm(charm_path)
    return charm
