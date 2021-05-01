import logging
from ops.charm import CharmEvents
from ops.framework import StoredState, EventSource, EventBase
from ops.relation import ProviderBase

# import pprint

import grafana_config
logger = logging.getLogger(__name__)


class GrafanaSourcesChanged(EventBase):
    def __init__(self, handle, data=None):
        super().__init__(handle)
        self.data = data

    def snapshot(self):
        return {"data": self.data}

    def restore(self, snapshot):
        self.data = snapshot["data"]


class GrafanaSourcesToDeleteChanged(EventBase):
    def __init__(self, handle, data=None):
        super().__init__(handle)
        self.data = data

    def snapshot(self):
        return {"data": self.data}

    def restore(self, snapshot):
        self.data = snapshot["data"]


class GrafanaSourceEvents(CharmEvents):
    grafana_sources_changed = EventSource(GrafanaSourcesChanged)
    grafana_sources_to_delete_changed = EventSource(GrafanaSourcesToDeleteChanged)


class GrafanaProvider(ProviderBase):
    on = GrafanaSourceEvents()
    _stored = StoredState()

    def __init__(self, charm, name, service, version=None):
        super().__init__(charm, name, service, version)
        self.charm = charm

        self._stored.set_default(sources=dict())  # available data sources
        self._stored.set_default(sources_to_delete=set())

        events = self.charm.on[name]

        self.framework.observe(events.relation_changed,
                               self._on_grafana_source_relation_changed)
        self.framework.observe(events.relation_broken,
                               self._on_grafana_source_relation_broken)

    def _on_grafana_source_relation_changed(self, event):
        """Get relation data for Grafana source.

        This event handler (if the unit is the leader) will get data for
        an incoming grafana-source relation and make the relation data
        is available in the app's datastore object (StoredState).
        """
        if not self.charm.unit.is_leader():
            return

        rel_id = event.relation.id
        data = event.relation.data[event.unit]

        # dictionary of all the required/optional datasource field values
        # using this as a more generic way of getting data source fields
        datasource_fields = {
            field: data.get(field) for field in
            grafana_config.REQUIRED_DATASOURCE_FIELDS | grafana_config.OPTIONAL_DATASOURCE_FIELDS
        }

        # This should NOT be so hard to get, but private-address no longer appears to be part
        # of the default event data. Maybe a framework bug?
        datasource_fields['private-address'] = \
            str(self.model.get_binding(event.relation.name).network.bind_address)

        missing_fields = [
            field
            for field in grafana_config.REQUIRED_DATASOURCE_FIELDS
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
                "No name 'grafana-source' or provided name is already in use. "
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
        datasource_fields["unit_name"] = event.unit.name

        # add the new datasource relation data to the current state
        new_source_data = {
            field: value
            for field, value in datasource_fields.items()
            if value is not None
        }

        self._stored.sources.update({rel_id: new_source_data})
        self.on.grafana_sources_changed.emit()

    def _on_grafana_source_relation_broken(self, event):
        if not self.charm.unit.is_leader():
            return

        rel_id = event.relation.id

        self._remove_source_from_datastore(rel_id)
        try:
            self._remove_source_from_datastore(rel_id)
            self.on.grafana_sources_changed.emit()
        except KeyError:
            logger.warning("Could not remove source for relation: {}".format(rel_id))

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

    def sources(self):
        sources = []
        for source in self._stored.sources.values():
            sources.append(source)

        return sources

    def sources_to_delete(self):
        sources_to_delete = []
        for source in self._stored.sources_to_delete:
            sources_to_delete.append(source)

        return sources_to_delete
