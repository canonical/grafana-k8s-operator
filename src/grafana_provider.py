import logging
from ops.charm import CharmEvents
from ops.framework import StoredState, EventSource, EventBase
from ops.relation import ProviderBase

import config
logger = logging.getLogger(__name__)


class SourcesChanged(EventBase):
    def __init__(self, handle, data=None):
        super().__init__(handle)
        self.data = data

    def snapshot(self):
        return {"data": self.data}

    def restore(self, snapshot):
        self.data = snapshot["data"]


class MonitoringEvents(CharmEvents):
    sources_changed = EventSource(SourcesChanged)


class MonitoringProvider(ProviderBase):
    on = MonitoringEvents()
    _stored = StoredState()

    def __init__(self, charm, name, service, version=None):
        super().__init__(charm, name, service, version)
        self.charm = charm
        self._stored.set_default(jobs={})
        events = self.charm.on[name]
        self.framework.observe(events.relation_changed,
                               self._on_grafana_source_relation_changed)
        self.framework.observe(events.relation_broken,
                               self._on_grafana_source_relation_broken)

    def _on_grafana_source_relation_changed(self, event):
        if not self.charm.unit.is_leader():
            return

        rel_id = event.relation.id
        data = event.relation.data[event.app]

        # dictionary of all the required/optional datasource field values
        # using this as a more generic way of getting data source fields
        source_fields = \
            {field: data.get(field) for field in config.REQUIRED_DATASOURCE_FIELDS |
             config.OPTIONAL_DATASOURCE_FIELDS}

        missing_fields = [field for field
                          in config.REQUIRED_DATASOURCE_FIELDS
                          if source_fields.get(field) is None]

        # check the relation data for missing required fields
        if len(missing_fields) > 0:
            logger.error("Missing required data fields for grafana-source "
                         "relation: {}".format(missing_fields))
            return

        # specifically handle optional fields if necessary
        # check if source-name was not passed or if we have already saved the provided name
        if source_fields['source-name'] is None \
                or source_fields['source-name'] in self._stored.source_names:
            default_source_name = '{}_{}'.format(
                event.app.name,
                rel_id
            )
            logger.warning("No name 'grafana-source' or provided name is already in use. "
                           "Using safe default: {}.".format(default_source_name))
            source_fields['source-name'] = default_source_name

        # set the first grafana-source as the default (needed for pebble config)
        # if `self._stored.sources` is currently empty, this is the first
        source_fields['isDefault'] = 'false'
        if not dict(self._stored.sources):
            source_fields['isDefault'] = 'true'

        # add unit name so the source can be removed might be a
        # duplicate of 'source-name', but this will guarantee lookup
        source_fields['unit_name'] = event.unit.name

        # add the new datasource relation data to the current state
        new_source_data = {
            field: value for field, value in source_fields.items()
            if value is not None
        }

        self._stored.sources['rel_id'] = new_source_data
        self.on.sources_changed.emit()

    def _on_grafana_source_relation_broken(self, event):
        if not self.charm.unit.is_leader():
            return

        rel_id = event.relation.id
        try:
            del self._stored.sources[rel_id]
            self.on.sources_changed.emit()
        except KeyError:
            pass

    def sources(self):
        sources = []
        for source in self._stored.sources:
            sources.append(source)

        return sources
