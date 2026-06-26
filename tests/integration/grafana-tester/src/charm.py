#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""A Charm to functionally test the Grafana Operator."""

import logging
from typing import cast

from charms.grafana_k8s.v1.grafana_source import GrafanaSourceProvider
from charms.grafana_k8s.v0.grafana_auth import GrafanaAuthProxyProvider
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from charms.traefik_k8s.v1.ingress_per_unit import IngressPerUnitRequirer  # type: ignore
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

logger = logging.getLogger(__name__)

PORT = 9090


class GrafanaTesterCharm(CharmBase):
    """A Charm used to test the Grafana charm."""

    def __init__(self, *args):
        super().__init__(*args)
        self._name = "grafana-tester"

        app_datasource = cast(bool, self.config.get("app_datasource", True))
        unit_datasources = cast(bool, self.config.get("unit_datasources", False))

        # Ingress: app-level datasources pair with ingress-per-app, per-unit datasources
        # pair with ingress-per-unit. The grafana-source library never talks to the
        # ingress library; it only receives whichever URL we feed it below.
        self.ipa = IngressPerAppRequirer(self, relation_name="ingress", port=PORT)
        self.ipu = IngressPerUnitRequirer(self, relation_name="ingress-per-unit", port=PORT)

        self.grafana_source = GrafanaSourceProvider(
            self,
            source_type="prometheus",
            source_port=str(PORT),
            app_datasource=app_datasource,
            unit_datasources=unit_datasources,
            app_datasource_url=self.ipa.url,
            unit_datasource_url=self.ipu.url,
            refresh_event=self.on.grafana_tester_pebble_ready,
        )
        self.grafana_dashboard = GrafanaDashboardProvider(self)
        self.grafana_auth_proxy_provider = GrafanaAuthProxyProvider(
            self, relation_name="grafana-auth"
        )
        self.framework.observe(
            self.on.grafana_tester_pebble_ready, self._on_grafana_tester_pebble_ready
        )

        self.framework.observe(self.on.config_changed, self._on_config_changed)

        self.framework.observe(
            self.grafana_auth_proxy_provider.on.urls_available, self._on_urls_available
        )

        self.framework.observe(self.ipa.on.ready, self._on_ingress_changed)
        self.framework.observe(self.ipa.on.revoked, self._on_ingress_changed)
        self.framework.observe(self.ipu.on.ready, self._on_ingress_changed)
        self.framework.observe(self.ipu.on.revoked, self._on_ingress_changed)

    def _on_grafana_tester_pebble_ready(self, _):
        """Just set it ready. It's a pause image."""
        self.unit.status = ActiveStatus()

    def _on_config_changed(self, _):
        """Reconfigure the Grafana tester."""
        container = self.unit.get_container(self._name)
        if not container.can_connect():
            self.unit.status = BlockedStatus("Waiting for Pebble ready")
            return

        self.unit.status = ActiveStatus()

    def _on_urls_available(self, event):
        self.urls = event.urls
        self.unit.status = ActiveStatus()

    def _on_ingress_changed(self, _):
        """Push the (possibly ingressed) addresses into the grafana-source relation.

        Called on both ``ready`` and ``revoked``. On revoke the URL is ``None``; we
        still re-publish (with an empty URL) so the source falls back to the
        load-balanced service / unit FQDN address instead of retaining a stale
        ingress URL.
        """
        self.grafana_source.update_app_source(self.ipa.url or "")
        self.grafana_source.update_unit_source(self.ipu.url or "")
        self.unit.status = ActiveStatus()


if __name__ == "__main__":
    main(GrafanaTesterCharm)
