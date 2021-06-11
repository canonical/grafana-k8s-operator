import json
import logging

from ops.charm import CharmBase, RelationBrokenEvent, RelationChangedEvent
from ops.framework import StoredState
from ops.relation import ProviderBase
from typing import List

from .consumer import (
    GrafanaSourceEvents,
    SourceData,
    SourceFieldsMissingError,
    _validate,
)

logger = logging.getLogger(__name__)


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

        rel = event.relation
        rel_type = event.unit if event.unit else event.app

        data = (
            json.loads(event.relation.data[rel_type].get("sources", {}))
            if event.relation.data[rel_type].get("sources", {})
            else None
        )
        if not data:
            return

        source = SourceData(event.app.name, event.unit, event.app, rel.id, data)
        try:
            data = _validate(self, source)
        except SourceFieldsMissingError as e:
            logger.critical(
                f"Missing data on added grafana-k8s source {e}", exc_info=True
            )
            return

        self._stored.sources[rel.id] = data
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
            if removed_source:
                self._stored.sources_to_delete.add(removed_source["source-name"])
                self.on.sources_to_delete_changed.emit()
        except KeyError:
            logger.warning("Could not remove source for relation: {}".format(rel_id))

    @property
    def sources(self) -> List[dict]:
        """Returns an array of sources the source_provider knows about"""
        sources = []
        for source in self._stored.sources.values():
            sources.append(source)

        return sources

    def update_port(self, relation_name: str, port: int) -> None:
        if self.charm.unit.is_leader():
            for relation in self.charm.model.relations[relation_name]:
                logger.debug("Setting grafana-k8s address data for relation", relation)
                if str(port) != relation.data[self.charm.app].get("port", None):
                    relation.data[self.charm.app]["port"] = str(port)

    @property
    def sources_to_delete(self) -> List[str]:
        """Returns an array of source names which have been removed"""
        sources_to_delete = []
        for source in self._stored.sources_to_delete:
            sources_to_delete.append(source)

        return sources_to_delete
