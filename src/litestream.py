# Copyright 2025 Canonical
# See LICENSE file for licensing details.
"""Replication class."""

import logging
from typing import List
from ops import Container
import socket
from ops.pebble import (
    ConnectionError,
    Layer,
)
import yaml
from relation import Relation
from constants import DATABASE_PATH

logger = logging.getLogger()


class Litestream:
    """Listream workload."""

    def __init__(
        self,
        container: Container,
        is_leader: bool,
        peers: Relation,
    ):
        self._container = container
        self._is_leader = is_leader
        self._fqdn = socket.getfqdn()
        self._peers = peers

    @property
    def layer(self) -> Layer:
        """Construct the pebble layer information for litestream."""
        config = {}

        if self._is_leader:
            self._peers.set_app_data("replica_primary", socket.gethostbyname(self._fqdn))
            config["LITESTREAM_ADDR"] = f"{socket.gethostbyname(self._fqdn)}:{9876}"
        else:
            config["LITESTREAM_UPSTREAM_URL"] = (
                f"{self._peers.get_app_data('replica_primary')}:{9876}"
            )

        layer = Layer(
            {
                "summary": "litestream layer",
                "description": "litestream layer",
                "services": {
                    "litestream": {
                        "override": "replace",
                        "summary": "litestream service",
                        "command": "litestream replicate -config /etc/litestream.yml",
                        "startup": "enabled",
                        "environment": {
                            **config,
                        },
                    }
                },
            }
        )

        return layer

    def reconcile(self):
        """Unconditional control logic."""
        if self._container.can_connect():
            changes = []
            self._reconcile_config(changes)
            if any(changes):
                self.restart_litestream()

    def _reconcile_config(self, changes: List):
        if self._container.get_plan().services != self.layer.services:
            changes.append(True)

        litestream_config = {"addr": ":9876", "dbs": [{"path": DATABASE_PATH}]}

        if not self._is_leader:
            litestream_config["dbs"][0].update(
                {"upstream": {"url": "http://${LITESTREAM_UPSTREAM_URL}"}}
            )  # type: ignore

        self._container.push("/etc/litestream.yml", yaml.dump(litestream_config), make_dirs=True)

    def restart_litestream(self) -> None:
        """Restart the pebble container.

        `container.replan()` is intentionally avoided, since if no environment
        variables are changed, this will not actually restart Litestream.
        """
        layer = self.layer
        try:
            plan = self._container.get_plan()
            if plan.services == layer.services:
                return
            self._container.add_layer("litestream", layer, combine=True)
            self._container.restart("litestream")
            logger.info("litestream replication restarted")
        except ConnectionError:
            logger.error(
                "Could not restart replication -- Pebble socket does "
                "not exist or is not responsive"
            )
