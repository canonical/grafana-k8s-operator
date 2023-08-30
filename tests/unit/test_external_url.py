#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import unittest
from typing import Dict
from unittest.mock import MagicMock, patch

import ops
from charms.traefik_route_k8s.v0.traefik_route import TraefikRouteRequirer
from ops.model import ActiveStatus
from ops.testing import Harness

from charm import PORT, GrafanaCharm

logger = logging.getLogger(__name__)

ops.testing.SIMULATE_CAN_CONNECT = True
CONTAINER_NAME = "grafana"
SERVICE_NAME = "grafana"

k8s_resource_multipatch = patch.multiple(
    "charm.KubernetesComputeResourcesPatch",
    _namespace="test-namespace",
    _patch=lambda *a, **kw: True,
    is_ready=lambda *a, **kw: True,
)


class TestExternalUrl(unittest.TestCase):
    """External url sources have a precedence, and must be correctly propagated everywhere."""

    def setUp(self, *unused):
        self.harness = Harness(GrafanaCharm)
        self.addCleanup(self.harness.cleanup)

        model_name = "testmodel"
        self.harness.set_model_name(model_name)
        for p in [
            patch("lightkube.core.client.GenericSyncClient"),
            patch(
                "socket.getfqdn", new=lambda *args: f"grafana-k8s-0.{model_name}.svc.cluster.local"
            ),
            patch("socket.gethostbyname", new=lambda *args: "1.2.3.4"),
            k8s_resource_multipatch,
            patch.object(GrafanaCharm, "grafana_version", "0.0.0"),
            patch("ops.testing._TestingModelBackend.network_get"),
            patch("ops.testing._TestingPebbleClient.exec", MagicMock()),
        ]:
            p.start()
            self.addCleanup(p.stop)

        self.harness.set_leader(True)

        # Peer relation
        self.app_name = "grafana-k8s"
        self.peer_rel_id = self.harness.add_relation("grafana", self.app_name)

        # Auth relation
        # FIXME why tests fail when this relation is not created?
        self.grafana_auth_rel_id = self.harness.add_relation("grafana-auth", "auth_provider")

        self.harness.begin_with_initial_hooks()
        self.harness.container_pebble_ready(CONTAINER_NAME)
        self.harness.container_pebble_ready("litestream")
        self.fqdn_url = f"http://fqdn:{PORT}"

    def get_pebble_env(self) -> Dict[str, str]:
        service = (
            self.harness.get_container_pebble_plan(CONTAINER_NAME).services["grafana"].to_dict()
        )
        return service["environment"]

    def is_service_running(self) -> bool:
        service = self.harness.model.unit.get_container(CONTAINER_NAME).get_service(SERVICE_NAME)
        return service.is_running()

    @patch.object(TraefikRouteRequirer, "external_host", new="1.2.3.4")
    def test_url_without_path(self):
        """The root url and subpath env vars should not be set when no subpath is present."""
        # GIVEN a charm with an fqdn as its external URL
        # (this is set by a mock decorator)

        # THEN root url and subpath envs are defined
        self.assertEqual(self.get_pebble_env()["GF_SERVER_SERVE_FROM_SUB_PATH"], "False")
        self.assertEqual(
            self.get_pebble_env()["GF_SERVER_ROOT_URL"],
            "http://grafana-k8s-0.testmodel.svc.cluster.local:3000",
        )
        self.assertTrue(self.is_service_running())

    def test_external_url_precedence(self):
        """Precedence is [ingress] > [fqdn]."""
        # GIVEN a charm with the fqdn as its external URL
        # (this is set by a mock decorator)

        # WHEN a relation with traefik is formed
        with patch.object(TraefikRouteRequirer, "external_host", new="1.2.3.4"):
            rel_id = self.harness.add_relation("ingress", "traefik-app")
            self.harness.add_relation_unit(rel_id, "traefik-app/0")

            # AND ingress becomes ready
            self.harness.charm.ingress.on.ready.emit(
                self.harness.charm.model.get_relation("ingress", rel_id)
            )

            # THEN root url is fqdn and the subpath env is defined
            self.assertEqual(self.get_pebble_env()["GF_SERVER_SERVE_FROM_SUB_PATH"], "False")
            self.assertEqual(
                self.get_pebble_env()["GF_SERVER_ROOT_URL"], "http://1.2.3.4/testmodel-grafana-k8s"
            )
            self.assertTrue(self.is_service_running())

            # WHEN the web_external_url config option is set
            external_url_config = "http://foo.bar.config:8080/path/to/grafana"
            self.harness.update_config({"web_external_url": external_url_config})

            # THEN root url is not affected
            self.assertEqual(self.get_pebble_env()["GF_SERVER_SERVE_FROM_SUB_PATH"], "False")
            self.assertEqual(
                self.get_pebble_env()["GF_SERVER_ROOT_URL"], "http://1.2.3.4/testmodel-grafana-k8s"
            )
            self.assertTrue(self.is_service_running())

            # WHEN the web_external_url config option is cleared
            self.harness.update_config(unset=["web_external_url"])

            # THEN root url is still not affected
            self.assertEqual(self.get_pebble_env()["GF_SERVER_SERVE_FROM_SUB_PATH"], "False")
            self.assertEqual(
                self.get_pebble_env()["GF_SERVER_ROOT_URL"], "http://1.2.3.4/testmodel-grafana-k8s"
            )

        # WHEN the traefik relation is removed
        with patch.object(TraefikRouteRequirer, "external_host", new=""):
            self.harness.remove_relation_unit(rel_id, "traefik-app/0")
            self.harness.remove_relation(rel_id)

            # THEN root url and subpath envs are undefined (because fqdn is a bare hostname)
            self.assertEqual(self.get_pebble_env()["GF_SERVER_SERVE_FROM_SUB_PATH"], "False")
            self.assertEqual(
                self.get_pebble_env()["GF_SERVER_ROOT_URL"],
                "http://grafana-k8s-0.testmodel.svc.cluster.local:3000",
            )
            self.assertTrue(self.is_service_running())

    @unittest.skip("The admin intentionally sets this. Leaving it not fully specced for now.")
    def test_invalid_web_route_prefix(self):
        for invalid_url in ["htp:/foo.bar", "htp://foo.bar", "foo.bar"]:
            with self.subTest(url=invalid_url):
                # WHEN the external url config option is invalid
                self.harness.update_config({"web_external_url": invalid_url})

                # THEN the unit is active
                # TODO change to blocked
                self.assertIsInstance(self.harness.charm.unit.status, ActiveStatus)

                # AND the pebble envvars are set, even though values are invalid
                self.assertIn("GF_SERVER_SERVE_FROM_SUB_PATH", self.get_pebble_env())
                self.assertIn("GF_SERVER_ROOT_URL", self.get_pebble_env())
                self.assertTrue(self.is_service_running())

                # WHEN the invalid option in cleared
                self.harness.update_config(unset=["web_external_url"])

                # THEN the unit is active
                self.assertIsInstance(self.harness.charm.unit.status, ActiveStatus)
