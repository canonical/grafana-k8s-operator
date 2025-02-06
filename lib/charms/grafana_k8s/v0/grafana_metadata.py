"""grafana_metadata

This implements provider and requirer sides of the grafana-metadata interface, which is used to communicate information
about an Grafana installation such as its url and UID.

## Usage

### Requirer

To add this relation to your charm as a requirer, add the following to your `charmcraft.yaml` or `metadata.yaml`:

```yaml
requires:
  grafana-metadata:
    # The example below uses the API for when limit=1.  If you need to support multiple related applications, remove
    # this and use the list-based data accessor method.
    limit: 1
    interface: grafana_metadata
```

To handle the relation events in your charm, use `GrafanaMetadataRequirer`.  That object handles all relation events for
this relation, and emits a `DataChangedEvent` when data changes the charm might want to react to occur.  To set it up,
instantiate an `GrafanaMetadataRequirer` object in your charm's `__init__` method and observe the `DataChangedEvent`:

```python
class FooCharm(CharmBase):
    def __init__(self, framework):
        super().__init__(framework)
        # Create the GrafanaMetadataRequirer instance, providing the relation name you've used
        self.grafana_metadata = GrafanaMetadataRequirer(self, "grafana-metadata")
        self.framework.observe(self.grafana_metadata.on.data_changed, self.do_something_with_metadata)
```

To access the data elsewhere in the charm, use the provided data accessors.  These return `GrafanaMetadataAppData`
objects:

```python
class FooCharm(CharmBase):
    ...
    # If using limit=1
    def do_something_with_metadata(self):
        # Get exactly one related application's data, raising if more than one is available
        # note: if not using limit=1, see .get_data_from_all_relations()
        metadata = self.grafana_metadata.get_data()
        if metadata is None:
            self.log("No metadata available yet")
            return
        self.log(f"Got Grafana's internal_url: {metadata.internal_url}")
```

### Provider

To add this relation to your charm as a provider, add the following to your `charmcraft.yaml` or `metadata.yaml`:

```yaml
provides:
  grafana-metadata:
    interface: grafana_metadata
```

To handle the relation events in your charm, use `GrafanaMetadataProvider`.  That object sends data to all related
requirers automatically when applications join.  To set it up, instantiate an `GrafanaMetadataProvider` object in your
charm's `__init__` method:

```python
class FooCharm(CharmBase):
    def __init__(self, framework):
        super().__init__(framework)
        # Create the GrafanaMetadataProvider instance, providing the root namespace for the Grafana installation
        self.grafana_metadata = GrafanaMetadataProvider(
            charm=self,
            grafana_uid=self.unique_name,
            ingress_url=self.external_url,
            internal_url=self.internal_url,
            relation_name="grafana-metadata"
        )
```
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

# Uncomment once we're actually pulling from this repo instead of a gh branch
# PYDEPS = ["charm-relation-building-blocks"]

DEFAULT_RELATION_NAME = "grafana-info"


# Interface schema

class GrafanaMetadataAppData(BaseModel):
    """Data model for the grafana-info interface."""

    # TODO: Copy this exactly from Dylan's mimir code
    ingress_url: str = Field(description="The ingress URL.")
    internal_url: str = Field(description="The URL for connecting to the prometheus api from inside the cluster.")
    grafana_uid: str = Field(description="The UID of this Grafana application.")


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
