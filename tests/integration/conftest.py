#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
import functools
import logging
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pytest
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


class Store(defaultdict):
    def __init__(self):
        super(Store, self).__init__(Store)

    def __getattr__(self, key):
        """Override __getattr__ so dot syntax works on keys."""
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        """Override __setattr__ so dot syntax works on keys."""
        self[key] = value


store = Store()


def timed_memoizer(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        fname = func.__qualname__
        logger.info("Started: %s" % fname)
        start_time = datetime.now()
        if fname in store.keys():
            ret = store[fname]
        else:
            logger.info("Return for {} not cached".format(fname))
            ret = await func(*args, **kwargs)
            store[fname] = ret
        logger.info("Finished: {} in: {} seconds".format(fname, datetime.now() - start_time))
        return ret

    return wrapper


@pytest.fixture(scope="module", autouse=True)
def copy_grafana_libraries_into_tester_charm(ops_test: OpsTest) -> None:
    """Ensure that the tester charm uses the current Grafana libraries."""
    libs = [
        Path("lib/charms/", lib)
        for lib in [
            "observability_libs/v0/juju_topology.py",
            "grafana_k8s/v0/grafana_dashboard.py",
            "grafana_k8s/v0/grafana_source.py",
            "grafana_k8s/v0/grafana_auth.py",
        ]
    ]
    for lib in libs:
        Path("tests/integration/grafana-tester", lib.parent).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            lib.as_posix(), "tests/integration/grafana-tester/{}".format(lib.as_posix())
        )


@pytest.fixture(scope="module")
@timed_memoizer
async def grafana_charm(ops_test: OpsTest) -> Path:
    """Grafana charm used for integration testing."""
    charm = await ops_test.build_charm(".")
    return charm


@pytest.fixture(scope="module")
@timed_memoizer
async def grafana_tester_charm(ops_test: OpsTest) -> Path:
    """A charm to integration test the Grafana charm."""
    charm_path = "tests/integration/grafana-tester"
    charm = await ops_test.build_charm(charm_path)
    return charm


@pytest.fixture(scope="module")
def temp_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("data")
