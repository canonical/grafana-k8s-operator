#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""A Charm to functionally test the Grafana Operator."""

import logging

from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from charms.grafana_k8s.v0.grafana_source import GrafanaSourceProvider
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

logger = logging.getLogger(__name__)


class GrafanaTesterCharm(CharmBase):
    """A Charm used to test the Grafana charm."""

    def __init__(self, *args):
        super().__init__(*args)
        self._name = "grafana-tester"
        self.grafana_source = GrafanaSourceProvider(self, self.on.grafana_tester_pebble_ready)
        self.grafana_dashboard = GrafanaDashboardProvider(self)
        self.framework.observe(
            self.on.grafana_tester_pebble_ready, self._on_grafana_tester_pebble_ready
        )

        self.framework.observe(self.on.config_changed, self._on_config_changed)

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


if __name__ == "__main__":
    main(GrafanaTesterCharm)
