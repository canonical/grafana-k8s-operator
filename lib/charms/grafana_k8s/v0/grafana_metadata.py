"""TODO: Add a proper docstring here.

This is a placeholder docstring for this charm library. Docstrings are
presented on Charmhub and updated whenever you push a new version of the
library.

Complete documentation about creating and documenting libraries can be found
in the SDK docs at https://juju.is/docs/sdk/libraries.

See `charmcraft publish-lib` and `charmcraft fetch-lib` for details of how to
share and consume charm libraries. They serve to enhance collaboration
between charmers. Use a charmer's libraries for classes that handle
integration with their charm.

Bear in mind that new revisions of the different major API versions (v0, v1,
v2 etc) are maintained independently.  You can continue to update v0 and v1
after you have pushed v3.

Markdown is supported, following the CommonMark specification.
"""

from typing import List, Optional, Union

from charm_relation_building_blocks.relation_handlers import Receiver, Sender
# import and re-export these classes from the relation_handlers module, in case the user needs them
from charm_relation_building_blocks.relation_handlers import DataChangedEvent as DataChangedEvent  # ignore: F401
from charm_relation_building_blocks.relation_handlers import ReceiverCharmEvents as ReceiverCharmEvents  # ignore: F401

from ops import CharmBase, BoundEvent
from pydantic import BaseModel, Field

# The unique Charmhub library identifier, never change it
LIBID = "26290f24974540adb4464b695bd01ea3"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

DEFAULT_RELATION_NAME = "grafana-info"


# Interface schema

class GrafanaMetadataAppData(BaseModel):
    """Data model for the grafana-info interface."""

    # TODO: Copy this exactly from Dylan's mimir code
    ingress_url: str = Field()
    internal_url: str = Field()
    grafana_uid: str = Field()


class GrafanaMetadataRequirer(Receiver):
    """Class for handling the receiver side of the grafana-info relation."""

    # inherits the events:
    # on = ReceiverCharmEvents()  # type: ignore[reportAssignmentType]
    #

    def __init__(
            self,
            charm: CharmBase,
            relation_name: str = DEFAULT_RELATION_NAME,
            refresh_event: Optional[Union[BoundEvent, List[BoundEvent]]] = None,
    ) -> None:
        """Initialize the GrafanaMetadataRequirer object.

        Args:
            charm: The charm instance.
            relation_name: The name of the relation.
            refresh_event: An event or list of events that should trigger the library to process its relations.
                           By default, this charm already observes the relation_changed event.
        """
        super().__init__(charm, relation_name, GrafanaMetadataAppData, refresh_event)


class GrafanaMetadataProvider(Sender):
    """Class for handling the sending side of the grafana-info relation."""

    def __init__(
            self,
            charm: CharmBase,
            grafana_uid: str,
            ingress_url: str,
            internal_url: str,
            relation_name: str = DEFAULT_RELATION_NAME,
            refresh_event: Optional[Union[BoundEvent, List[BoundEvent]]] = None,
    ) -> None:
        """Initialize the GrafanaMetadataProvider object.

        Args:
            # TODO: Copy this exactly from Dylan's mimir code
            charm: The charm instance.
            grafana_uid: The UID of this Grafana instance.
            ingress_url: The URL for the Grafana ingress.
            internal_url: The URL for the Grafana internal service.
            relation_name: The name of the relation.
            refresh_event: An event or list of events that should trigger the library to publish data to its relations.
                           By default, this charm already observes the relation_joined and on_leader_elected events.
        """
        data = GrafanaMetadataAppData(grafana_uid=grafana_uid, ingress_url=ingress_url, internal_url=internal_url)
        super().__init__(charm, data, relation_name, refresh_event)
