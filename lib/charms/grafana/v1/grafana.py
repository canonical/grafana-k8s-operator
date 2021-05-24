import json
import logging

from ops.charm import CharmEvents, RelationBrokenEvent
from ops.framework import EventBase, EventSource, StoredState
from ops.relation import ConsumerBase, ProviderBase

from . import config

LIBID = "987654321"
LIBAPI = 1
LIBPATCH = 0

logger = logging.getLogger(__name__)


def _get_defaults(self, source_name):
    """Check whether a source name is already in use, since Grafana
    does not gracefully handle duplicate names.
    """
    return any(
        [s["source-name"] == source_name for s in self._stored.sources.values()]
    )


class GrafanaSourceConsumer(ConsumerBase):
    _stored = StoredState()

    def __init__(self, charm, name, consumes, multi=False):
        """Construct a Grafana charm client.

        The :class:`GrafanaConsumer` object provides an interface
        to Grafana. This interface supports providing additional
        sources for Grafana to monitor. For example, if a charm
        exposes some metrics which are consumable by a dashboard
        (such as Prometheus), then an additional source can be added
        by instantiating a :class:`GrafanaConsumer` object and
        adding its datasources as follows:

            self.grafana = GrafanaConsumer(self, "monitoring", {"grafana-source"}: ">=1.0"})
            self.grana.add_source({
                "source-type": <source-type>,
                "address": <address>
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
        self._relation_name = name

        self._stored.set_default(sources=dict())  # available data sources
        self._stored.set_default(sources_to_delete=set())
        self._stored.set_default(dashboards=set())
        events = self.charm.on[self._relation_name]
        self.framework.observe(events.relation_joined, self._update_sources)

    def add_source(self, source_data, rel_id=None):
        """Add an additional source to the Grafana source service.

        Args:
            source_data: a :dict: object of the source to monitor,
                in the format of:
                {
                "source-type": <source-type<,
                "address": <address>,
                "port": <port>,
                "source-name": <source-name> (optional),
                }
            rel_id: an optional integer specifying the relation ID
                for the grafana source service, only required if the
                :class:`GrafanaConsumer` has been instantiated in
                `multi` mode.

        """
        rel = self.framework.model.get_relation(self._relation_name, rel_id)

        if source_data["source-name"] is None or _get_defaults(
            self, source_data["source-name"]
        ):
            default_source_name = "{}_{}".format(self._relation_name, rel_id)
            logger.warning(
                "'source-name' not specified' or provided name is already in use. "
                "Using safe default: {}.".format(default_source_name)
            )
            source_data["source-name"] = default_source_name

        rel.data[self.charm.app]["sources"] = json.dumps(source_data)
        self._stored.sources[rel_id] = source_data

    def remove_source(self, rel_id=None):
        """Removes a source relation.

        Args:
            rel_id: an optional integer specifying the relation ID
                for the grafana source service, only required if the
                :class:`GrafanaConsumer` has been instantiated in
                `multi` mode.
        """
        rel = self.framework.model.get_relation(self._relation_name, rel_id)

        if rel_id is None:
            rel_id = rel.id

        rel.data[self.charm.app].pop("sources")
        source = self._stored.sources.pop(rel_id)

        if source is not None:
            self._stored.sources_to_delete.add(source["source-name"])

    def list_sources(self):
        """Returns an array of currently valid sources"""
        sources = []
        for source in self._stored.sources.values():
            sources.append(source)

        return sources

    @property
    def removed_source_names(self):
        """Returns an array of source names which have been removed"""
        sources = []
        for source in self._stored.sources_to_delete:
            sources.append(source)

        return sources

    def _update_sources(self, event):
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


class GrafanaSourceProvider(ProviderBase):
    on = GrafanaSourceEvents()
    _stored = StoredState()

    def __init__(self, charm, name, service, version=None):
        """A Grafana based Monitoring service provider

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

        self._stored.set_default(sources=dict())  # available data sources
        self._stored.set_default(sources_to_delete=set())
        self._stored.set_default(dashboards=set())

        events = self.charm.on[name]

        self.framework.observe(
            events.relation_changed, self.on_grafana_source_relation_changed
        )
        self.framework.observe(
            events.relation_broken, self.on_grafana_source_relation_broken
        )

    def on_grafana_source_relation_changed(self, event):
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

        sources = json.loads(data.get("sources", {}))
        if not sources:
            return

        # dictionary of all the required/optional datasource field values
        # using this as a more generic way of getting data source fields
        datasource_fields = {
            field: sources.get(field)
            for field in config.REQUIRED_DATASOURCE_FIELDS
            | config.OPTIONAL_DATASOURCE_FIELDS
        }

        missing_fields = [
            field
            for field in config.REQUIRED_DATASOURCE_FIELDS
            if datasource_fields.get(field) is None
        ]

        # check the relation data for missing required fields
        if len(missing_fields) > 0:
            logger.error(
                "Missing required data fields for grafana-source "
                "relation: {}".format(missing_fields)
            )
            if self._stored.sources.get(rel_id, None) is not None:
                self._remove_source_from_datastore(rel_id)
            return

        # specifically handle optional fields if necessary
        # check if source-name was not passed or if we have already saved the provided name
        if datasource_fields["source-name"] is None or _get_defaults(
            self, datasource_fields["source-name"]
        ):
            default_source_name = "{}_{}".format(event.app.name, rel_id)
            logger.warning(
                "'source-name' not specified' or provided name is already in use. "
                "Using safe default: {}.".format(default_source_name)
            )
            datasource_fields["source-name"] = default_source_name

        # set the first grafana-source as the default (needed for pod config)
        # if `self._stored.sources` is currently empty, this is the first
        datasource_fields["isDefault"] = "false"
        if not dict(self._stored.sources):
            datasource_fields["isDefault"] = "true"

        # add unit name so the source can be removed might be a
        # duplicate of 'source-name', but this will guarantee lookup
        datasource_fields["unit_name"] = event.unit

        # add the new datasource relation data to the current state
        new_source_data = {
            field: value
            for field, value in datasource_fields.items()
            if value is not None
        }

        self._stored.sources[rel_id] = new_source_data
        self.on.sources_changed.emit()

    def on_grafana_source_relation_broken(self, event):
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

    def _remove_source_from_datastore(self, rel_id):
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

    def _source_name_in_use(self, source_name):
        """Check whether a source name is already in use, since Grafana
        does not gracefully handle duplicate names.
        """
        return any(
            [s["source-name"] == source_name for s in self._stored.sources.values()]
        )

    def sources(self):
        """Returns an array of sources the provdier knows about"""
        sources = []
        for source in self._stored.sources.values():
            sources.append(source)

        return sources

    def sources_to_delete(self):
        """Returns an array of source names which have been removed"""
        sources_to_delete = []
        for source in self._stored.sources_to_delete:
            sources_to_delete.append(source)

        return sources_to_delete
