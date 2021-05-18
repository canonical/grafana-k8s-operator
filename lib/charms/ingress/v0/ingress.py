"""Library for the ingress relation.

This library contains the Requires and Provides classes for handling
the ingress interface.

Import `IngressRequires` in your charm, with two required options:
    - "self" (the charm itself)
    - config_dict

`config_dict` accepts the following keys:
    - service-hostname (required)
    - service-name (required)
    - service-port (required)
    - max_body-size
    - service-namespace
    - session-cookie-max-age
    - tls-secret-name

As an example:
```
from charms.ingress.v0.ingress import IngressRequires

# In your charm's `__init__` method.
self.ingress = IngressRequires(self, {"service-hostname": self.config["external_hostname"],
                                      "service-name": self.app.name,
                                      "service-port": 80})

# In your charm's `config-changed` handler.
self.ingress.update_config({"service-hostname": self.config["external_hostname"]})
```
"""

import logging

from ops.charm import CharmEvents
from ops.framework import EventBase, EventSource, Object
from ops.model import BlockedStatus

# The unique Charmhub library identifier, never change it
LIBID = "2d35a009b0d64fe186c99a8c9e53c6ab"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft push-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 7

logger = logging.getLogger(__name__)

REQUIRED_INGRESS_RELATION_FIELDS = {
    "service-hostname",
    "service-name",
    "service-port",
}

OPTIONAL_INGRESS_RELATION_FIELDS = {
    "max-body-size",
    "service-namespace",
    "session-cookie-max-age",
    "tls-secret-name",
}


class IngressAvailableEvent(EventBase):
    pass


class IngressCharmEvents(CharmEvents):
    """Custom charm events."""

    ingress_available = EventSource(IngressAvailableEvent)


class IngressRequires(Object):
    """This class defines the functionality for the 'requires' side of the 'ingress' relation.

    Hook events observed:
        - relation-changed
    """

    def __init__(self, charm, config_dict):
        super().__init__(charm, "ingress")

        self.framework.observe(
            charm.on["ingress"].relation_changed, self._on_relation_changed
        )

        self.config_dict = config_dict

    def _config_dict_errors(self, update_only=False):
        """Check our config dict for errors."""
        block_status = False
        unknown = [
            x
            for x in self.config_dict
            if x
            not in REQUIRED_INGRESS_RELATION_FIELDS | OPTIONAL_INGRESS_RELATION_FIELDS
        ]
        if unknown:
            logger.error(
                "Unknown key(s) in config dictionary found: %s", ", ".join(unknown)
            )
            block_status = True
        if not update_only:
            missing = [
                x for x in REQUIRED_INGRESS_RELATION_FIELDS if x not in self.config_dict
            ]
            if missing:
                logger.error(
                    "Missing required key(s) in config dictionary: %s",
                    ", ".join(missing),
                )
                block_status = True
        if block_status:
            self.model.unit.status = BlockedStatus(
                "Error in ingress relation, check `juju debug-log`"
            )
            return True
        return False

    def _on_relation_changed(self, event):
        """Handle the relation-changed event."""
        # `self.unit` isn't available here, so use `self.model.unit`.
        if self.model.unit.is_leader():
            if self._config_dict_errors():
                return
            for key in self.config_dict:
                event.relation.data[self.model.app][key] = str(self.config_dict[key])

    def update_config(self, config_dict):
        """Allow for updates to relation."""
        if self.model.unit.is_leader():
            self.config_dict = config_dict
            if self._config_dict_errors(update_only=True):
                return
            relation = self.model.get_relation("ingress")
            if relation:
                for key in self.config_dict:
                    relation.data[self.model.app][key] = str(self.config_dict[key])


class IngressProvides(Object):
    """This class defines the functionality for the 'provides' side of the 'ingress' relation.

    Hook events observed:
        - relation-changed
    """

    def __init__(self, charm):
        super().__init__(charm, "ingress")
        # Observe the relation-changed hook event and bind
        # self.on_relation_changed() to handle the event.
        self.framework.observe(
            charm.on["ingress"].relation_changed, self._on_relation_changed
        )
        self.charm = charm

    def _on_relation_changed(self, event):
        """Handle a change to the ingress relation.

        Confirm we have the fields we expect to receive."""
        # `self.unit` isn't available here, so use `self.model.unit`.
        if not self.model.unit.is_leader():
            return

        ingress_data = {
            field: event.relation.data[event.app].get(field)
            for field in REQUIRED_INGRESS_RELATION_FIELDS
            | OPTIONAL_INGRESS_RELATION_FIELDS
        }

        missing_fields = sorted(
            [
                field
                for field in REQUIRED_INGRESS_RELATION_FIELDS
                if ingress_data.get(field) is None
            ]
        )

        if missing_fields:
            logger.error(
                "Missing required data fields for ingress relation: {}".format(
                    ", ".join(missing_fields)
                )
            )
            self.model.unit.status = BlockedStatus(
                "Missing fields for ingress: {}".format(", ".join(missing_fields))
            )

        # Create an event that our charm can use to decide it's okay to
        # configure the ingress.
        self.charm.on.ingress_available.emit()
