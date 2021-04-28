import logging
from ops.framework import StoredState
from ops.relation import ConsumerBase

LIBID = "1234"
LIBAPI = 1
LIBPATCH = 0
logger = logging.getLogger(__name__)


class GrafanaConsumer(ConsumerBase):
    _stored = StoredState()

    def __init__(self, charm, name, consumes, multi=False):
        super().__init__(charm, name, consumes, multi)

        self.charm = charm
        self.relation_name = name

        self._stored.set_default(sources=dict())  # available data sources
        self._stored.set_default(sources_to_delete=set())

        events = self.charm.on[self.relation_name]

        self.framework.observe(events.relation_joined,
                               self._update_grafana_sources)

    def add_source(self, source, rel_id=None):
        if rel_id is None:
            rel_id = super()._stored.relation_id

        self._update_sources(source, rel_id)

    def remove_source(self, source, rel_id=None):
        if rel_id is None:
            rel_id = super()._stored.relation_id

        try:
            removed_source = self._stored.sources.pop(rel_id, None)
            self._stored.sources_to_delete.add(removed_source["source-name"])
            self.on.sources_to_delete_changed.emit()
        except KeyError:
            return

        self._update_sources(removed_source, rel_id)

    def _update_grafana_sources(self, event):
        rel_id = event.relation.id
        if not self._stored.sources.get(rel_id, {}):
            return

        event.relation.data[rel_id] = self._stored.sources[rel_id]

    def _update_sources(self, source, rel_id):
        self._stored.sources[rel_id] = source
        rel = self.framework.model.get_relation(self.relation_name, rel_id)
        rel.data[self.charm.app] = source
