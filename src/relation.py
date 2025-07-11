# Copyright 2025 Canonical
# See LICENSE file for licensing details.
"""Relation class."""

import json
from typing import Any, Optional
import ops


class Relation:
    """A helper class to manage relation data."""

    def __init__(self, app: ops.Application, relation: Optional[ops.Relation]):
        self._relation = relation
        self._app = app

    @property
    def data(self):
        """Return relation data."""
        if self._relation:
            return self._relation.data
        return None

    def set_app_data(self, key: str, data: Any) -> None:
        """Put information into the app data bucket."""
        if self.data:
            self.data[self._app][key] = json.dumps(data)

    def get_app_data(self, key: str) -> Any:
        """Retrieve information from the app data bucket."""
        if not self.data:
            return {}
        data = self.data[self._app].get(key, "")
        return json.loads(data) if data else {}
