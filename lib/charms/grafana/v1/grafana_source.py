import json
import logging

from collections import namedtuple
from ops.charm import CharmBase, CharmEvents, RelationBrokenEvent, RelationChangedEvent
from ops.framework import EventBase, EventSource, StoredState
from ops.relation import ConsumerBase, ProviderBase

from . import config

LIBID = "987654321"
LIBAPI = 1
LIBPATCH = 0

logger = logging.getLogger(__name__)

SourceData = namedtuple("SourceData", "name unit app rel_id data")


class SourceFieldsMissingError(Exception):
    pass


class GrafanaSourcesChanged(EventBase):
    """Event emitted when Grafana sources change"""

    def __init__(self, handle, data=None):
        super().__init__(handle)
        self.data = data

    def snapshot(self):
        """Save grafana source information"""
        return {"data": self.data}

    def restore(self, snapshot):
        """Restore grafana source information"""
        self.data = snapshot["data"]


class GrafanaSourceEvents(CharmEvents):
    """Events raised by :class:`GrafanaSourceEvents`"""

    sources_changed = EventSource(GrafanaSourcesChanged)
    sources_to_delete_changed = EventSource(GrafanaSourcesChanged)


def _validate(self, source: SourceData) -> dict:
    """Check whether given source data is valid. If it is missing optional
    fields only, those are set from defaults. If it is missing required fields,
    `False` is returned. If not, correct defaults are substituted.

    Args:
        self: A :class:`GrafanaConsumer` or :class:`GrafanaProvider` object
        source: A :dict: representing the source data
    """

    def source_name_in_use(source_name):
        return any(
            [s["source-name"] == source_name for s in self._stored.sources.values()]
        )

    def check_required_fields(source_data: dict):
        # dictionary of all the required/optional datasource field values
        # using this as a more generic way of getting data source fields
        validated_source = {
            field: source_data.get(field)
            for field in config.REQUIRED_DATASOURCE_FIELDS
            | config.OPTIONAL_DATASOURCE_FIELDS
        }

        validated_source["address"] = (
            source_data.get("address")
            if "address" in source_data.keys()
            else source_data.get("private-address")
        )

        missing_fields = [
            field
            for field in config.REQUIRED_DATASOURCE_FIELDS
            if validated_source.get(field) is None
        ]

        # check the relation data for missing required fields
        if len(missing_fields) > 0:
            logger.error(
                "Missing required data fields for grafana-source "
                "relation: {}".format(missing_fields)
            )

            logger.error("Removing bad datasource from the configuration")

            if self._stored.sources.get(source.rel_id, None) is not None:
                self._remove_source_from_datastore(source.rel_id)

            raise SourceFieldsMissingError(
                "Missing required data fields for " "grafana-source relation: ",
                missing_fields,
            )

    def set_defaults():
        # specifically handle optional fields if necessary
        # check if source-name was not passed or if we have already saved the provided name
        if source.data.get("source-name") is None or source_name_in_use(
            source.data.get("source-name")
        ):
            default_source_name = "{}_{}".format(source.name, source.rel_id)
            logger.warning(
                "'source-name' not specified' or provided name is already in use. "
                "Using safe default: {}.".format(default_source_name)
            )
            source.data["source-name"] = default_source_name

        # set the first grafana-source as the default (needed for pod config)
        # if `self._stored.sources` is currently empty, this is the first
        source.data["isDefault"] = "false" if dict(self._stored.sources) else "true"

        # normalize the new datasource relation data
        data = {
            field: value for field, value in source.data.items() if value is not None
        }

        return data

    check_required_fields(source.data)
    return set_defaults()


class GrafanaSourceConsumer(ConsumerBase):
    _stored = StoredState()

    def __init__(
        self, charm: CharmBase, name: str, consumes: dict, multi=False
    ) -> None:
        """Construct a Grafana charm client.

        The :class:`GrafanaConsumer` object provides an interface
        to Grafana. This interface supports providing additional
        sources for Grafana to monitor. For example, if a charm
        exposes some metrics which are consumable by a dashboard
        (such as Prometheus), then an additional source can be added
        by instantiating a :class:`GrafanaConsumer` object and
        adding its datasources as follows:

            self.grafana = GrafanaConsumer(self, "grafana-source", {"grafana-source"}: ">=1.0"})
            self.granfana.add_source({
                "source-type": <source-type>,
                "address": <address>,
                "port": <port>
            })

        Args:

            charm: a :class:`CharmBase` object which manages this
                :class:`GrafanaConsumer` object. Generally this is
                `self` in the instantiating class.
            name: a :string: name of the relation between `charm`
                the Grafana charmed service.
            consumes: a :dict: of acceptable monitoring service
                providers. The keys of the dictionary are :string:
                names of grafaba siyrce service providers. Typically,
                this is `grafana-source`. The values of the dictionary
                are corresponding minimal acceptable semantic versions
                for the service.
            multi: an optional (default `False`) flag to indicate if
                this object should support interacting with multiple
                service providers.

        """
        super().__init__(charm, name, consumes, multi)

        self.charm = charm
        events = self.charm.on[name]

        self._stored.set_default(sources=dict())  # available data sources
        self._stored.set_default(sources_to_delete=set())
        self.framework.observe(
            events.relation_changed, self._update_sources
        )

    def add_source(self, data: dict, rel_id=None) -> None:
        """Add an additional source to the Grafana source service.

        Args:
            data: a :dict: object of the source to monitor,
                in the format of:
                {
                "source-type": <source-type>,
                "address": <address>,
                "port": <port>,
                "source-name": <source-name> (optional),
                }
            rel_id: an optional integer specifying the relation ID
                for the grafana source service, only required if the
                :class:`GrafanaConsumer` has been instantiated in
                `multi` mode.

        """
        rel = self.framework.model.get_relation(self.name, rel_id)

        source_data = SourceData(
            self.name,
            self.charm.unit,
            rel.app,
            rel_id,
            data,
        )

        try:
            data = _validate(self, source_data)
        except SourceFieldsMissingError as e:
            logger.critical(
                f"Missing data on added grafana-k8s source {e}", exc_info=True
            )
            return

        rel.data[self.charm.app]["sources"] = json.dumps(data)
        self._stored.sources[rel_id] = data

    def remove_source(self, rel_id=None) -> None:
        """Removes a source relation.

        Args:
            rel_id: an optional integer specifying the relation ID
                for the grafana source service, only required if the
                :class:`GrafanaConsumer` has been instantiated in
                `multi` mode.
        """
        rel = self.framework.model.get_relation(self.name, rel_id)

        if rel_id is None:
            rel_id = rel.id

        rel.data[self.charm.app].pop("sources")
        source = self._stored.sources.pop(rel_id)

        if source is not None:
            self._stored.sources_to_delete.add(source["source-name"])

    def list_sources(self) -> []:
        """Returns an array of currently valid sources"""
        sources = []
        for source in self._stored.sources.values():
            sources.append(source)

        return sources

    @property
    def removed_source_names(self) -> []:
        """Returns an array of source names which have been removed"""
        sources = []
        for source in self._stored.sources_to_delete:
            sources.append(source)

        return sources

    def _update_sources(self, event: RelationChangedEvent) -> None:
        """
        Update the stored grafana sources if this is not a
        :class:`RelationBrokenEvent` and :class:`GrafanaConsumer`
        has previously seen this relation and has stored sources
        """
        rel_id = event.relation.id
        if not self._stored.sources.get(rel_id, {}):
            return

        if type(event) is RelationBrokenEvent:
            return

        event.relation.data[rel_id]["sources"] = self._stored.sources[rel_id]


