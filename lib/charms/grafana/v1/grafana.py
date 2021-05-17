import json
import logging

from ops.charm import RelationBrokenEvent
from ops.framework import StoredState
from ops.relation import ConsumerBase

LIBID = "987654321"
LIBAPI = 1
LIBPATCH = 0

logger = logging.getLogger(__name__)


class GrafanaSourceConsumer(ConsumerBase):
    _stored = StoredState()

    def __init__(self, charm, name, consumes, multi=False):
        super().__init__(charm, name, consumes, multi)

        self.charm = charm
        self.relation_name = name

        self._stored.set_default(sources=dict())  # available data sources
        self._stored.set_default(sources_to_delete=set())
        self._stored.set_default(dashboards=set())
        events = self.charm.on[self.relation_name]
        self.framework.observe(events.relation_joined,
                               self._update_sources)

    def add_source(self, source_data, rel_id=None):
        """
        {"isDefault": <bool>,
         "source-name": <source-name>,
         "source-type": <source-type<,
         "private-address": <private-address>,
         "port": <port>
        }

        Keyword arguments:
        rel_id -- the relation ID to add this source to
        """
        rel = self.framework.model.get_relation(self.relation_name, rel_id)

        rel.data[self.charm.app]["sources"] = json.dumps(source_data)
        self._stored.sources[rel_id] = source_data

    def remove_source(self, rel_id=None):
        """
        Removes a source relation.

        Keyword arguments:
        rel_id -- the relation ID to remove this source from
        """
        rel = self.framework.model.get_relation(self.relation_name, rel_id)

        if rel_id is None:
            rel_id = rel.id

        rel.data[self.charm.app].pop("sources")
        source = self._stored.sources.pop(rel_id)

        if source is not None:
            self._stored.sources_to_delete.add(source['source-name'])

    def list_sources(self):
        """Returns an array of sources"""
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
        rel_id = event.relation.id
        if not self._stored.sources.get(rel_id, {}):
            return

        if type(event) is RelationBrokenEvent:
            return

        event.relation.data[rel_id]["sources"] = self._stored.sources[rel_id]
