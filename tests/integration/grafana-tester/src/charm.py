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
from ops.pebble import Layer

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

    def _on_config_changed(self, _):
        """Reconfigure the Grafana tester."""
        container = self.unit.get_container(self._name)
        if not container.can_connect():
            self.unit.status = BlockedStatus("Waiting for Pebble ready")
            return

        current_services = container.get_plan().services
        new_layer = self._tester_pebble_layer()
        if current_services != new_layer.services:
            container.add_layer(self._name, new_layer, combine=True)
            logger.debug("Added tester layer to container")

            container.restart(self._name)
            logger.info("Restarted tester service")

        self.unit.status = ActiveStatus()

    def _tester_pebble_layer(self):
        """Generate Grafana tester pebble layer."""
        layer_spec = {
            "summary": "grafana tester",
            "description": "a test data generator for Grafana",
            "services": {
                self._name: {
                    "override": "replace",
                    "summary": "We don't do anything!",
                    "command": "python /metrics.py",
                    "startup": "enabled",
                }
            },
        }
        return Layer(layer_spec)


if __name__ == "__main__":
    main(GrafanaTesterCharm)
