# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""A library for working with Grafana dashboards for charm authors."""

import base64
import copy
import json
import logging
import sys
import uuid
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ops.charm import (
    CharmBase,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationCreatedEvent,
    RelationMeta,
    RelationRole,
    UpgradeCharmEvent,
)
from ops.framework import (
    EventBase,
    EventSource,
    Object,
    ObjectEvents,
    StoredDict,
    StoredList,
    StoredState,
)
from ops.model import Relation

# The unique Charmhub library identifier, never change it
LIBID = "c49eb9c7dfef40c7b6235ebd67010a3f"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 5

logger = logging.getLogger(__name__)


DEFAULT_RELATION_NAME = "grafana-dashboard"
RELATION_INTERFACE_NAME = "grafana_dashboard"


class RelationNotFoundError(Exception):
    """Raised if there is no relation with the given name."""

    def __init__(self, relation_name: str):
        self.relation_name = relation_name
        self.message = f"No relation named '{relation_name}' found"

        super().__init__(self.message)


class RelationInterfaceMismatchError(Exception):
    """Raised if the relation with the given name has a different interface."""

    def __init__(
        self,
        relation_name: str,
        expected_relation_interface: str,
        actual_relation_interface: str,
    ):
        self.relation_name = relation_name
        self.expected_relation_interface = expected_relation_interface
        self.actual_relation_interface = actual_relation_interface
        self.message = (
            f"The '{relation_name}' relation has '{actual_relation_interface}' as "
            f"interface rather than the expected '{expected_relation_interface}'"
        )

        super().__init__(self.message)


class RelationRoleMismatchError(Exception):
    """Raised if the relation with the given name has a different direction."""

    def __init__(
        self,
        relation_name: str,
        expected_relation_role: RelationRole,
        actual_relation_role: RelationRole,
    ):
        self.relation_name = relation_name
        self.expected_relation_interface = expected_relation_role
        self.actual_relation_role = actual_relation_role
        self.message = (
            f"The '{relation_name}' relation has role '{repr(actual_relation_role)}' "
            f"rather than the expected '{repr(expected_relation_role)}'"
        )

        super().__init__(self.message)


def _validate_relation_by_interface_and_direction(
    charm: CharmBase,
    relation_name: str,
    expected_relation_interface: str,
    expected_relation_role: RelationRole,
) -> str:
    """Verifies that a relation has the necessary characteristics.

    Verifies that the `relation_name` provided: (1) exists in metadata.yaml,
    (2) declares as interface the interface name passed as `relation_interface`
    and (3) has the right "direction", i.e., it is a relation that `charm`
    provides or requires.

    Args:
        charm: a `CharmBase` object to scan for the matching relation.
        relation_name: the name of the relation to be verified.
        expected_relation_interface: the interface name to be matched by the
            relation named `relation_name`.
        expected_relation_role: whether the `relation_name` must be either
            provided or required by `charm`.
    """
    if relation_name not in charm.meta.relations:
        raise RelationNotFoundError(relation_name)

    relation: RelationMeta = charm.meta.relations[relation_name]

    actual_relation_interface = relation.interface_name
    if actual_relation_interface != expected_relation_interface:
        raise RelationInterfaceMismatchError(
            relation_name, expected_relation_interface, actual_relation_interface
        )

    if expected_relation_role == RelationRole.provides:
        if relation_name not in charm.meta.provides:
            raise RelationRoleMismatchError(
                relation_name, RelationRole.provides, RelationRole.requires
            )
    elif expected_relation_role == RelationRole.requires:
        if relation_name not in charm.meta.requires:
            raise RelationRoleMismatchError(
                relation_name, RelationRole.requires, RelationRole.provides
            )
    else:
        raise Exception(f"Unexpected RelationDirection: {expected_relation_role}")


def type_convert_stored(obj):
    """Convert Stored* to their appropriate types, recursively."""
    if isinstance(obj, StoredList):
        rlist = []  # type: List[Any]
        for i in obj:
            rlist.append(type_convert_stored(i))
        return rlist
    elif isinstance(obj, StoredDict):
        rdict = {}  # type: Dict[Any, Any]
        for k in obj.keys():
            rdict[k] = type_convert_stored(obj[k])
        return rdict
    else:
        return obj


