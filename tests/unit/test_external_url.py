#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

from dataclasses import replace
import logging
import unittest
from typing import Dict
from unittest.mock import patch
from pytest import fixture, mark
#from charms.traefik_k8s.v0.traefik_route import TraefikRouteRequirer
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from ops.model import ActiveStatus
from ops.testing import Model, Relation, CharmEvents


logger = logging.getLogger(__name__)

CONTAINER_NAME = "grafana"
SERVICE_NAME = "grafana"

@fixture
def base_state_with_model(base_state):
    return replace(base_state, model=Model(name="testmodel"))

def get_pebble_env(charm) -> Dict[str, str]:
    service = (
        charm.unit.get_container(CONTAINER_NAME).get_plan().services["grafana"].to_dict()
    )
    return service["environment"]  # type: ignore

def is_service_running(charm) -> bool:
    service = charm.model.unit.get_container(CONTAINER_NAME).get_service(SERVICE_NAME)
    return service.is_running()

@mark.parametrize(
    "event",
    (
        CharmEvents.update_status(),
        CharmEvents.start(),
        CharmEvents.install(),
        CharmEvents.config_changed(),
    ),
)
def test_url_without_path(ctx, base_state_with_model, event):
    """The root url and subpath env vars should not be set when no subpath is present."""
    # GIVEN a charm

    # WHEN any event is fired
    with ctx(event, base_state_with_model) as mgr:
        mgr.run()
        charm = mgr.charm
        # THEN root URL should be the FQDN URL and Grafana should not serve internal Grafana API endpoints from a subpath
        assert get_pebble_env(charm)["GF_SERVER_SERVE_FROM_SUB_PATH"] == "False"
        assert get_pebble_env(charm)["GF_SERVER_ROOT_URL"] == "http://grafana-k8s-0.testmodel.svc.cluster.local:3000"
        assert is_service_running(charm)

def test_external_url_precedence(ctx, base_state_with_model, peer_relation):
    """Precedence is [ingress] > [fqdn]."""
    # GIVEN an ingress relation
    ingress_rel = Relation("ingress", remote_app_name="traefik-app")
    state = replace(base_state_with_model, relations={peer_relation, ingress_rel})

    with patch.multiple("charm.IngressPerAppRequirer", url="http://1.2.3.4/testmodel-grafana-k8s"):
        with patch.object(IngressPerAppRequirer, "is_ready", return_value=True):
            # WHEN relation_changed on traefik is fired
            with ctx(ctx.on.relation_changed(ingress_rel), state) as mgr:
                state_out = mgr.run()
                charm = mgr.charm

                # THEN root URL is the ingress URL and the subpath env is set to True
                assert get_pebble_env(charm)["GF_SERVER_SERVE_FROM_SUB_PATH"] == "True"
                assert get_pebble_env(charm)["GF_SERVER_ROOT_URL"] == "http://1.2.3.4/testmodel-grafana-k8s"
                assert is_service_running(charm)

            # WHEN the web_external_url config option is set
            external_url_config = "http://foo.bar.config:8080/path/to/grafana"
            state_in = replace(state_out, config={"web_external_url": external_url_config})
            with ctx(ctx.on.config_changed(), state_in) as mgr:
                state_out = mgr.run()
                charm = mgr.charm
                # THEN root url is not affected
                assert get_pebble_env(charm)["GF_SERVER_SERVE_FROM_SUB_PATH"] == "True"
                assert get_pebble_env(charm)["GF_SERVER_ROOT_URL"] == "http://1.2.3.4/testmodel-grafana-k8s"
                assert is_service_running(charm)

            # WHEN the web_external_url config option is cleared
            external_url_config = ""
            state_in = replace(state_out, config={"web_external_url": external_url_config})
            with ctx(ctx.on.config_changed(), state_in) as mgr:
                state_out = mgr.run()
                charm = mgr.charm
                # THEN root url is still not affected
                assert get_pebble_env(charm)["GF_SERVER_SERVE_FROM_SUB_PATH"] == "True"
                assert get_pebble_env(charm)["GF_SERVER_ROOT_URL"] == "http://1.2.3.4/testmodel-grafana-k8s"

    # WHEN the traefik relation is removed
    with ctx(ctx.on.relation_broken(ingress_rel), state) as mgr:
        state_out = mgr.run()
        charm = mgr.charm
        # THEN the root URL is the FQDN and Grafana does not serve from the subpath
        assert get_pebble_env(charm)["GF_SERVER_SERVE_FROM_SUB_PATH"] == "False"
        assert get_pebble_env(charm)["GF_SERVER_ROOT_URL"] == "http://grafana-k8s-0.testmodel.svc.cluster.local:3000"
        assert is_service_running(charm)


@unittest.skip("The admin intentionally sets this. Leaving it not fully specced for now.")
def test_invalid_web_route_prefix(ctx, base_state_with_model):
    for invalid_url in ["htp:/foo.bar", "htp://foo.bar", "foo.bar"]:
        # WHEN the external url config option is invalid
        state = replace(base_state_with_model, config={"web_external_url": invalid_url})
        with ctx(ctx.on.update_status(), state) as mgr:
            state_out = mgr.run()
            charm = mgr.charm
            # THEN the unit is active
            # TODO change to blocked
            assert charm.unit.status == ActiveStatus()
            # AND the pebble envvars are set, even though values are invalid
            assert "GF_SERVER_SERVE_FROM_SUB_PATH" in get_pebble_env(charm)
            assert "GF_SERVER_ROOT_URL" in get_pebble_env(charm)
            assert is_service_running(charm)

        # WHEN the invalid option in cleared
        state = replace(state_out, config={"web_external_url": ""})
        with ctx(ctx.on.update_status(), state) as mgr:
            mgr.run()
            charm = mgr.charm
            # THEN the unit is active
            assert charm.unit.status == ActiveStatus()
