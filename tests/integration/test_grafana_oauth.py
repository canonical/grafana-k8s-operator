#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests the oauth library using the Canonical Identity Stack.

It tests that the grafana charm can provide Single Sign-On Services to users
with the oauth integration.
"""

import logging
from helpers import oci_image

import os
import pytest
import requests
from playwright.async_api._generated import Page, BrowserContext
from pytest_operator.plugin import OpsTest

from oauth_tools.dex import ExternalIdpManager
from oauth_tools.oauth_test_helper import (
    deploy_identity_bundle,
    get_reverse_proxy_app_url,
    complete_external_idp_login,
    access_application_login_page,
    click_on_sign_in_button_by_text,
    verify_page_loads,
    get_cookie_from_browser_by_name,
)
from oauth_tools.conftest import *  # noqa
from oauth_tools.constants import EXTERNAL_USER_EMAIL, APPS

logger = logging.getLogger(__name__)

tester_resources = {
    "grafana-tester-image": oci_image(
        "./tests/integration/grafana-tester/metadata.yaml", "grafana-tester-image"
    )
}
grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
    "litestream-image": oci_image("./charmcraft.yaml", "litestream-image"),
}


@pytest.mark.skip_if_deployed
@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest, grafana_charm):
    # Instantiating the ExternalIdpManager object deploys the external identity provider.
    external_idp_manager = ExternalIdpManager(ops_test=ops_test)

    await deploy_identity_bundle(ops_test=ops_test, external_idp_manager=external_idp_manager)

    # Deploy grafana
    await ops_test.model.deploy(
        grafana_charm,
        resources=grafana_resources,
        application_name="grafana",
        trust=True,
    )

    # Integrate grafana with the identity bundle
    await ops_test.model.integrate("grafana:oauth", APPS.HYDRA)
    await ops_test.model.integrate("grafana:ingress", APPS.TRAEFIK_PUBLIC)
    await ops_test.model.integrate("grafana:receive-ca-cert", APPS.SELF_SIGNED_CERTIFICATES)

    await ops_test.model.wait_for_idle(
        apps=[
            APPS.HYDRA,
            APPS.TRAEFIK_PUBLIC,
            APPS.SELF_SIGNED_CERTIFICATES,
            "grafana",
        ],
        status="active",
        raise_on_blocked=False,
        raise_on_error=False,
        timeout=1000,
    )


async def test_oauth_login_with_identity_bundle(
    ops_test: OpsTest, page: Page, context: BrowserContext
) -> None:
    external_idp_manager = ExternalIdpManager(ops_test=ops_test)

    grafana_proxy = await get_reverse_proxy_app_url(ops_test, APPS.TRAEFIK_PUBLIC, "grafana")
    redirect_login = os.path.join(grafana_proxy, "login")

    await access_application_login_page(
        page=page, url=grafana_proxy, redirect_login_url=redirect_login
    )

    await click_on_sign_in_button_by_text(
        page=page, text="Sign in with external identity provider"
    )

    await complete_external_idp_login(
        page=page, ops_test=ops_test, external_idp_manager=external_idp_manager
    )

    redirect_url = os.path.join(grafana_proxy, "?*")
    await verify_page_loads(page=page, url=redirect_url)

    # Verifying that the login flow was successful is application specific.
    # The test uses Grafana's /api/user endpoint to verify the session cookie is valid
    grafana_session_cookie = await get_cookie_from_browser_by_name(
        browser_context=context, name="grafana_session"
    )
    request = requests.get(
        os.path.join(grafana_proxy, "api/user"),
        headers={"Cookie": f"grafana_session={grafana_session_cookie}"},
        verify=False,
    )
    assert request.status_code == 200
    assert request.json()["email"] == EXTERNAL_USER_EMAIL

    external_idp_manager.remove_idp_service()