class GrafanaDashboardsChanged(EventBase):
    """Event emitted when Grafana dashboards change."""

    def __init__(self, handle, data=None):
        super().__init__(handle)
        self.data = data

    def snapshot(self) -> Dict:
        """Save grafana source information."""
        return {"data": self.data}

    def restore(self, snapshot):
        """Restore grafana source information."""
        self.data = snapshot["data"]


class GrafanaDashboardEvents(ObjectEvents):
    """Events raised by :class:`GrafanaSourceEvents`."""

    dashboards_changed = EventSource(GrafanaDashboardsChanged)


class GrafanaDashboardEvent(EventBase):
    """Event emitted when Grafana dashboards cannot be resolved.

    Enables us to set a clear status on the consumer.
    """

    def __init__(self, handle, error_message: str = "", valid: bool = False):
        super().__init__(handle)
        self.error_message = error_message
        self.valid = valid

    def snapshot(self) -> Dict:
        """Save grafana source information."""
        return {"error_message": self.error_message, "valid": self.valid}

    def restore(self, snapshot):
        """Restore grafana source information."""
        self.error_message = snapshot["error_message"]
        self.valid = snapshot["valid"]


class GrafanaConsumerEvents(ObjectEvents):
    """Events raised by :class:`GrafanaSourceEvents`."""

    dashboard_status_changed = EventSource(GrafanaDashboardEvent)


def resolve_dir_against_main_path(*path_elements: str) -> str:
    """Resolve the provided path items against the directory of the main file.

    Look up the directory of the main .py file being executed. This is normally
    going to be the charm.py file of the charm including this library. Then, resolve
    the provided path elements and, if the result path exists and is a directory,
    return its absolute path; otherwise, return `None`.
    """
    charm_file = sys.path[0]

    default_alerts_dir = Path(charm_file).joinpath(*path_elements)

    if default_alerts_dir.exists() and default_alerts_dir.is_dir:
        return str(default_alerts_dir.absolute())

    return None


