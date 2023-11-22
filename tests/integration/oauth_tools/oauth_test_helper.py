#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
from os.path import join
import re
from typing import Dict, List, Optional

from playwright.async_api._generated import BrowserContext, Page
from playwright.async_api import expect
from pytest_operator.plugin import OpsTest

from oauth_tools.dex import ExternalIdpManager
from oauth_tools.constants import (
    APPS,
    OAUTH_RELATION,
    IDENTITY_BUNDLE,
    EXTERNAL_USER_EMAIL,
    EXTERNAL_USER_PASSWORD,
    DEX_CLIENT_ID,
    DEX_CLIENT_SECRET,
)

logger = logging.getLogger(__name__)


async def get_reverse_proxy_app_url(
    ops_test: OpsTest, ingress_app_name: str, app_name: str
) -> str:
    """Get the address of a proxied application."""
    status = await ops_test.model.get_status()  # noqa: F821
    address = status["applications"][ingress_app_name]["public-address"]
    return f"https://{address}/{ops_test.model.name}-{app_name}/"


async def deploy_identity_bundle(ops_test: OpsTest, external_idp_manager: ExternalIdpManager):
    """Convenience function for deploying and configuring the identity bundle."""
    await ops_test.model.deploy(
        IDENTITY_BUNDLE.NAME,
        channel=IDENTITY_BUNDLE.CHANNEL,
        trust=True,
    )

    await ops_test.model.applications[APPS.KRATOS_EXTERNAL_IDP_INTEGRATOR].set_config(
        {
            "client_id": DEX_CLIENT_ID,
            "client_secret": DEX_CLIENT_SECRET,
            "provider": "generic",
            "issuer_url": external_idp_manager.idp_service_url,
            "scope": "profile email",
            "provider_id": "Dex",
        }
    )

    await ops_test.model.wait_for_idle(
        raise_on_blocked=False,
        status="active",
        timeout=2000,
    )

    get_redirect_uri_action = (
        await ops_test.model.applications[APPS.KRATOS_EXTERNAL_IDP_INTEGRATOR]
        .units[0]
        .run_action("get-redirect-uri")
    )

    action_output = await get_redirect_uri_action.wait()
    assert "redirect-uri" in action_output.results

    external_idp_manager.update_redirect_uri(redirect_uri=action_output.results["redirect-uri"])


async def access_application_login_page(page: Page, url: str, redirect_login_url: str = ""):
    """Convenience function for navigating the browser to the login page."""
    """
    Usage:
        If the url of the application redirects to a login page, pass the application's url as url,
        and a pattern string for the login page as redirect_login_url.

        Otherwise pass the url of the application's login page as url, and leave redirect_login_url
        empty.
    """
    await page.goto(url)
    if redirect_login_url:
        await expect(page).to_have_url(re.compile(rf"{redirect_login_url}*"))


async def click_on_sign_in_button_by_text(page: Page, text: str):
    """Convenience function for retrieving the Oauth Sign In button by its displayed text."""
    async with page.expect_navigation():
        await page.get_by_text(text).click()


async def click_on_sign_in_button_by_alt_text(page: Page, alt_text: str):
    """Convenience function for retrieving the Oauth Sign In button by the alt text."""
    async with page.expect_navigation():
        await page.get_by_alt_text(alt_text).click()


async def complete_external_idp_login(
    page: Page, ops_test: OpsTest, external_idp_manager: ExternalIdpManager
) -> None:
    """Convenience function for navigating the external identity provider's user interface."""
    expected_url = join(
        await get_reverse_proxy_app_url(
            ops_test, OAUTH_RELATION.OAUTH_PROXY, APPS.IDENTITY_PLATFORM_LOGIN_UI_OPERATOR
        ),
        "ui/login",
    )
    await expect(page).to_have_url(re.compile(rf"{expected_url}*"))
    async with page.expect_navigation():
        await page.get_by_role("button", name="Dex").click()

    await expect(page).to_have_url(re.compile(rf"{external_idp_manager.idp_service_url}*"))
    await page.get_by_placeholder("email address").click()
    await page.get_by_placeholder("email address").fill(EXTERNAL_USER_EMAIL)
    await page.get_by_placeholder("password").click()
    await page.get_by_placeholder("password").fill(EXTERNAL_USER_PASSWORD)
    await page.get_by_role("button", name="Login").click()


async def verify_page_loads(page: Page, url: str):
    """Convenience function for verifying that the correct url has been loaded."""
    await page.wait_for_url(url)


async def get_cookie_from_browser_by_name(
    browser_context: BrowserContext, name: str
) -> Optional[str]:
    """Convenience function for retrieving a cookie."""
    cookies = await browser_context.cookies()
    for cookie in cookies:
        if cookie["name"] == name:
            return cookie["value"]
    return None


async def get_cookies_from_browser_by_url(browser_context: BrowserContext, url: str) -> List[Dict]:
    """Convenience function for retrieving cookies belonging to a domain."""
    # see structure of returned dictionaries at https://playwright.dev/docs/api/class-browsercontext#browser-context-cookies
    cookies = await browser_context.cookies(url)
    return cookies
