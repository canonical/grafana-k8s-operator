#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests the oauth library using the Canonical Identity Stack.

It tests that the grafana charm can provide Single Sign-On Services to users
with the oauth integration.
"""

import logging
from pathlib import Path
from helpers import oci_image

import os
import pytest
import requests
from playwright.async_api._generated import Page, BrowserContext
from pytest_operator.plugin import OpsTest

from oauth_tools import (
    deploy_identity_bundle,
    get_reverse_proxy_app_url,
    complete_auth_code_login,
    access_application_login_page,
    click_on_sign_in_button_by_text,
    verify_page_loads,
    get_cookie_from_browser_by_name,
    ExternalIdpService,
)

pytest_plugins = ["oauth_tools.fixtures"]
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


async def test_build_and_deploy(
    ops_test: OpsTest,
    grafana_charm: Path,
    hydra_app_name: str,
    public_traefik_app_name: str,
    self_signed_certificates_app_name: str,
    ext_idp_service: ExternalIdpService,
):
    # Instantiating the ExternalIdpManager object deploys the external identity provider.

    await deploy_identity_bundle(
        ops_test=ops_test, bundle_channel="0.2/edge", ext_idp_service=ext_idp_service
    )

    # Deploy grafana
    await ops_test.model.deploy(
        grafana_charm,
        resources=grafana_resources,
        application_name="grafana",
        trust=True,
    )

    # Integrate grafana with the identity bundle
    await ops_test.model.integrate("grafana:oauth", hydra_app_name)
    await ops_test.model.integrate("grafana:ingress", public_traefik_app_name)
    await ops_test.model.integrate("grafana:receive-ca-cert", self_signed_certificates_app_name)

    await ops_test.model.wait_for_idle(
        apps=[
            hydra_app_name,
            public_traefik_app_name,
            self_signed_certificates_app_name,
            "grafana",
        ],
        status="active",
        raise_on_blocked=False,
        raise_on_error=False,
        timeout=1000,
    )


@pytest.mark.skip(reason="This test file started failing on timeout and blocks our releases")
async def test_oauth_login_with_identity_bundle(
    ops_test: OpsTest,
    page: Page,
    context: BrowserContext,
    public_traefik_app_name: str,
    user_email: str,
    ext_idp_service: ExternalIdpService,
) -> None:
    grafana_proxy = await get_reverse_proxy_app_url(ops_test, public_traefik_app_name, "grafana")
    redirect_login = os.path.join(grafana_proxy, "login")

    await access_application_login_page(
        page=page, url=grafana_proxy, redirect_login_url=redirect_login
    )

    await click_on_sign_in_button_by_text(
        page=page, text="Sign in with external identity provider"
    )

    await complete_auth_code_login(page=page, ops_test=ops_test, ext_idp_service=ext_idp_service)

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
    assert request.json()["email"] == user_email