class GrafanaDashboardConsumer(Object):
    """A consumer object for Grafana dashboards."""

    _stored = StoredState()
    on = GrafanaConsumerEvents()

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = DEFAULT_RELATION_NAME,
        dashboards_path: Optional[str] = None,
    ) -> None:
        """Construct a Grafana dashboard charm client.

        The :class:`GrafanaDashboardConsumer` object provides an interface
        to Grafana. This interface supports providing additional
        dashboards for Grafana to display. For example, if a charm
        exposes some metrics which are consumable by a dashboard
        (such as Prometheus), then an additional dashboard can be added
        by instantiating a :class:`GrafanaDashboardConsumer` object and
        adding its datasources as follows:

            self.grafana = GrafanaDashboardConsumer(self)

        Args:
            charm: a :class:`CharmBase` object which manages this
                :class:`GrafanaConsumer` object. Generally this is
                `self` in the instantiating class.
            relation_name: a :string: name of the relation between `charm`
                the Grafana charmed service. The default is "grafana-dashboard".
                It is strongly advised not to change the default, so that people
                deploying your charm will have a consistent experience with all
                other charms that consume Grafana dashboards.
            dashboards_path: a filesystem path relative to the charm root
                where dashboard templates can be located. By default, the library
                expects dashboard files to be in the `<charm-py-directory>/grafana_dashboards`
                directory.
        """
        _validate_relation_by_interface_and_direction(
            charm, DEFAULT_RELATION_NAME, RELATION_INTERFACE_NAME, RelationRole.requires
        )

        if not dashboards_path:
            dashboards_path = resolve_dir_against_main_path("grafana_dashboards")

        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self._DASHBOARDS_PATH = dashboards_path
        self._stored.set_default(dashboards={}, dashboard_templates={})

        events = self.charm.on[relation_name]

        self.framework.observe(self.charm.on.upgrade_charm, self._on_upgrade_charm)

        self.framework.observe(
            events.relation_created, self._on_grafana_dashboard_relation_created
        )
        self.framework.observe(
            events.relation_changed, self._on_grafana_dashboard_relation_changed
        )

    def _on_upgrade_charm(self, event: UpgradeCharmEvent) -> None:
        """Refresh the dashboards when the charm is upgraded.

        Args:
            event: A :class:`UpgradeCharmEvent` which triggers the event
        """
        for dashboard_rel in self.charm.model.relations[self.relation_name]:
            self._set_dashboard_data(dashboard_rel)

    def _on_grafana_dashboard_relation_created(self, event: RelationCreatedEvent) -> None:
        """Watch for a relation being created and automatically send dashboards.

        Args:
            event: The :class:`RelationJoinedEvent` sent when a
                `grafana_dashboaard` relationship is joined
        """
        rel = event.relation
        self._set_dashboard_data(rel)

    def _set_dashboard_data(self, rel: Relation) -> None:
        """Watch for a relation being joined and automatically send dashboards.

        Args:
            rel: The :class:`Relation` to set grafana_dashboard data for
        """
        data = {}

        for path in Path(self._DASHBOARDS_PATH).glob("*.tmpl"):
            if not path.is_file():
                continue

            data[path.stem] = base64.b64encode(zlib.compress(path.read_bytes(), 9)).decode()

        self._stored.dashboard_templates[rel.id] = data

        self._update_dashboards(data, rel.id)

    def _on_grafana_dashboard_relation_changed(self, event: RelationChangedEvent) -> None:
        """Watch for changes so we know if there's an error to signal back to the parent charm.

        Args:
            event: The `RelationChangedEvent` that triggered this handler.
        """
        if not self.charm.unit.is_leader():
            return

        rel = self.framework.model.get_relation(self.relation_name, event.relation.id)
        data = json.loads(rel.data[event.app].get("event", "{}"))

        if not data:
            return

        error_message = data.get("errors", "")
        if error_message:
            self.on.dashboard_status_changed.emit(
                error_message=data.get("errors", ""), valid=data.get("valid", False)
            )
            return

        valid_message = data.get("valid", False)
        self.on.dashboard_status_changed.emit(valid=bool(valid_message))

    def _update_dashboards(self, data: dict, rel_id: int) -> None:
        """Update the dashboards in the relation data bucket."""
        if not self.charm.unit.is_leader():
            return

        prom_target = "{} [ {} / {} ]".format(
            self.charm.app.name.capitalize(),
            self.charm.model.name,
            self.charm.model.uuid,
        )

        prom_query = "juju_model='{}',juju_model_uuid='{}',juju_application='{}'".format(
            self.charm.model.name, self.charm.model.uuid, self.charm.app.name
        )

        # It's completely ridiculous to add a UUID, but if we don't have some
        # pseudo-random value, this never makes it across 'juju set-state'
        stored_data = {
            "monitoring_target": prom_target,
            "monitoring_query": prom_query,
            "templates": data,
            "removed": False,
            "invalidated": False,
            "invalidated_reason": "",
            "uuid": str(uuid.uuid4()),
        }
        rel = self.framework.model.get_relation(self.relation_name, rel_id)

        self._stored.dashboards[rel_id] = stored_data
        rel.data[self.charm.app]["dashboards"] = json.dumps(stored_data)

    def remove_dashboard(self, rel_id=None) -> None:
        """Remove a dashboard from Grafana."""
        if not self.charm.unit.is_leader():
            return

        rel = self.framework.model.get_relation(self.relation_name, rel_id)

        # The relation may be `None` when broken
        if not rel:
            return

        dash = self._stored.dashboards.pop(rel.id, {})

        if dash:
            dash["removed"] = True
            rel.data[self.charm.app]["dashboards"] = json.dumps(type_convert_stored(dash))

    def invalidate_dashboard(self, reason: str, rel_id=None) -> None:
        """Invalidate, but do not remove a dashboard until relations restore."""
        if not self.charm.unit.is_leader():
            return

        rel = self.framework.model.get_relation(self.relation_name, rel_id)

        if not rel:
            return

        dash = self._stored.dashboards[rel.id]
        dash["invalidated"] = True
        dash["invalidated_reason"] = reason

        rel.data[self.charm.app]["dashboards"] = json.dumps(type_convert_stored(dash))
        self.on.dashboard_status_changed.emit(error_message=reason, valid=False)

    @property
    def dashboards(self) -> List:
        """Return a list of known dashboard."""
        return [v for v in self._stored.dashboards.values()]


