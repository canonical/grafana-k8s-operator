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

import json
import logging
from typing import List, Optional, Union, MutableMapping, Type


from ops import CharmBase, BoundEvent, EventBase, CharmEvents, EventSource, Object
from pydantic import BaseModel, Field, ValidationError

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


# The implementation of this interface is split into two parts: the library code specific to this relation (the schema
# and definition of requirer/proivider classes), and the generic tooling that can be used for any relation of this sort.
# The generic part is first, and then the bottom of this file has the code specific to this relation.


class DataChangedEvent(EventBase):
    """Charm Event triggered when the relation data has changed."""


class ReceiverCharmEvents(CharmEvents):
    """Events raised by the data receiver side of the interface."""

    data_changed = EventSource(DataChangedEvent)


class Receiver(Object):
    """Base class for the receiver side of a generic uni-directional application data relation."""

    on = ReceiverCharmEvents()  # type: ignore[reportAssignmentType]

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str,
        data_model: Type[BaseModel],
        refresh_event: Optional[Union[BoundEvent, List[BoundEvent]]] = None,
    ) -> None:
        """Initialize the Receiver object.

        Args:
            charm: The charm instance that the relation is attached to.
            relation_name: The name of the relation.
            data_model: The pydantic data model class to use for instantiating data instances.
            refresh_event: An event or list of events that should trigger this library to process its relations.
                           By default, this charm already observes the relation_changed event.
        """
        super().__init__(charm, relation_name)

        self._charm = charm
        self._relation_name = relation_name
        self._data_model = data_model

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

        raw_data = relations[0].data.get(relations[0].app)
        if not raw_data:
            return None

        # Static analysis errors saying the keys may not be strings.  Protect against this by converting them.
        raw_data = {str(k): v for k, v in raw_data.items()}

        return load_from_databag(self._data_model, raw_data)

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
            info_list.append(self._data_model(**data_dict))
        return info_list


class Sender(Object):
    """Base class for the sending side of a generic uni-directional application data relation."""

    def __init__(
        self,
        charm: CharmBase,
        data: BaseModel,
        relation_name: str,
        refresh_event: Optional[Union[BoundEvent, List[BoundEvent]]] = None,
    ) -> None:
        """Initialize the IstioInfoProvider object.

        Args:
            charm: The charm instance.
            data: An instance of the data sent on this relation.
            relation_name: The name of the relation.
            refresh_event: An event or list of events that should trigger the library to publish data to its relations.
                           By default, this charm already observes the relation_joined and on_leader_elected events.
        """
        super().__init__(charm, relation_name)

        self._charm = charm
        self._data = data
        self._relation_name = relation_name

        if not refresh_event:
            refresh_event = []
        if isinstance(refresh_event, BoundEvent):
            refresh_event = [refresh_event]
        for ev in refresh_event:
            self.framework.observe(ev, self.handle_send_data_event)

        self.framework.observe(
            self._charm.on[self._relation_name].relation_joined, self.handle_send_data_event
        )
        # Observe leader elected events because only the leader should send data, and we don't want to miss a case where
        # the relation_joined event happens during a leadership change.
        self.framework.observe(self._charm.on.leader_elected, self.handle_send_data_event)

    def handle_send_data_event(self, _: EventBase) -> None:
        """Handle events that should send data to the relation."""
        if self._charm.unit.is_leader():
            self.send_data()

    def _get_relations(self):
        """Return the applications related to us under the monitored relation."""
        return self._charm.model.relations.get(self._relation_name, ())

    def send_data(self):
        """Post istio-info to all related applications.

        If the calling charm needs to handle cases where the data cannot be sent, it should observe the
        send_info_failed event.  This, however, is better handled by including a check on the is_ready method
        in the charm's collect_status event.
        """
        info_relations = self._get_relations()
        for relation in info_relations:
            dump_to_databag(self._data, relation.data[self._charm.app])

    def _is_relation_data_up_to_date(self):
        """Confirm that the Istio info data we should publish is published to all related applications."""
        expected_app_data = self._data
        for relation in self._get_relations():
            try:
                app_data = load_from_databag(self._data.__class__, (relation.data[self._charm.app]))
            except ValidationError:
                return False
            if app_data != expected_app_data:
                return False
        return True

    def is_ready(self):
        """Return whether the data has been published to all related applications.

        Useful for charms that handle the collect_status event.
        """
        return self._is_relation_data_up_to_date()


# Note: MutableMapping is imported from the typing module and not collections.abc
# because subscripting collections.abc.MutableMapping was added in python 3.9, but
# most of our charms are based on 20.04, which has python 3.8.
_RawDatabag = MutableMapping[str, str]


# Adapted from https://github.com/canonical/cos-lib/blob/main/src/cosl/interfaces/utils.py's DatabagModelV2
def load_from_databag(model: Type[BaseModel], databag: Optional[_RawDatabag]) -> BaseModel:
    """Load a pydantic model from a Juju databag."""
    try:
        return model.model_validate_json(json.dumps(dict(databag)))  # type: ignore
    except ValidationError as e:
        msg = f"failed to validate databag: {databag}"
        if databag:
            log.debug(msg, exc_info=True)
        raise e


def dump_to_databag(data: BaseModel, databag: Optional[_RawDatabag] = None, clear: bool = True) -> _RawDatabag:
    """Write the contents of a pydantic model to a Juju databag.

    :param data: the data model instance to write the data from.
    :param databag: the databag to write the data to.
    :param clear: ensure the databag is cleared before writing it.
    """
    _databag: _RawDatabag = {} if databag is None else databag

    if clear:
        _databag.clear()

    dct = data.model_dump(mode="json", by_alias=True, exclude_defaults=True, round_trip=True)  # type: ignore
    _databag.update(dct)
    return _databag


# Code specific to this library implementation

# Interface schema

class GrafanaMetadataAppData(BaseModel):
    """Data model for the grafana-info interface."""

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
