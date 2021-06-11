import json
import logging

from collections import namedtuple
from ops.charm import CharmBase, CharmEvents, RelationBrokenEvent, RelationChangedEvent
from ops.framework import EventBase, EventSource, StoredState
from ops.relation import ConsumerBase
from typing import List


LIBID = "987654321"
LIBAPI = 1
LIBPATCH = 0

logger = logging.getLogger(__name__)

SourceData = namedtuple("SourceData", "name unit app rel_id data")
REQUIRED_DATASOURCE_FIELDS = {
    "address",  # the hostname/IP of the data source server
    "port",  # the port of the data source server
    "source-type",  # the data source type (e.g. prometheus)
}

OPTIONAL_DATASOURCE_FIELDS = {
    "source-name",  # a human-readable name of the source
}


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
            for field in REQUIRED_DATASOURCE_FIELDS | OPTIONAL_DATASOURCE_FIELDS
        }

        validated_source["address"] = (
            source_data.get("address")
            if "address" in source_data.keys()
            else source_data.get("private-address")
        )

        missing_fields = [
            field
            for field in REQUIRED_DATASOURCE_FIELDS
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

            self.grafana = GrafanaConsumer(self, "grafana-source", {"grafana-source"}: ">=2.0"})
            self.grafana.add_source({
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
                names of grafana source service providers. Typically,
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
        self.framework.observe(events.relation_changed, self._on_relation_changed)
        self.framework.observe(events.relation_broken, self._on_relation_broken)

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

        rel.data[self.charm.unit]["sources"] = json.dumps(data)
        self._stored.sources[rel_id] = data
        self.on.available.emit()

    def remove_source(self, rel_id=None) -> None:
        """Removes a source relation.

        Args:
            rel_id: an optional integer specifying the relation ID
                for the grafana-k8s source service, only required if the
                :class:`GrafanaConsumer` has been instantiated in
                `multi` mode.
        """
        rel = self.framework.model.get_relation(self.name, rel_id)

        if rel_id is None:
            rel_id = rel.id

        rel.data[self.charm.unit].pop("sources")
        source = self._stored.sources.pop(rel_id)

        if source is not None:
            self._stored.sources_to_delete.add(source["source-name"])
        self.on.available.emit()

    def list_sources(self) -> List[dict]:
        """Returns an array of currently valid sources"""
        sources = []
        for source in self._stored.sources.values():
            sources.append(source)

        return sources

    @property
    def removed_source_names(self) -> List[str]:
        """Returns an array of source names which have been removed"""
        sources = []
        for source in self._stored.sources_to_delete:
            sources.append(source)

        return sources

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """
        Update the stored grafana sources if this is not a
        :class:`RelationBrokenEvent` and :class:`GrafanaConsumer`
        has previously seen this relation and has stored sources
        """
        rel = event.relation
        rel_type = event.unit if event.unit else event.app

        data = json.loads(event.relation.data[rel_type].get("sources", {}))
        if not data:
            return

        self._stored.sources[rel.id] = _validate(
            self,
            SourceData(
                self.name,
                self.charm.unit,
                rel.app,
                rel.id,
                event.relation.data[rel_type].get("sources")
            )
        )

        event.relation.data[self.charm.unit]["sources"] = json.dumps(self._stored.sources[rel.id])

        self.on.available.emit()

    def _on_relation_broken(self, event: RelationBrokenEvent) -> None:
        """
        Remove any known sources from this relation
        """

        rel_id = event.relation.id
        self.remove_source(rel_id)
        self.on.available.emit()
