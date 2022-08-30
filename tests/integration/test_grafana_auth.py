#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests the library using dummy requirer and provider charms.

It tests that the charms are able to relate and to exchange data.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import pytest
import yaml

logger = logging.getLogger(__name__)

PROVIDER_METADATA = yaml.safe_load(
    Path("tests/integration/auth-provider-tester/metadata.yaml").read_text()
)
REQUIRER_METADATA = yaml.safe_load(
    Path("tests/integration/grafana-tester/metadata.yaml").read_text()
)
PROVIDER_CHARM_NAME = PROVIDER_METADATA["name"]
REQUIRER_CHARM_NAME = REQUIRER_METADATA["name"]
DEPLOY_TIMEOUT = 1000
PROVIDER_APPLICATION_NAME = "auth-provider-tester"
REQUIRER_APPLICATION_NAME = "grafana-tester"


class TestAuthLib:
    @pytest.fixture(scope="module")
    @pytest.mark.abort_on_fail
    async def setup(self, ops_test):
        await self._deploy_provider(ops_test)
        await self._deploy_requirer(ops_test)

    def _find_charm(self, charm_dir: str, charm_file_name: str) -> Optional[str]:
        for root, _, files in os.walk(charm_dir):
            for file in files:
                if file == charm_file_name:
                    return os.path.join(root, file)
        return None

    async def _deploy_provider(self, ops_test):
        provider_charm = self._find_charm(
            "tests/integration/auth-provider-tester/", PROVIDER_CHARM_NAME
        )
        if not provider_charm:
            provider_charm = await ops_test.build_charm("tests/integration/auth-provider-tester/")
        resources = {
            f"{PROVIDER_CHARM_NAME}-image": PROVIDER_METADATA["resources"][
                f"{PROVIDER_CHARM_NAME}-image"
            ]["upstream-source"],
        }
        await ops_test.model.deploy(
            provider_charm,
            resources=resources,
            application_name=PROVIDER_APPLICATION_NAME,
            trust=True,
        )
        await ops_test.model.wait_for_idle(
            apps=[PROVIDER_APPLICATION_NAME], status="active", timeout=1000
        )

    async def _deploy_requirer(self, ops_test):
        requirer_charm = self._find_charm("tests/integration/grafana-tester/", REQUIRER_CHARM_NAME)
        if not requirer_charm:
            requirer_charm = await ops_test.build_charm("tests/integration/grafana-tester/")
        resources = {
            f"{REQUIRER_CHARM_NAME}-image": REQUIRER_METADATA["resources"][
                f"{REQUIRER_CHARM_NAME}-image"
            ]["upstream-source"],
        }
        await ops_test.model.deploy(
            requirer_charm,
            resources=resources,
            application_name=REQUIRER_APPLICATION_NAME,
            trust=True,
        )

    async def test_relate_and_wait_for_idle(self, ops_test, setup):
        await ops_test.model.add_relation(
            relation1=REQUIRER_APPLICATION_NAME, relation2=PROVIDER_APPLICATION_NAME
        )
        await ops_test.model.wait_for_idle(
            apps=[REQUIRER_APPLICATION_NAME], status="active", timeout=1000
        )