class GrafanaSourceProvider(ProviderBase):
    on = GrafanaSourceEvents()
    _stored = StoredState()

    def __init__(self, charm: CharmBase, name: str, service: str, version=None) -> None:
        """A Grafana based Monitoring service consumer

        Args:
            charm: a :class:`CharmBase` instance that manages this
                instance of the Grafana source service.
            name: string name of the relation that is provides the
                Grafana source service.
            service: string name of service provided. This is used by
                :class:`GrafanaProvider` to validate this service as
                acceptable. Hence the string name must match one of the
                acceptable service names in the :class:`GrafanaSourceProvider`s
                `consumes` argument. Typically this string is just "grafana".
            version: a string providing the semantic version of the Grafana
                source being provided.

        """
        super().__init__(charm, name, service, version)
        self.charm = charm
        events = self.charm.on[name]

        self._stored.set_default(sources=dict())  # available data sources
        self._stored.set_default(sources_to_delete=set())

        self.framework.observe(
            events.relation_changed, self.on_grafana_source_relation_changed
        )
        self.framework.observe(
            events.relation_broken, self.on_grafana_source_relation_broken
        )

    def on_grafana_source_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle relation changes in related consumers.

        If there are changes in relations between Grafana source providers
        and consumers, this event handler (if the unit is the leader) will
        get data for an incoming grafana-source relation through a
        :class:`GrafanaSourcesChanged` event, and make the relation data
        is available in the app's datastore object. The Grafana charm can
        then respond to the event to update its configuration
        """
        if not self.charm.unit.is_leader():
            return

        rel_id = event.relation.id
        data = event.relation.data[event.app]

        data = json.loads(data.get("sources", {}))
        if not data:
            return

        source = SourceData(event.app.name, event.unit, event.app, rel_id, data)

        try:
            data = _validate(self, source)
        except SourceFieldsMissingError as e:
            logger.critical(
                f"Missing data on added grafana-k8s source {e}", exc_info=True
            )
            return

        self._stored.sources[rel_id] = data
        self.on.sources_changed.emit()

    def on_grafana_source_relation_broken(self, event: RelationBrokenEvent) -> None:
        """Update job config when consumers depart.

        When a Grafana source consumer departs, the configuration
        for that consumer is removed from the list of sources jobs,
        added to a list of sources to remove, and other consumers
        are informed through a :class:`GrafanaSourcesChanged` event.
        """
        if not self.charm.unit.is_leader():
            return

        rel_id = event.relation.id
        self._remove_source_from_datastore(rel_id)

    def _remove_source_from_datastore(self, rel_id: int) -> None:
        """Remove the grafana-source from the datastore. and add the
        name to the list of sources to remove when a relation is
        broken.
        """

        logger.info("Removing all data for relation: {}".format(rel_id))

        try:
            removed_source = self._stored.sources.pop(rel_id, None)
            self._stored.sources_to_delete.add(removed_source["source-name"])
            self.on.sources_to_delete_changed.emit()
        except KeyError:
            logger.warning("Could not remove source for relation: {}".format(rel_id))

    def sources(self) -> []:
        """Returns an array of sources the provdier knows about"""
        sources = []
        for source in self._stored.sources.values():
            sources.append(source)

        return sources

    def update_port(self, relation_name: str, port: int) -> None:
        if self.charm.unit.is_leader():
            for relation in self.charm.model.relations[relation_name]:
                logger.info("Setting address data for relation", relation)
                if str(port) != relation.data[self.charm.app].get("port", None):
                    relation.data[self.charm.app]["port"] = str(port)

    def sources_to_delete(self) -> []:
        """Returns an array of source names which have been removed"""
        sources_to_delete = []
        for source in self._stored.sources_to_delete:
            sources_to_delete.append(source)

        return sources_to_delete
