import json
import logging

from ops.charm import CharmEvents
from ops.framework import StoredState, EventSource, EventBase

from config import *
from relation import ProviderBase

logger = logging.getLogger(__name__)


class GrafanaSourcesChanged(EventBase):
    def __init__(self, handle, data=None):
        super().__init__(handle)
        self.data = data

    def snapshot(self):
        return {"data": self.data}

    def restore(self, snapshot):
        self.data = snapshot["data"]


class GrafanaSourceEvents(CharmEvents):
    grafana_sources_changed = EventSource(GrafanaSourcesChanged)
    grafana_sources_to_delete_changed = EventSource(GrafanaSourcesChanged)


class GrafanaSourceProvider(ProviderBase):
    on = GrafanaSourceEvents()
    _stored = StoredState()

    def __init__(self, charm, name, service, version=None):
        super().__init__(charm, name, service, version)
        self.charm = charm

        self._stored.set_default(sources=dict())  # available data sources
        self._stored.set_default(sources_to_delete=set())
        self._stored.set_default(dashboards=set())

        events = self.charm.on[name]

        self.framework.observe(events.relation_changed,
                               self.on_grafana_source_relation_changed)
        self.framework.observe(events.relation_broken,
                               self.on_grafana_source_relation_broken)

    def on_grafana_source_relation_changed(self, event):
        """Get relation data for Grafana source.

        This event handler (if the unit is the leader) will get data for
        an incoming grafana-source relation and make the relation data
        is available in the app's datastore object (StoredState).
        """
        if not self.charm.unit.is_leader():
            return

        rel_id = event.relation.id
        data = event.relation.data[event.app]

        sources = json.loads(data.get('sources', {}))
        if not sources:
            return

        # dictionary of all the required/optional datasource field values
        # using this as a more generic way of getting data source fields
        datasource_fields = {
            field: sources.get(field) for field in
            REQUIRED_DATASOURCE_FIELDS | OPTIONAL_DATASOURCE_FIELDS
        }

        missing_fields = [
            field for field in REQUIRED_DATASOURCE_FIELDS
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
        if (
            datasource_fields["source-name"] is None
            or self._source_name_in_use(datasource_fields["source-name"])
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
        self.on.grafana_sources_changed.emit()

    def on_grafana_source_relation_broken(self, event):
        if not self.charm.unit.is_leader():
            return

        rel_id = event.relation.id
        self._remove_source_from_datastore(rel_id)

    def _remove_source_from_datastore(self, rel_id):
        """Remove the grafana-source from the datastore."""

        logger.info("Removing all data for relation: {}".format(rel_id))

        try:
            removed_source = self._stored.sources.pop(rel_id, None)
            self._stored.sources_to_delete.add(removed_source["source-name"])
            self.on.grafana_sources_to_delete_changed.emit()
        except KeyError:
            logger.warning("Could not remove source for relation: {}".format(rel_id))

    def _source_name_in_use(self, source_name):
        return any([s["source-name"] == source_name for s in self._stored.sources.values()])

    def update_port(self, relation_name, port):
        if self.charm.unit.is_leader():
            for relation in self.charm.model.relations[relation_name]:
                logger.info("Setting address data for relation", relation)
                if str(port) != relation.data[self.charm.app].get(
                        "port", None
                ):
                    relation.data[self.charm.app]["port"] = str(port)

    def sources(self):
        """Returns an array of sources"""
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
