# Copyright 2025 Canonical
# See LICENSE file for licensing details.
"""Peer relation class."""
import json
from typing import Any, Optional
from ops import Application, Relation

class Peer:
    """A helper class to manage peer relation data."""

    def __init__(self, app:Application, peers: Optional[Relation] = None):
        self._peers = peers
        self._app = app

    @property
    def data(self):
        """Return peer relation data.

        Used by charms.grafana_k8s.v0.grafana_source lib.
        """
        if self._peers:
            return self._peers.data
        return None

    @property
    def has_peers(self) -> bool:
        """Check whether there are any other Grafanas as peers."""
        return len(self._peers.units) > 0 if self._peers is not None else False


    def set_peer_data(self, key: str, data: Any) -> None:
        """Put information into the peer data bucket instead of `StoredState`."""
        if self._peers:
            self._peers.data[self._app][key] = json.dumps(data)

    def get_peer_data(self, key: str) -> Any:
        """Retrieve information from the peer data bucket instead of `StoredState`."""
        if not self.data:
            return {}
        data = self.data[self._app].get(key, "")
        return json.loads(data) if data else {}
