"""grafana_metadata.

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

To implement handling this relation:

* instantiate a `GrafanaMetadataRequirer` object in your charm's `__init__` method.  This object handles all low-level
  events for managing this relation (relation-changed, relation-joined, etc)
* observe the `DataChangedEvent` event anywhere you want to react to changes in the data provided by this relation.

An example implementation is:

```python
class FooCharm(CharmBase):
    def __init__(self, framework):
        super().__init__(framework)
        # Create the GrafanaMetadataRequirer instance, providing the relation name you've used
        self.grafana_metadata = GrafanaMetadataRequirer(self, "grafana-metadata")
        self.framework.observe(self.grafana_metadata.on.data_changed, self._on_grafana_metadata_data_changed)
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

Return:
        self.log(f"Got Grafana's internal_url: {metadata.internal_url}")
```

### Provider

To add this relation to your charm as a provider, add the following to your `charmcraft.yaml` or `metadata.yaml`:

```yaml
provides:
  grafana-metadata:
    interface: grafana_metadata
```

To manage sending data to related applications in your charm, use `GrafanaMetadataProvider`.  Note that
`GrafanaMetadataProvider` *does not* manage any events, but instead provides a `send_data` method for sending data to
all related applications.  Triggering `send_data` appropriately is left to the charm author, although generally you want
to do this at least during relation_joined and leader_elected events.  An example implementation is:

```python
class FooCharm(CharmBase):
    def __init__(self, framework):
        super().__init__(framework)
        self.grafana_metadata = GrafanaMetadataProvider(
            charm=self,
            grafana_uid=self.unique_name,
            ingress_url=self.external_url,
            internal_url=self.internal_url,
            relation_name="grafana-metadata"
        )

        self.framework.observe(self.on.leader_elected, self.do_something_to_send_data)
        self.framework.observe(self._charm.on["grafana-metadata"].relation_joined, self.do_something_to_send_data)
```
"""
import json
import logging
from typing import List, Optional, Union


from ops import CharmBase, BoundEvent, EventBase, CharmEvents, EventSource, Object
from pydantic import BaseModel, Field

# The unique Charmhub library identifier, never change it
LIBID = "26290f24974540adb4464b695bd01ea3"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

PYDEPS = ["pydantic>=2"]

log = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "grafana-info"


class GrafanaMetadataAppData(BaseModel):
    """Data model for the grafana-info interface."""

    ingress_url: str = Field(description="The ingress URL.")
    internal_url: str = Field(description="The URL for connecting to the prometheus api from inside the cluster.")
    grafana_uid: str = Field(description="The UID of this Grafana application.")


class DataChangedEvent(EventBase):
    """Charm Event triggered when the relation data has changed."""


class ReceiverCharmEvents(CharmEvents):
    """Events raised by the data receiver side of the interface."""

    data_changed = EventSource(DataChangedEvent)


class GrafanaMetadataRequirer(Object):
    """Class for handling the receiver side of the grafana-info relation."""

    on = ReceiverCharmEvents()  # type: ignore[reportAssignmentType]

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str,
        refresh_event: Optional[Union[BoundEvent, List[BoundEvent]]] = None,
    ) -> None:
        """Initialize the GrafanaMetadataRequirer object.

        Args:
            charm: The charm instance.
            relation_name: The name of the relation.
            refresh_event: An event or list of events that should trigger the library to process its relations.
                           By default, this charm already observes the relation_changed event.
        """
        super().__init__(charm, relation_name)

        self._charm = charm
        self._relation_name = relation_name

        if not refresh_event:
            refresh_event = []
        if isinstance(refresh_event, BoundEvent):
            refresh_event = [refresh_event]
        for ev in refresh_event:
            self.framework.observe(ev, self.on_relation_changed)

        self.framework.observe(
            self._charm.on[self._relation_name].relation_changed, self.on_relation_changed
        )

    def __len__(self):
        """Return the number of related applications."""
        return len(self.get_relations())

    def on_relation_changed(self, _: EventBase) -> None:
        """Handle when the remote application data changed."""
        self.on.data_changed.emit()

    def get_relations(self):
        """Return the relation instances for applications related to us on the monitored relation."""
        return self._charm.model.relations.get(self._relation_name, ())

    def get_data(self) -> Optional[BaseModel]:
        """Return data for at most one related application, raising if more than one is available.

        Useful for charms that always expect exactly one related application.  It is recommended that those charms also
        set limit=1 for that relation in charmcraft.yaml.  Returns None if no data is available (either because no
        applications are related to us, or because the related application has not sent data).
        """
        relations = self.get_relations()
        if len(relations) == 0:
            return None
        if len(relations) > 1:
            # TODO: Different exception type?
            raise ValueError("Cannot get_info when more than one application is related.")

        raw_data_dict = relations[0].data.get(relations[0].app)
        if not raw_data_dict:
            return None

        # Static analysis errors saying the keys may not be strings.  Protect against this by converting them.
        raw_data_dict = {str(k): v for k, v in raw_data_dict.items()}

        return GrafanaMetadataAppData.model_validate_json(json.dumps(raw_data_dict))  # type: ignore

    def get_data_from_all_relations(self) -> List[BaseModel]:
        """Return a list of data objects from all relations."""
        relations = self.get_relations()
        info_list = []
        for i, relation in enumerate(relations):
            data_dict = relation.data.get(relation.app)
            if not data_dict:
                info_list.append(None)
                continue

            # Static analysis errors saying the keys may not be strings.  Protect against this by converting them.
            data_dict = {str(k): v for k, v in data_dict.items()}
            info_list.append(GrafanaMetadataAppData(**data_dict))
        return info_list


class GrafanaMetadataProvider(Object):
    """Class for handling the Provider side of the grafana-info relation."""

    def __init__(
        self,
        charm: CharmBase,
        grafana_uid: str,
        ingress_url: str,
        internal_url: str,
        relation_name: str,
    ):
        """Initialize the GrafanaMetadataProvider object.

        This library does not automatically observe any events - it is up to the charm to call send_data when it is
        appropriate to do so.  This is typically on at least all relation_joined events and the leader_elected event.

        Args:
            charm: The charm instance.
            grafana_uid: The UID of this Grafana instance.
            ingress_url: The URL for the Grafana ingress.
            internal_url: The URL for the Grafana internal service.
            relation_name: The name of the relation.
        """
        super().__init__(charm, relation_name)

        self._charm = charm
        self._data = GrafanaMetadataAppData(ingress_url=ingress_url, internal_url=internal_url, grafana_uid=grafana_uid)
        self._relation_name = relation_name

    def _get_relations(self):
        """Return the applications related to us under the monitored relation."""
        return self._charm.model.relations.get(self._relation_name, ())

    def send_data(self):
        """Post grafana-metadata to all related applications.

        This method writes to the relation's app data bag, and thus should never be called by a unit that is not the
        leader otherwise ops will raise an exception.
        """
        info_relations = self._get_relations()
        for relation in info_relations:
            databag= relation.data[self._charm.app]
            databag.update(self._data.model_dump(mode="json", by_alias=True, exclude_defaults=True, round_trip=True))
