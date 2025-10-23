#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pyright: reportAttributeAccessIssue = false
import asyncio
import logging

import pytest
from helpers import oci_image, get_traefik_url, fetch_with_retry
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

grafana_resources = {
    "grafana-image": oci_image("./charmcraft.yaml", "grafana-image"),
    "litestream-image": oci_image("./charmcraft.yaml", "litestream-image"),
}

grafana_app_name = "grafana"
traefik_app_name = "traefik"
ssc_app_name = "self-signed-certificates"
idle_period = 90

@pytest.mark.abort_on_fail
async def test_deploy(ops_test, grafana_charm):
    await asyncio.gather(
        ops_test.model.deploy(
            grafana_charm,
            resources=grafana_resources,
            application_name=grafana_app_name,
            trust=True,
        ),
        ops_test.model.deploy(
            "ch:traefik-k8s",
            application_name=traefik_app_name,
            channel="edge",
            trust=True,
        ),
        ops_test.model.deploy(
            "ch:self-signed-certificates",
            application_name=ssc_app_name,
            #channel="latest/stable",
            trust=True,
        ),
    )

    # Relate Grafana and Traefik - this will be using traefik route.
    await ops_test.model.add_relation(f"{grafana_app_name}:ingress", traefik_app_name)

    await asyncio.gather(
        ops_test.model.wait_for_idle(
            apps=[grafana_app_name, traefik_app_name, ssc_app_name],
            timeout=600,
        ),
    )

@pytest.mark.abort_on_fail
async def test_no_tls(ops_test):
    """Test whether we are able to reach Grafana via Traefik when using no TLS.

    This means that both Traefik and Grafana are only using HTTP.
    """
    traefik_address = await get_traefik_url(ops_test, traefik_app_name=traefik_app_name)

    assert "http://" in traefik_address

    grafana_address = f"{traefik_address}/{ops_test.model.info.name}-{grafana_app_name}"
    # We expect a 200 response now
    fetch_with_retry(url=grafana_address, expected_status=200)

@pytest.mark.abort_on_fail
async def test_internal_and_full_tls(ops_test):
    """Test whether we are able to reach Grafana via Traefik when using internal TLS.

    This means that Traefik is reachable via HTTP, but it communicates with Grafana over HTTPS.
    """
    # Relate Grafana and SSC - this will make Grafana use TLS.
    await ops_test.model.add_relation(f"{grafana_app_name}", f"{ssc_app_name}:certificates")

    traefik_address = await get_traefik_url(ops_test, traefik_app_name=traefik_app_name)

    assert "http://" in traefik_address

    grafana_address = f"{traefik_address}/{ops_test.model.info.name}-{grafana_app_name}"

    # If we call Traefik before it's related to SSC, it's not configured to use TLS.
    # Hence, if it tries to route the request to Grafana (which uses TLS), it will fail.
    # This is because it doesn't trust Grafana's CA's certificate.
    fetch_with_retry(url=grafana_address, expected_status=500)

    # Relate Traefik and SSC so Traefik is configured to use TLS.
    await ops_test.model.add_relation(f"{traefik_app_name}", f"{ssc_app_name}:certificates")

    traefik_address = await get_traefik_url(ops_test, traefik_app_name=traefik_app_name)

    # Wait for Traefik to finish executing after relation is added
    await asyncio.gather(
        ops_test.model.wait_for_idle(
            apps=[grafana_app_name, traefik_app_name, ssc_app_name],
            timeout=600,
        ),
    )

    assert "https://" in traefik_address

    grafana_address = f"{traefik_address}/{ops_test.model.info.name}-{grafana_app_name}"

    # This time, we should succeed.
    # This tests full TLS.
    fetch_with_retry(url=grafana_address, expected_status=200)

    # Now, if call http://, it should also work because when Traefik is configured for TLS, it redirects from 80 to 443.
    grafana_address = grafana_address.replace("https://", "http://")
    fetch_with_retry(url=grafana_address, expected_status=200)


@pytest.mark.abort_on_fail
async def test_external_tls(ops_test):
    # Remove relation between Grafana and SSC. This means that Grafana no loger uses TLS.
    # TLS is terminated now at Traefik and traffik between Traefik and Grafana is unencrpyted.
    await ops_test.model.applications[grafana_app_name].remove_relation(f"{grafana_app_name}:certificates", ssc_app_name)

    await asyncio.gather(
        ops_test.model.wait_for_idle(
            apps=[grafana_app_name, traefik_app_name, ssc_app_name],
            timeout=600,
        ),
    )

    traefik_address = await get_traefik_url(ops_test, traefik_app_name="traefik")

    # Since Traefik still uses TLS, the URL below has https in it. This should get a 200.
    assert "https://" in traefik_address

    grafana_address = f"{traefik_address}/{ops_test.model.info.name}-{grafana_app_name}"

    fetch_with_retry(url=grafana_address, expected_status=200)

    # Also, to test whether Traefik correctly routes HTTP traffic to HTTPS, we'll make the same call to http:// this time.
    # Since Traefik uses TLS, it should redirect to HTTPS.
    # If we disable redirects, we should get a 301
    grafana_address = grafana_address.replace("https://", "http://")
    fetch_with_retry(url=grafana_address, expected_status=301, follow_redirects=False)

    # And if we allow redirects, we should get a 200.
    fetch_with_retry(url=grafana_address, expected_status=200)

