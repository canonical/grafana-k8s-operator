# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""A library for integrating Grafana dashboards in charmed operators."""

import base64
import json
import logging
import lzma
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ops.charm import (
    CharmBase,
    HookEvent,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationCreatedEvent,
    RelationMeta,
    RelationRole,
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
LIBPATCH = 7

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


class InvalidDirectoryPathError(Exception):
    """Raised if the grafana dashboards folder cannot be found or is otherwise invalid."""

    def __init__(
        self,
        grafana_dashboards_absolute_path: str,
        message: str,
    ):
        self.grafana_dashboards_absolute_path = grafana_dashboards_absolute_path
        self.message = message

        super().__init__(self.message)


def _resolve_dir_against_charm_path(charm: CharmBase, *path_elements: str) -> str:
    """Resolve the provided path items against the directory of the main file.

    Look up the directory of the charmed operator file being executed. This is normally
    going to be the charm.py file of the charm including this library. Then, resolve
    the provided path elements and return its absolute path.

    Raises:
        InvalidDirectoryPathError if the resolved path does not exist or it is not a directory

    """
    charm_dir = Path(charm.charm_dir)
    if not charm_dir.exists() or not charm_dir.is_dir():
        # Operator Framework does not currently expose a robust
        # way to determine the top level charm source directory
        # that is consistent across deployed charms and unit tests
        # Hence for unit tests the current working directory is used
        # TODO: updated this logic when the following ticket is resolved
        # https://github.com/canonical/operator/issues/643
        charm_dir = Path(os.getcwd())

    dir_path = charm_dir.absolute().joinpath(*path_elements)

    if not dir_path.exists():
        raise InvalidDirectoryPathError(str(dir_path), "directory does not exist")
    if not dir_path.is_dir():
        raise InvalidDirectoryPathError(str(dir_path), "is not a directory")

    return str(dir_path)


def _validate_relation_by_interface_and_direction(
    charm: CharmBase,
    relation_name: str,
    expected_relation_interface: str,
    expected_relation_role: RelationRole,
) -> None:
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

    Raises:
        RelationNotFoundError: If there is no relation in the charm's metadata.yaml
            named like the value of the `relation_name` argument.
        RelationInterfaceMismatchError: If the relation interface of the
            relation named as the provided `relation_name` argument does not
            match the `expected_relation_interface` argument.
        RelationRoleMismatchError: If the relation named as the provided `relation_name`
            argument has a different role than what is specified by the
            `expected_relation_role` argument.
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


def _encode_dashboard_content(content: Union[str, bytes]) -> str:
    if isinstance(content, str):
        content = bytes(content, "utf-8")

    return base64.b64encode(lzma.compress(content)).decode("utf-8")


def _decode_dashboard_content(encoded_content: str) -> str:
    return lzma.decompress(base64.b64decode(encoded_content.encode("utf-8"))).decode()


def _type_convert_stored(obj):
    """Convert Stored* to their appropriate types, recursively."""
    if isinstance(obj, StoredList):
        return list(map(_type_convert_stored, obj))
    elif isinstance(obj, StoredDict):
        rdict = {}  # type: Dict[Any, Any]
        for k in obj.keys():
            rdict[k] = _type_convert_stored(obj[k])
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

    Enables us to set a clear status on the provider.
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


class GrafanaProviderEvents(ObjectEvents):
    """Events raised by :class:`GrafanaSourceEvents`."""

    dashboard_status_changed = EventSource(GrafanaDashboardEvent)


class GrafanaDashboardProvider(Object):
    """An API to provide Grafana dashboards to a Grafana charm."""

    _stored = StoredState()
    on = GrafanaProviderEvents()

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = DEFAULT_RELATION_NAME,
        dashboards_path: str = "src/grafana_dashboards",
    ) -> None:
        """API to provide Grafana dashboard to a Grafana charmed operator.

        The :class:`GrafanaDashboardProvider` object provides an API
        to upload dashboards to a Grafana charm. In its most streamlined
        usage, the :class:`GrafanaDashboardProvider` is integrated in a
        charmed operator as follows:

            self.grafana = GrafanaDashboardProvider(self)

        The :class:`GrafanaDashboardProvider` will look for dashboard
        templates in the `<charm-py-directory>/grafana_dashboards` folder.
        Additionally, dashboard templates can be uploaded programmatically
        via the :method:`GrafanaDashboardProvider.add_dashboard` method.

        To use the :class:`GrafanaDashboardProvider` API, you need a relation
        defined in your charm operator's metadata.yaml as follows:

            provides:
                grafana-dashboard:
                    interface: grafana_dashboard

        If you would like to use relation name other than `grafana-dashboard`,
        you will need to specify the relation name via the `relation_name`
        argument when instantiating the :class:`GrafanaDashboardProvider` object.
        However, it is strongly advised to keep the the default relation name,
        so that people deploying your charm will have a consistent experience
        with all other charms that provide Grafana dashboards.

        It is possible to provide a different file path for the Grafana dashboards
        to be automatically managed by the :class:`GrafanaDashboardProvider` object
        via the `dashboards_path` argument. This may be necessary when the directory
        structure of your charmed operator repository is not the "usual" one as
        generated by `charmcraft init`, for example when adding the charmed operator
        in a Java repository managed by Maven or Gradle. However, unless there are
        such constraints with other tooling, it is strongly advised to store the
        Grafana dashboards in the default `<charm-py-directory>/grafana_dashboards`
        folder, in order to provide a consistent experience for other charmed operator
        authors.

        Args:
            charm: a :class:`CharmBase` object which manages this
                :class:`GrafanaProvider` object. Generally this is
                `self` in the instantiating class.
            relation_name: a :string: name of the relation managed by this
                :class:`GrafanaDashboardProvider`; it defaults to "grafana-dashboard".
            dashboards_path: a filesystem path relative to the charm root
                where dashboard templates can be located. By default, the library
                expects dashboard files to be in the `<charm-py-directory>/grafana_dashboards`
                directory.
        """
        _validate_relation_by_interface_and_direction(
            charm, relation_name, RELATION_INTERFACE_NAME, RelationRole.provides
        )

        try:
            dashboards_path = _resolve_dir_against_charm_path(charm, dashboards_path)
        except InvalidDirectoryPathError as e:
            logger.warning(
                "Invalid Grafana dashboards folder at %s: %s",
                e.grafana_dashboards_absolute_path,
                e.message,
            )

        super().__init__(charm, relation_name)

        self._charm = charm
        self._relation_name = relation_name
        self._dashboards_path = dashboards_path
        self._stored.set_default(dashboard_templates={})

        self.framework.observe(self._charm.on.leader_elected, self._update_all_dashboards_from_dir)
        self.framework.observe(self._charm.on.upgrade_charm, self._update_all_dashboards_from_dir)

        self.framework.observe(
            self._charm.on[self._relation_name].relation_created,
            self._on_grafana_dashboard_relation_created,
        )
        self.framework.observe(
            self._charm.on[self._relation_name].relation_changed,
            self._on_grafana_dashboard_relation_changed,
        )

    def add_dashboard(self, content: str) -> None:
        """Add a dashboard to the relation managed by this :class:`GrafanaDashboardProvider`.

        Args:
            content: a string representing a Jinja template. Currently, no
                global variables are added to the Jinja template evaluation
                context.
        """
        # Update of storage must be done irrespective of leadership, so
        # that the stored state is there when this unit becomes leader.
        stored_dashboard_templates = self._stored.dashboard_templates

        encoded_dashboard = _encode_dashboard_content(content)

        # Use as id the first chars of the encoded dashboard, so that its
        # it is predictable across units.
        id = f"prog:{encoded_dashboard[0:7]}"
        stored_dashboard_templates[id] = self._content_to_dashboard_object(encoded_dashboard)

        if self._charm.unit.is_leader():
            for dashboard_relation in self._charm.model.relations[self._relation_name]:
                self._upset_dashboards_on_relation(dashboard_relation)

    def remove_non_builtin_dashboards(self) -> None:
        """Remove all dashboards to the relation added via :method:`add_dashboard`."""
        # Update of storage must be done irrespective of leadership, so
        # that the stored state is there when this unit becomes leader.
        stored_dashboard_templates = self._stored.dashboard_templates

        for dashboard_id in list(stored_dashboard_templates.keys()):
            if dashboard_id.startswith("prog:"):
                del stored_dashboard_templates[dashboard_id]

        if self._charm.unit.is_leader():
            for dashboard_relation in self._charm.model.relations[self._relation_name]:
                self._upset_dashboards_on_relation(dashboard_relation)

    def update_dashboards(self) -> None:
        """Trigger the re-evaluation of the data on all relations."""
        if self._charm.unit.is_leader():
            for dashboard_relation in self._charm.model.relations[self._relation_name]:
                self._upset_dashboards_on_relation(dashboard_relation)

    def _update_all_dashboards_from_dir(self, _: HookEvent) -> None:
        """Scans the built-in dashboards and updates relations with changes."""
        # Update of storage must be done irrespective of leadership, so
        # that the stored state is there when this unit becomes leader.

        # Ensure we do not leave outdated dashboards by removing from stored all
        # the encoded dashboards that start with "file/".
        if self._dashboards_path:
            stored_dashboard_templates = self._stored.dashboard_templates

            for dashboard_id in list(stored_dashboard_templates.keys()):
                if dashboard_id.startswith("file:"):
                    del stored_dashboard_templates[dashboard_id]

            for path in filter(Path.is_file, Path(self._dashboards_path).glob("*.tmpl")):
                id = f"file:{path.stem}"
                stored_dashboard_templates[id] = self._content_to_dashboard_object(
                    _encode_dashboard_content(path.read_bytes())
                )

            if self._charm.unit.is_leader():
                for dashboard_relation in self._charm.model.relations[self._relation_name]:
                    self._upset_dashboards_on_relation(dashboard_relation)

    def _on_grafana_dashboard_relation_created(self, event: RelationCreatedEvent) -> None:
        """Watch for a relation being created and automatically send dashboards.

        Args:
            event: The :class:`RelationJoinedEvent` sent when a
                `grafana_dashboaard` relationship is joined
        """
        if self._charm.unit.is_leader():
            self._upset_dashboards_on_relation(event.relation)

    def _on_grafana_dashboard_relation_changed(self, event: RelationChangedEvent) -> None:
        """Watch for changes so we know if there's an error to signal back to the parent charm.

        Args:
            event: The `RelationChangedEvent` that triggered this handler.
        """
        if self._charm.unit.is_leader():
            data = json.loads(event.relation.data[event.app].get("event", "{}"))

            if not data:
                return

            valid = bool(data.get("valid", True))
            errors = data.get("errors", [])
            if valid and not errors:
                self.on.dashboard_status_changed.emit(valid=valid)
            else:
                self.on.dashboard_status_changed.emit(valid=valid, errors=errors)

    def _upset_dashboards_on_relation(self, relation: Relation) -> None:
        """Update the dashboards in the relation data bucket."""
        # It's completely ridiculous to add a UUID, but if we don't have some
        # pseudo-random value, this never makes it across 'juju set-state'
        stored_data = {
            "templates": _type_convert_stored(self._stored.dashboard_templates),
            "uuid": str(uuid.uuid4()),
        }

        relation.data[self._charm.app]["dashboards"] = json.dumps(stored_data)

    def _content_to_dashboard_object(self, content: str) -> Dict:
        return {
            "charm": self._charm.meta.name,
            "content": content,
            "juju_topology": self._juju_topology,
        }

    @property
    def _juju_topology(self) -> Dict:
        return {
            "model": self._charm.model.name,
            "model_uuid": self._charm.model.uuid,
            "application": self._charm.app.name,
            "unit": self._charm.unit.name,
        }

    @property
    def dashboard_templates(self) -> List:
        """Return a list of the known dashboard templates."""
        return [v for v in self._stored.dashboard_templates.values()]