class GrafanaDashboardProvider(Object):
    """A provider object for working with Grafana Dashboards."""

    on = GrafanaDashboardEvents()
    _stored = StoredState()

    def __init__(self, charm: CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """A Grafana based Monitoring service consumer.

        Args:
            charm: a :class:`CharmBase` instance that manages this
                instance of the Grafana dashboard service.
            relation_name: a :string: name of the relation between `charm`
                the Grafana charmed service. The default is "grafana-dashboard".
                It is strongly advised not to change the default, so that people
                deploying your charm will have a consistent experience with all
                other charms that provide Grafana dashboards.
        """
        _validate_relation_by_interface_and_direction(
            charm, relation_name, RELATION_INTERFACE_NAME, RelationRole.requires
        )

        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.source_relation = "grafana-source"
        events = self.charm.on[relation_name]

        self._stored.set_default(
            dashboards=dict(),
            invalid_dashboards=dict(),
            active_sources=[],
        )

        self.framework.observe(
            events.relation_changed, self._on_grafana_dashboard_relation_changed
        )
        self.framework.observe(events.relation_broken, self._on_grafana_dashboard_relation_broken)

    def _on_grafana_dashboard_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle relation changes in related consumers.

        If there are changes in relations between Grafana dashboard providers
        and consumers, this event handler (if the unit is the leader) will
        get data for an incoming grafana-dashboard relation through a
        :class:`GrafanaDashboardsChanged` event, and make the relation data
        is available in the app's datastore object. The Grafana charm can
        then respond to the event to update its configuration
        """
        if not self.charm.unit.is_leader():
            return

        rel = self.framework.model.get_relation(self.relation_name, event.relation.id)

        data = (
            json.loads(rel.data[event.app].get("dashboards", {}))
            if rel.data[event.app].get("dashboards", {})
            else None
        )
        if not data:
            logger.warning("No dashboard data found in relation")
            return

        # Figure out our Prometheus relation and template the query

        try:
            prom_rel = self.charm.model.relations[self.source_relation][0]
            if len(prom_rel.units) == 0:
                logger.error("No %s related to %s!", self.source_relation, self.relation_name)
                return
        except IndexError:
            logger.error("No %s related to %s!", self.source_relation, self.relation_name)
            return

        prom_unit = next(iter(prom_rel.units))
        prom_identifier = "{}_{}_{}".format(
            self.charm.model.name,
            self.charm.model.uuid,
            prom_unit.app.name,
        )

        data["monitoring_identifier"] = prom_identifier

        # Get rid of this now that we passed through to the other side
        data.pop("uuid", None)

        # Pop it out of the list of dashboards if a relation is broken externally
        if data.get("removed", False):
            self._stored.dashboards.pop(rel.id)
            return

        if data.get("invalidated", False):
            self._stored.invalid_dashboards[rel.id] = data
            self._purge_dead_dashboard(rel.id)
            rel.data[self.charm.app]["event"] = json.dumps(
                {"errors": data.get("invalidated_reason"), "valid": False}
            )
            return

        if not self._check_active_data_sources(data, rel):
            return

        self._validate_dashboard_data(data, rel)

    def _validate_dashboard_data(self, data: Dict, rel: Relation) -> None:
        """Validate a given dashboard.

        Verify that the passed dashboard data is able to be found in our list
        of datasources and will render. If they do, let the charm know by
        emitting an event.

        Args:
            data: Dict; The serialised dashboard.
            rel: Relation; The relation the dashboard is associated with.
        """
        grafana_datasource = self._find_grafana_datasource(data, rel)
        if not grafana_datasource:
            return

        # Import at runtime so we don't get client dependencies
        from jinja2 import Template
        from jinja2.exceptions import TemplateSyntaxError

        # The dashboards are WAY too big since this ultimately calls out to Juju to
        # set the relation data, and it overflows the maximum argument length for
        # subprocess, so we have to use b64, annoyingly.
        # Worse, Python3 expects absolutely everything to be a byte, and a plain
        # `base64.b64encode()` is still too large, so we have to go through hoops
        # of encoding to byte, compressing with zlib, converting to base64 so it
        # can be converted to JSON, then all the way back

        templates = {}
        try:
            for fname in data["templates"]:
                tm = Template(
                    zlib.decompress(base64.b64decode(data["templates"][fname].encode())).decode()
                )
                tmpl = tm.render(
                    grafana_datasource=grafana_datasource,
                    prometheus_target=data["monitoring_target"],
                    prometheus_query=data["monitoring_query"],
                )
                templates[fname] = base64.b64encode(zlib.compress(tmpl.encode(), 9)).decode()
        except TemplateSyntaxError:
            self._purge_dead_dashboard(rel.id)
            errmsg = "Cannot add Grafana dashboard. Template is not valid Jinja"
            logger.warning(errmsg)
            rel.data[self.charm.app]["event"] = json.dumps({"errors": errmsg, "valid": False})
            return

        msg = {
            "target": data["monitoring_identifier"],
            "dashboards": templates,
            "data": data,
        }

        # Remove it from the list of invalid dashboards if it's there, and
        # send data back to the providing charm so it knows this dashboard is
        # valid now
        if self._stored.invalid_dashboards.pop(rel.id, None):
            rel.data[self.charm.app]["event"] = json.dumps({"errors": "", "valid": True})

        stored_data = self._stored.dashboards.get(rel.id, {}).get("data", {})
        coerced_data = type_convert_stored(stored_data) if stored_data else {}

        if not coerced_data == msg["data"]:
            self._stored.dashboards[rel.id] = msg
            self.on.dashboards_changed.emit()

    def _find_grafana_datasource(self, data: Dict, rel: Relation) -> Union[str, None]:
        """Find datasources on a given relation for a provider.

        Loop through the provider data and try to find a matching datasource. Return it
        if possible, otherwise add it to the list of invalid dashboards.

        May return either a :str: if a datasource is found, or :None: if it cannot be
        resolved
        """
        try:
            grafana_datasource = "{}".format(
                [
                    x["source-name"]
                    for x in self._stored.active_sources
                    if data["monitoring_identifier"] in x["source-name"]
                ][0]
            )
        except IndexError:
            self._check_active_data_sources(data, rel)
            return None
        return grafana_datasource

    def _check_active_data_sources(self, data: Dict, rel: Relation) -> bool:
        """Check for active Grafana dashboards.

        A trivial check to see whether there are any active datasources or not, used
        by both new dashboard additions and trying to restore invalid ones.

        Returns: a boolean indicating if there are any active dashboards.
        """
        if not self._stored.active_sources:
            msg = "Cannot add Grafana dashboard. No configured datasources"
            self._stored.invalid_dashboards[rel.id] = data
            self._purge_dead_dashboard(rel.id)
            logger.warning(msg)
            rel.data[self.charm.app]["event"] = json.dumps({"errors": msg, "valid": False})

            return False
        return True

    def renew_dashboards(self, sources: List) -> None:
        """Re-establish dashboards following a change to the relation.

        If something changes between this library and a datasource, try to re-establish
        invalid dashboards and invalidate active ones.

        Args:
            sources: List; A list of datasources.
        """
        # Cannot nest StoredDict inside StoredList
        self._stored.active_sources = [dict(s) for s in sources]

        # Make copies so we don't mutate these during iteration
        invalid_dashboards = copy.deepcopy(type_convert_stored(self._stored.invalid_dashboards))
        active_dashboards = copy.deepcopy(type_convert_stored(self._stored.dashboards))

        for rel_id, data in invalid_dashboards.items():
            rel = self.framework.model.get_relation(self.relation_name, rel_id)
            self._validate_dashboard_data(dict(data), rel)

        # Check the active dashboards also in case a source was removed
        for rel_id, stored in active_dashboards.items():
            rel = self.framework.model.get_relation(self.relation_name, rel_id)
            self._validate_dashboard_data(dict(stored["data"]), rel)

    def _on_grafana_dashboard_relation_broken(self, event: RelationBrokenEvent) -> None:
        """Update job config when consumers depart.

        When a Grafana dashboard consumer departs, the configuration
        for that consumer is removed from the list of dashboards
        """
        if not self.charm.unit.is_leader():
            return

        rel_id = event.relation.id
        try:
            self._stored.dashboards.pop(rel_id, None)
            self.on.dashboards_changed.emit()
        except KeyError:
            logger.warning("Could not remove dashboard for relation: {}".format(rel_id))

    def _purge_dead_dashboard(self, rel_id: int) -> None:
        """If an errored dashboard is in stored data, remove it and trigger a deletion."""
        if self._stored.dashboards.pop(rel_id, None):
            self.on.dashboards_changed.emit()

    @property
    def dashboards(self) -> List:
        """Get a list of known dashboards.

        Returns: a list of known dashboards.
        """
        dashboards = []
        for dash in self._stored.dashboards.values():
            dashboards.append(dash)
        return dashboards