class GrafanaDashboardConsumer(Object):
    """A consumer object for working with Grafana Dashboards."""

    on = GrafanaDashboardEvents()
    _stored = StoredState()

    def __init__(self, charm: CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """API to receive Grafana dashboards from charmed operators.

        The :class:`GrafanaDashboardConsumer` object provides an API
        to consume dashboards provided by a charmed operator using the
        :class:`GrafanaDashboardProvider` library. The
        :class:`GrafanaDashboardConsumer` is integrated in a
        charmed operator as follows:

            self.grafana = GrafanaDashboardConsumer(self)

        To use this library, you need a relation defined as follows in
        your charm operator's metadata.yaml:

            requires:
                grafana-dashboard:
                    interface: grafana_dashboard

        If you would like to use a different relation name than
        `grafana-dashboard`, you need to specify the relation name via the
        `relation_name` argument. However, it is strongly advised not to
        change the default, so that people deploying your charm will have
        a consistent experience with all other charms that consume Grafana
        dashboards.

        Args:
            charm: a :class:`CharmBase` object which manages this
                :class:`GrafanaProvider` object. Generally this is
                `self` in the instantiating class.
            relation_name: a :string: name of the relation managed by this
                :class:`GrafanaDashboardConsumer`; it defaults to "grafana-dashboard".
        """
        _validate_relation_by_interface_and_direction(
            charm, relation_name, RELATION_INTERFACE_NAME, RelationRole.requires
        )

        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

        self._stored.set_default(dashboards=dict())

        self.framework.observe(
            self._charm.on[self._relation_name].relation_changed,
            self._on_grafana_dashboard_relation_changed,
        )
        self.framework.observe(
            self._charm.on[self._relation_name].relation_broken,
            self._on_grafana_dashboard_relation_broken,
        )

    def get_dashboards_from_relation(self, relation_id: int) -> List:
        """Get a list of known dashboards for one instance of the monitored relation.

        Args:
            relation_id: the identifier of the relation instance, as returned by
                :method:`ops.model.Relation.id`.

        Returns: a list of known dashboards coming from the provided relation instance.
        """
        return [
            self._to_external_object(relation_id, dashboard)
            for dashboard in self._stored.dashboards.get(relation_id, [])
        ]

    def _on_grafana_dashboard_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle relation changes in related providers.

        If there are changes in relations between Grafana dashboard consumers
        and providers, this event handler (if the unit is the leader) will
        get data for an incoming grafana-dashboard relation through a
        :class:`GrafanaDashboardsChanged` event, and make the relation data
        available in the app's datastore object. The Grafana charm can
        then respond to the event to update its configuration.
        """
        # TODO Are we sure this is right? It sounds like every Grafana unit
        # should create files with the dashboards in its container.
        if not self._charm.unit.is_leader():
            return

        self._render_dashboards_and_emit_event(event.relation)

    def update_dashboards(self, relation: Optional[Relation] = None) -> None:
        """Re-establish dashboards on one or more relations.

        If something changes between this library and a datasource, try to re-establish
        invalid dashboards and invalidate active ones.

        Args:
            relation: a specific relation for which the dashboards have to be
                updated. If not specified, all relations managed by this
                :class:`GrafanaDashboardConsumer` will be updated.
        """
        if not self._charm.unit.is_leader():
            return

        relations = [relation] if relation else self._charm.model.relations[self._relation_name]

        for relation in relations:
            self._render_dashboards_and_emit_event(relation)

    def _on_grafana_dashboard_relation_broken(self, event: RelationBrokenEvent) -> None:
        """Update job config when providers depart.

        When a Grafana dashboard provider departs, the configuration
        for that provider is removed from the list of dashboards
        """
        if not self._charm.unit.is_leader():
            return

        self._remove_all_dashboards_for_relation(event.relation)

    def _render_dashboards_and_emit_event(self, relation: Relation) -> None:
        """Validate a given dashboard.

        Verify that the passed dashboard data is able to be found in our list
        of datasources and will render. If they do, let the charm know by
        emitting an event.

        Args:
            relation: Relation; The relation the dashboard is associated with.
        """
        other_app = relation.app

        if not (raw_data := relation.data[other_app].get("dashboards", {})):
            logger.warning(
                "No dashboard data found in the %s:%s relation",
                self._relation_name,
                str(relation.id),
            )
            return

        data = json.loads(raw_data)

        # The only piece of data needed on this side of the relations is "templates"
        templates = data.pop("templates")

        # Import only if a charmed operator uses the consumer, we don't impose these
        # dependencies on the client
        from jinja2 import Template
        from jinja2.exceptions import TemplateSyntaxError

        # The dashboards are WAY too big since this ultimately calls out to Juju to
        # set the relation data, and it overflows the maximum argument length for
        # subprocess, so we have to use b64, annoyingly.
        # Worse, Python3 expects absolutely everything to be a byte, and a plain
        # `base64.b64encode()` is still too large, so we have to go through hoops
        # of encoding to byte, compressing with lzma, converting to base64 so it
        # can be converted to JSON, then all the way back.

        rendered_dashboards = []
        relation_has_invalid_dashboards = False

        for _, (fname, template) in enumerate(templates.items()):
            decoded_content = _decode_dashboard_content(template["content"])

            content = None
            error = None
            try:
                content = _encode_dashboard_content(Template(decoded_content).render())
            except TemplateSyntaxError as e:
                error = str(e)
                relation_has_invalid_dashboards = True

            # Prepend the relation name and ID to the dashboard ID to avoid clashes with
            # multiple relations with apps from the same charm, or having dashboards with
            # the same ids inside their charm operators
            rendered_dashboards.append(
                {
                    "id": f"{relation.name}:{relation.id}/{fname}",
                    "original_id": fname,
                    "content": content if content else None,
                    "template": template,
                    "valid": (error is None),
                    "error": error,
                }
            )

        if relation_has_invalid_dashboards:
            self._remove_all_dashboards_for_relation(relation)

            invalid_templates = [
                data["original_id"] for data in rendered_dashboards if not data["valid"]
            ]

            logger.warning(
                "Cannot add one or more Grafana dashboards from relation '{}:{}': the following "
                "templates are invalid: {}".format(
                    relation.name,
                    relation.id,
                    invalid_templates,
                )
            )

            relation.data[self._charm.app]["event"] = json.dumps(
                {
                    "errors": [
                        {
                            "dashboard_id": rendered_dashboard["original_id"],
                            "error": rendered_dashboard["error"],
                        }
                        for rendered_dashboard in rendered_dashboards
                        if rendered_dashboard["error"]
                    ]
                }
            )

            # Dropping dashboards for a relation needs to be signalled
            self.on.dashboards_changed.emit()
        else:
            stored_data = rendered_dashboards
            currently_stored_data = self._stored.dashboards.get(relation.id, {})

            coerced_data = (
                _type_convert_stored(currently_stored_data) if currently_stored_data else {}
            )

            if not coerced_data == stored_data:
                self._stored.dashboards[relation.id] = stored_data
                self.on.dashboards_changed.emit()

    def _remove_all_dashboards_for_relation(self, relation: Relation) -> None:
        """If an errored dashboard is in stored data, remove it and trigger a deletion."""
        if self._stored.dashboards.pop(relation.id, None):
            self.on.dashboards_changed.emit()

    def _to_external_object(self, relation_id, dashboard):
        print(dashboard)
        return {
            "id": dashboard["original_id"],
            "relation_id": relation_id,
            "charm": dashboard["template"]["charm"],
            "content": _decode_dashboard_content(dashboard["content"]),
        }

    @property
    def dashboards(self) -> List[Dict]:
        """Get a list of known dashboards across all instances of the monitored relation.

        Returns: a list of known dashboards. The JSON of each of the dashboards is available
            in the `content` field of the corresponding `dict`.
        """
        dashboards = []

        for _, (relation_id, dashboards_for_relation) in enumerate(
            self._stored.dashboards.items()
        ):
            for dashboard in dashboards_for_relation:
                dashboards.append(self._to_external_object(relation_id, dashboard))

        return dashboards
