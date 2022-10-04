#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright 2021 Canonical Ltd.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""A Kubernetes charm for Grafana."""

import configparser
import hashlib
import json
import logging
import os
import re
import secrets
import socket
import string
import time
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict
from urllib.parse import ParseResult, urlparse

import yaml
from charms.catalogue_k8s.v0.catalogue import CatalogueConsumer, CatalogueItem
from charms.grafana_auth.v0.grafana_auth import AuthRequirer, AuthRequirerCharmEvents
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardConsumer
from charms.grafana_k8s.v0.grafana_source import (
    GrafanaSourceConsumer,
    GrafanaSourceEvents,
    SourceFieldsMissingError,
)
from charms.observability_libs.v0.kubernetes_compute_resources_patch import (
    K8sResourcePatchFailedEvent,
    KubernetesComputeResourcesPatch,
    ResourceRequirements,
    adjust_resource_requirements,
)
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider
from charms.traefik_route_k8s.v0.traefik_route import TraefikRouteRequirer
from ops.charm import (
    ActionEvent,
    CharmBase,
    ConfigChangedEvent,
    HookEvent,
    RelationBrokenEvent,
    RelationChangedEvent,
    RelationJoinedEvent,
    UpgradeCharmEvent,
)
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus
from ops.pebble import (
    APIError,
    ConnectionError,
    ExecError,
    Layer,
    PathError,
    ProtocolError,
)

from grafana_server import Grafana
from kubernetes_service import K8sServicePatch, PatchFailed

logger = logging.getLogger()

REQUIRED_DATABASE_FIELDS = {
    "type",  # mysql, postgres or sqlite3 (sqlite3 doesn't work for HA)
    "host",  # in the form '<url_or_ip>:<port>', e.g. 127.0.0.1:3306
    "name",
    "user",
    "password",
}

VALID_DATABASE_TYPES = {"mysql", "postgres", "sqlite3"}
VALID_AUTHENTICATION_MODES = {"proxy"}

CONFIG_PATH = "/etc/grafana/grafana-config.ini"
PROVISIONING_PATH = "/etc/grafana/provisioning"
DATASOURCES_PATH = "/etc/grafana/provisioning/datasources/datasources.yaml"
DATABASE = "database"
PEER = "grafana"
PORT = 3000


class GrafanaCharm(CharmBase):
    """Charm to run Grafana on Kubernetes.

    This charm allows for high-availability
    (as long as a non-sqlite database relation is present).

    Developers of this charm should be aware of the Grafana provisioning docs:
    https://grafana.com/docs/grafana/latest/administration/provisioning/
    """

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        # -- initialize states --
        self.name = "grafana"
        self.containers = {
            "workload": self.unit.get_container(self.name),
            "replication": self.unit.get_container("litestream"),
        }
        self.grafana_service = Grafana("localhost", PORT)
        self._grafana_config_ini_hash = None
        self._grafana_datasources_hash = None
        self._stored.set_default(k8s_service_patched=False, admin_password="")

        self.metrics_endpoint = MetricsEndpointProvider(
            charm=self,
            jobs=[{"static_configs": [{"targets": ["*:3000"]}]}],
            refresh_event=self.on.grafana_pebble_ready,
        )

        # -- standard events
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.grafana_pebble_ready, self._on_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on.get_admin_password_action, self._on_get_admin_password)

        # -- grafana_source relation observations
        self.source_consumer = GrafanaSourceConsumer(self, "grafana-source")
        self.framework.observe(
            self.source_consumer.on.sources_changed,
            self._on_grafana_source_changed,
        )
        self.framework.observe(
            self.source_consumer.on.sources_to_delete_changed,
            self._on_grafana_source_changed,
        )

        # -- self-monitoring
        self.framework.observe(
            self.source_consumer.on.sources_changed,
            self._maybe_provision_own_dashboard,
        )
        self.framework.observe(
            self.on["metrics-endpoint"].relation_joined,
            self._maybe_provision_own_dashboard,
        )
        self.framework.observe(
            self.on["metrics-endpoint"].relation_broken,
            self._maybe_provision_own_dashboard,
        )

        # -- grafana_dashboard relation observations
        self.dashboard_consumer = GrafanaDashboardConsumer(self, "grafana-dashboard")
        self.framework.observe(
            self.dashboard_consumer.on.dashboards_changed, self._on_dashboards_changed
        )

        # -- Peer relation observations
        self.framework.observe(self.on[PEER].relation_changed, self._on_peer_data_changed)

        # -- database relation observations
        self.framework.observe(self.on[DATABASE].relation_changed, self._on_database_changed)
        self.framework.observe(self.on[DATABASE].relation_broken, self._on_database_broken)

        # -- k8s resource patch
        self.resource_patch = KubernetesComputeResourcesPatch(
            self, self.name, resource_reqs_func=self._resource_reqs_from_config
        )
        self.framework.observe(self.resource_patch.on.patch_failed, self._on_resource_patch_failed)
        # -- grafana_auth relation observations
        self.grafana_auth_requirer = AuthRequirer(
            self,
            relation_name="grafana-auth",
            urls=[f"{self.app.name}:{PORT}"],
            refresh_event=self.on.grafana_pebble_ready,
        )
        self.framework.observe(
            self.grafana_auth_requirer.on.auth_conf_available, self._on_grafana_auth_conf_available
        )

        # -- ingress via raw traefik_route
        # TraefikRouteRequirer expects an existing relation to be passed as part of the constructor,
        # so this may be none. Rely on `self.ingress.is_ready` later to check
        self.ingress = TraefikRouteRequirer(self, self.model.get_relation("ingress"), "ingress")  # type: ignore
        self.framework.observe(self.on["ingress"].relation_joined, self._configure_ingress)
        self.framework.observe(self.on.leader_elected, self._configure_ingress)
        self.framework.observe(self.on.config_changed, self._configure_ingress)

        self.catalog = CatalogueConsumer(
            charm=self,
            refresh_event=[
                self.on.grafana_pebble_ready,
                self.on["ingress"].relation_joined,
            ],
            item=CatalogueItem(
                name="Grafana",
                icon="bar-chart",
                url=self.external_url,
                description=(
                    "Grafana allows you to query, visualize, alert on, and "
                    "visualize metrics from mixed datasources in configurable "
                    "dashboards for observability."
                ),
            ),
        )

    def _on_install(self, _):
        """Handler for the install event during which we will update the K8s service."""
        self._patch_k8s_service()

    def _on_config_changed(self, event: ConfigChangedEvent) -> None:
        """Event handler for the config-changed event.

        If the configuration is changed, update the variables we know about and
        restart the services. We don't know specifically whether it's a new install,
        a relation change, a leader election, or other, so call `_configure` to check
        the config files

        Args:
            event: a :class:`ConfigChangedEvent` to signal that something happened
        """
        self._configure()
        self._configure_replication()

    def _configure_ingress(self, event: HookEvent) -> None:
        """Set up ingress if a relation is joined, config changed, or a new leader election.

        Since ingress-per-unit and ingress-per-app are not appropriate, as only the Grafana
        leader must be exposed over ingress in order for interactions with sqlite replication
        to work as expected to propagate changes across to follower units, ensuring that things
        are configured correctly on election is crucial.

        Also since :class:`TraefikRouteRequirer` may not have been constructed with an existing
        relation if a :class:`RelationJoinedEvent` comes through during the charm lifecycle, if we
        get one here, we should recreate it, but OF will give us grief about "two objects claiming
        to be ...", so manipulate its private `_relation` variable instead.

        Args:
            event: a :class:`HookEvent` to signal a change we may need to respond to.
        """
        if not self.unit.is_leader():
            return

        # If it's a RelationJoinedEvent, set it in the ingress object
        if isinstance(event, RelationJoinedEvent):
            self.ingress._relation = event.relation

        # No matter what, check readiness -- this blindly checks whether `ingress._relation` is not
        # None, so it overlaps a little with the above, but works as expected on leader elections
        # and config-change
        if self.ingress.is_ready():
            self._configure()
            self.ingress.submit_to_traefik(self._ingress_config)

    def _configure_replication(self) -> None:
        """Checks to ensure that the leader is streaming DB changes, and others are listening.

        If a leader election event through `config-changed` would result in a new primary, start
        it. If the address provided by the leader in peer data changes, `leader` will be false,
        and replicas will be started.

        Args:
            leader: a boolean indicating the leader status
        """
        if not self.containers["replication"].can_connect():
            return

        restart = False
        leader = self.unit.is_leader()

        if (
            self.containers["replication"].get_plan().services
            != self._build_replication(leader).services
        ):
            restart = True

        litestream_config = {"addr": ":9876", "dbs": [{"path": "/var/lib/grafana/grafana.db"}]}

        if not leader:
            litestream_config["dbs"][0].update({"upstream": {"url": "http://${LITESTREAM_UPSTREAM_URL}"}})  # type: ignore

        container = self.containers["replication"]
        if container.can_connect():
            container.push("/etc/litestream.yml", yaml.dump(litestream_config), make_dirs=True)

        if restart:
            self.restart_litestream(leader)

    def _on_grafana_source_changed(self, _: GrafanaSourceEvents) -> None:
        """When a grafana-source is added or modified, update the config.

        Args:
            event: a :class:`GrafanaSourceEvents` instance sent from the provider
        """
        self._configure()

    def _maybe_provision_own_dashboard(self, event: HookEvent) -> None:
        """If all the prerequisites are enabled, provision a self-monitoring dashboard.

        Requires:
            A Prometheus relation on self.prometheus_scrape
            The SAME Prometheus relation again on grafana_source

        If those are true, we have a Prometheus scraping this Grafana, and we should
        provision our dashboard.
        """
        container = self.unit.get_container(self.name)
        if not container.can_connect():
            logger.warning("Cannot connect to Pebble yet, not provisioning own dashboard")
            return

        source_related_apps = [rel.app for rel in self.model.relations["grafana-source"]]
        scrape_related_apps = [rel.app for rel in self.model.relations["metrics-endpoint"]]

        has_relation = any(
            [source for source in source_related_apps if source in scrape_related_apps]
        )

        dashboards_dir_path = os.path.join(PROVISIONING_PATH, "dashboards")
        self.init_dashboard_provisioning(dashboards_dir_path)

        dashboard_path = os.path.join(dashboards_dir_path, "grafana_metrics.json")
        if has_relation and self.unit.is_leader():
            # This is not going through the library due to the massive refactor needed in order
            # to squash all of the `validate_relation_direction` and structure around smashing
            # the datastructures for a self-monitoring use case. This is built-in in Grafana 9,
            # so it will FIXME be removed when we upgrade
            container.push(
                dashboard_path, Path("src/self_dashboard.json").read_bytes(), make_dirs=True
            )
        elif not has_relation or isinstance(event, RelationBrokenEvent):
            if container.list_files(dashboards_dir_path, pattern="grafana_metrics.json"):
                container.remove_path(dashboard_path)
                logger.debug("Removed dashboard %s", dashboard_path)
                self.restart_grafana()

    def _on_upgrade_charm(self, event: UpgradeCharmEvent) -> None:
        """Re-provision Grafana and its datasources on upgrade.

        Args:
            event: a :class:`UpgradeCharmEvent` to signal the upgrade
        """
        self.source_consumer.upgrade_keys()
        self.dashboard_consumer.update_dashboards()
        self._configure()
        self._on_dashboards_changed(event)

    def _on_stop(self, _) -> None:
        """Go into maintenance state if the unit is stopped."""
        self.unit.status = MaintenanceStatus("Application is terminating.")

    def _configure(self) -> None:
        """Configure Grafana.

        Generate configuration files and check the sums against what is
        already stored in the charm. If either the base Grafana config
        or the datasource config differs, restart Grafana.
        """
        if not self.containers["workload"].can_connect():
            return
        logger.debug("Handling grafana-k8s configuration change")
        restart = False

        # Generate a new base config and see if it differs from what we have.
        # If it does, store it and signal that we should restart Grafana
        grafana_config_ini = self._generate_grafana_config()
        config_ini_hash = hashlib.sha256(str(grafana_config_ini).encode("utf-8")).hexdigest()
        if not self.grafana_config_ini_hash == config_ini_hash:
            self.grafana_config_ini_hash = config_ini_hash
            self._update_grafana_config_ini(grafana_config_ini)
            logger.info("Updated Grafana's base configuration")

            restart = True

        # Do the same thing for datasources
        grafana_datasources = self._generate_datasource_config()
        datasources_hash = hashlib.sha256(str(grafana_datasources).encode("utf-8")).hexdigest()
        if not self.grafana_datasources_hash == datasources_hash:
            self.grafana_datasources_hash = datasources_hash
            self._update_datasource_config(grafana_datasources)
            logger.info("Updated Grafana's datasource configuration")

            # Non-leaders will get updates from litestream
            if self.unit.is_leader():
                restart = True

        if self.containers["workload"].get_plan().services != self._build_layer().services:
            restart = True

        if not self.resource_patch.is_ready():
            if isinstance(self.unit.status, ActiveStatus) or self.unit.status.message == "":
                self.unit.status = MaintenanceStatus("Waiting for resource limit patch to apply")
            return

        if restart:
            self.restart_grafana()
        else:
            # All clear, move to active.
            # We can basically only get here if the charm is completely restarted, but all of
            # the configs are correct, with the correct pebble plan, such as a node reboot.
            #
            # A node reboot does not send any identifiable events (`start`, `pebble_ready`), so
            # this is more or less the 'fallthrough' part of a case statement
            if not isinstance(self.unit.status, ActiveStatus):
                self.unit.status = ActiveStatus()

    def _update_datasource_config(self, config: str) -> None:
        """Write an updated datasource configuration file to the Pebble container if necessary.

        Args:
            config: A :str: containing the datasource configuration
        """
        container = self.unit.get_container(self.name)

        try:
            container.push(DATASOURCES_PATH, config, make_dirs=True)
        except ConnectionError:
            logger.error(
                "Could not push datasource config. Pebble refused connection. Shutting down?"
            )

    def _update_grafana_config_ini(self, config: str) -> None:
        """Write an updated Grafana configuration file to the Pebble container if necessary.

        Args:
            config: A :str: containing the datasource configuration
        """
        try:
            self.containers["workload"].push(CONFIG_PATH, config, make_dirs=True)
        except ConnectionError:
            logger.error(
                "Could not push datasource config. Pebble refused connection. Shutting down?"
            )

    @property
    def has_peers(self) -> bool:
        """Check whether or not there are any other Grafanas as peers."""
        rel = self.model.get_relation(PEER)
        return len(rel.units) > 0 if rel is not None else False

    @property
    def peers(self):
        """Fetch the peer relation."""
        return self.model.get_relation(PEER)

    def set_peer_data(self, key: str, data: Any) -> None:
        """Put information into the peer data bucket instead of `StoredState`."""
        self.peers.data[self.app][key] = json.dumps(data)

    def get_peer_data(self, key: str) -> Any:
        """Retrieve information from the peer data bucket instead of `StoredState`."""
        data = self.peers.data[self.app].get(key, "")
        return json.loads(data) if data else {}

    ############################
    # DASHBOARD IMPORT
    ###########################
    def init_dashboard_provisioning(self, dashboard_path: str):
        """Initialise the provisioning of Grafana dashboards.

        Args:
            dashboard_path: str; A file path to the dashboard to provision
        """
        self._configure()
        logger.info("Initializing dashboard provisioning path")
        container = self.unit.get_container(self.name)

        dashboard_config = {
            "apiVersion": 1,
            "providers": [
                {
                    "name": "Default",
                    "updateIntervalSeconds": "5",
                    "type": "file",
                    "options": {"path": dashboard_path},
                }
            ],
        }

        default_config = os.path.join(dashboard_path, "default.yaml")
        default_config_string = yaml.dump(dashboard_config)

        if not os.path.exists(dashboard_path):
            try:
                container.push(default_config, default_config_string, make_dirs=True)
                self.restart_grafana()
            except ConnectionError:
                logger.warning(
                    "Could not push default dashboard configuration. Pebble shutting down?"
                )

    def _on_dashboards_changed(self, event) -> None:
        """Handle dashboard events."""
        container = self.unit.get_container(self.name)
        dashboards_dir_path = os.path.join(PROVISIONING_PATH, "dashboards")

        self.init_dashboard_provisioning(dashboards_dir_path)

        if not container.can_connect():
            logger.debug("Cannot connect to Pebble yet, deferring event")
            event.defer()
            return

        dashboards_file_to_be_kept = {}
        try:
            for dashboard_file in container.list_files(dashboards_dir_path, pattern="juju_*.json"):
                dashboards_file_to_be_kept[dashboard_file.path] = False

            for dashboard in self.dashboard_consumer.dashboards:
                dashboard_content = dashboard["content"]
                dashboard_content_bytes = dashboard_content.encode("utf-8")
                dashboard_content_digest = hashlib.sha256(dashboard_content_bytes).hexdigest()
                dashboard_filename = "juju_{}_{}.json".format(
                    dashboard["charm"], dashboard_content_digest[0:7]
                )

                path = os.path.join(dashboards_dir_path, dashboard_filename)
                dashboards_file_to_be_kept[path] = True

                logger.debug("New dashboard %s", path)
                container.push(path, dashboard_content_bytes, make_dirs=True)

            for dashboard_file_path, to_be_kept in dashboards_file_to_be_kept.items():
                if not to_be_kept:
                    container.remove_path(dashboard_file_path)
                    logger.debug("Removed dashboard %s", dashboard_file_path)

        except ConnectionError:
            logger.exception("Could not update dashboards. Pebble shutting down?")

    #####################################

    # K8S WRANGLING

    #####################################

    def _patch_k8s_service(self):
        """Fix the Kubernetes service that was setup by Juju with correct port numbers."""
        if self.unit.is_leader() and not self._stored.k8s_service_patched:
            service_ports = [
                (self.app.name, PORT, PORT),
            ]
            try:
                K8sServicePatch.set_ports(self.app.name, service_ports)
            except PatchFailed as e:
                logger.error("Unable to patch the Kubernetes service: %s", str(e))
            else:
                self._stored.k8s_service_patched = True
                logger.info("Successfully patched the Kubernetes service!")

    #####################################

    # DATABASE EVENTS

    #####################################

    @property
    def has_db(self) -> bool:
        """Only consider a DB connection if we have config info."""
        rel = self.model.get_relation(DATABASE)
        return len(rel.units) > 0 if rel is not None else False

    def _on_peer_data_changed(self, _: RelationChangedEvent) -> None:
        """Get the replica primary address from peer data so we can check whether to restart.

        Args:
            event: A :class:`RelationChangedEvent` from a `grafana` source
        """
        primary_addr = self.get_peer_data("replica_primary")

        # If we found a key for the address of a primary, ensure that replication reflects the
        # current state. It is necessary to watch for peer_data_changed events, since a
        # leader election may not run any in specific order. Checking here ensures that, once
        # a new leader is elected AND updates the bucket with its address, that secondaries
        # are notified of where they should look to replication stream now, and restart their
        # clients. It is, generally, a way to guarantee the ordering between:
        #   - new leader elected
        #   - leader restarts litestream in "primary" mode (no `upstream:` in the config)
        #   - leader sets `replica_primary` in the peer databag as part of _build_replication
        #   - other units get on_peer_data_changed
        #   - secondaries get the "correct" primary and restart
        if primary_addr:
            self._configure_replication()

    def _on_database_changed(self, event: RelationChangedEvent) -> None:
        """Sets configuration information for database connection.

        Args:
            event: A :class:`RelationChangedEvent` from a `database` source
        """
        if not self.unit.is_leader():
            return

        # Get required information
        database_fields = {
            field: event.relation.data[event.app].get(field) for field in REQUIRED_DATABASE_FIELDS  # type: ignore
        }

        # if any required fields are missing, warn the user and return
        missing_fields = [
            field for field in REQUIRED_DATABASE_FIELDS if database_fields.get(field) is None
        ]
        if len(missing_fields) > 0:
            raise SourceFieldsMissingError(
                "Missing required data fields for database relation: {}".format(missing_fields)
            )

        # add the new database relation data to the datastore
        db_info = {field: value for field, value in database_fields.items() if value}
        self.set_peer_data("database", db_info)

        self._configure()

    def _on_database_broken(self, event: RelationBrokenEvent) -> None:
        """Removes database connection info from datastore.

        We are guaranteed to only have one DB connection, so clearing
        datastore.database is all we need for the change to be propagated
        to the Pebble container.

        Args:
            event: a :class:`RelationBrokenEvent` from a `database` source
        """
        if not self.unit.is_leader():
            return

        # remove the existing database info from datastore
        self.set_peer_data("database", {})
        logger.info("Removing the grafana-k8s database backend config")

        # Cleanup the config file
        self._configure()

    def _generate_grafana_config(self) -> str:
        """Generate a database configuration for Grafana.

        For now, this only creates database information, since everything else
        can be set in ENV variables, but leave for expansion later so we can
        hide auth secrets
        """
        return self._generate_database_config() if self.has_db else ""

    def _generate_database_config(self) -> str:
        """Generate a database configuration.

        Returns:
            A string containing the required database information to be stubbed into the config
            file.
        """
        db_config = self.get_peer_data("database")
        if not db_config:
            return ""

        config_ini = configparser.ConfigParser()
        db_type = "mysql"

        db_url = "{0}://{1}:{2}@{3}/{4}".format(
            db_type,
            db_config.get("user"),
            db_config.get("password"),
            db_config.get("host"),
            db_config.get("name"),
        )
        config_ini["database"] = {
            "type": db_type,
            "host": db_config.get("host"),
            "name": db_config.get("name", ""),
            "user": db_config.get("user", ""),
            "password": db_config.get("password", ""),
            "url": db_url,
        }

        # This is silly, but a ConfigParser() handles this nicer than
        # raw string manipulation
        data = StringIO()
        config_ini.write(data)
        data.seek(0)
        ret = data.read()
        data.close()
        return ret

    #####################################

    # PEBBLE OPERATIONS

    #####################################

    def _on_pebble_ready(self, event) -> None:
        """When Pebble is ready, start everything up."""
        self._configure()
        self.source_consumer.upgrade_keys()
        self.dashboard_consumer.update_dashboards()
        version = self.grafana_version
        if version is not None:
            self.unit.set_workload_version(version)
        else:
            logger.debug(
                "Cannot set workload version at this time: could not get Alertmanager version."
            )

    def restart_grafana(self) -> None:
        """Restart the pebble container.

        `container.replan()` is intentionally avoided, since if no environment
        variables are changed, this will not actually restart Grafana, which is
        necessary to reload the provisioning files.

        Note that Grafana does not support SIGHUP, so a full restart is needed.
        """
        layer = self._build_layer()
        try:
            self.containers["workload"].add_layer(self.name, layer, combine=True)
            if self.containers["workload"].get_service(self.name).is_running():
                self.containers["workload"].stop(self.name)

            self.containers["workload"].start(self.name)
            logger.info("Restarted grafana-k8s")

            if self._poll_container(self.containers["workload"].can_connect):
                # We should also make sure sqlite is in WAL mode for replication
                self.containers["workload"].push(
                    "/usr/local/bin/sqlite3",
                    Path("sqlite-static").read_bytes(),
                    permissions=0o755,
                    make_dirs=True,
                )

                pragma = self.containers["workload"].exec(
                    [
                        "/usr/local/bin/sqlite3",
                        "/var/lib/grafana/grafana.db",
                        "pragma journal_mode=wal;",
                    ]
                )
                pragma.wait()

            self.unit.status = ActiveStatus()
        except ExecError as e:
            # debug because, on initial container startup when Grafana has an open lock and is
            # populating, this comes up with ERRCODE: 26
            logger.debug("Could not apply journal_mode pragma. Exit code: {}".format(e.exit_code))
        except ConnectionError:
            logger.error(
                "Could not restart grafana-k8s -- Pebble socket does "
                "not exist or is not responsive"
            )

    def restart_litestream(self, leader: bool) -> None:
        """Restart the pebble container.

        `container.replan()` is intentionally avoided, since if no environment
        variables are changed, this will not actually restart Litestream.
        """
        layer = self._build_replication(leader)

        try:
            plan = self.containers["replication"].get_plan()
            if plan.services != layer.services:
                self.containers["replication"].add_layer("litestream", layer, combine=True)
                if self.containers["replication"].get_service("litestream").is_running():
                    self.containers["replication"].stop("litestream")

                self.containers["replication"].start("litestream")
                logger.info("Restarted replication")
        except ConnectionError:
            logger.error(
                "Could not restart replication -- Pebble socket does "
                "not exist or is not responsive"
            )

    def _parse_grafana_path(self, parts: ParseResult) -> dict:
        """Convert web_external_url into a usable path."""
        # urlparse.path parsing is absolutely horrid and only
        # guarantees any kind of sanity if there is a scheme
        if not parts.scheme and not parts.path.startswith("/"):
            # This could really be anything!
            logger.warning(
                "Could not determine web_external_url for Grafana. Please "
                "use a fully-qualified path or a bare subpath"
            )
            return {}

        return {
            "scheme": parts.scheme or "http",
            "host": "0.0.0.0",
            "port": parts.netloc.split(":")[1] if ":" in parts.netloc else PORT,
            "path": parts.path,
        }

    def _build_layer(self) -> Layer:
        """Construct the pebble layer information."""
        # Placeholder for when we add "proper" mysql support for HA
        extra_info = {
            "GF_DATABASE_TYPE": "sqlite3",
        }

        grafana_path = self.external_url
        if self._auth_env_vars:
            extra_info.update(self._auth_env_vars)

        grafana_path = self.external_url

        # We have to do this dance because urlparse() doesn't have any good
        # truthiness, and parsing an empty string is still 'true'
        if grafana_path:
            parts = self._parse_grafana_path(urlparse(grafana_path))

            # It doesn't matter unless there's a subpath, since the
            # redirect to login is fine with a bare hostname
            if parts and parts["path"]:
                extra_info.update(
                    {
                        "GF_SERVER_SERVE_FROM_SUB_PATH": "True",
                        "GF_SERVER_ROOT_URL": "{}://{}:{}{}".format(
                            parts["scheme"], parts["host"], parts["port"], parts["path"]
                        ),
                    }
                )

        layer = Layer(
            {
                "summary": "grafana-k8s layer",
                "description": "grafana-k8s layer",
                "services": {
                    self.name: {
                        "override": "replace",
                        "summary": "grafana-k8s service",
                        "command": "grafana-server -config {}".format(CONFIG_PATH),
                        "startup": "enabled",
                        "environment": {
                            "GF_SERVER_HTTP_PORT": str(PORT),
                            "GF_LOG_LEVEL": self.model.config["log_level"],
                            "GF_PLUGINS_ENABLE_ALPHA": "true",
                            "GF_PATHS_PROVISIONING": PROVISIONING_PATH,
                            "GF_SECURITY_ADMIN_USER": self.model.config["admin_user"],
                            "GF_SECURITY_ADMIN_PASSWORD": self._get_admin_password(),
                            "GF_USERS_AUTO_ASSIGN_ORG": str(
                                self.model.config["enable_auto_assign_org"]
                            ),
                            **extra_info,
                        },
                    }
                },
            }
        )

        return layer

    def _build_replication(self, primary: bool) -> Layer:
        """Construct the pebble layer information for litestream."""
        config = {}

        if primary:
            self.set_peer_data("replica_primary", socket.gethostbyname(socket.getfqdn()))
            config["LITESTREAM_ADDR"] = "{}:{}".format(
                socket.gethostbyname(socket.getfqdn()), "9876"
            )
        else:
            config["LITESTREAM_UPSTREAM_URL"] = "{}:{}".format(
                self.get_peer_data("replica_primary"), "9876"
            )

        layer = Layer(
            {
                "summary": "litestream layer",
                "description": "litestream layer",
                "services": {
                    "litestream": {
                        "override": "replace",
                        "summary": "litestream service",
                        "command": "litestream replicate -config /etc/litestream.yml",
                        "startup": "enabled",
                        "environment": {
                            **config,
                        },
                    }
                },
            }
        )

        return layer

    @property
    def grafana_version(self):
        """Grafana server version.

        Returns:
            A string equal to the Grafana server version.
        """
        container = self.containers["workload"]
        if not container.can_connect():
            return None
        version_output, _ = container.exec(["grafana-server", "-v"]).wait_output()
        # Output looks like this:
        # Version 8.2.6 (commit: d2cccfe, branch: HEAD)
        result = re.search(r"Version (\d*\.\d*\.\d*)", version_output)
        if result is None:
            return result
        return result.group(1)

    @property
    def grafana_config_ini_hash(self) -> str:
        """Returns the hash for the Grafana ini file."""
        return self._grafana_config_ini_hash or self._get_hash_for_file(CONFIG_PATH)

    @grafana_config_ini_hash.setter
    def grafana_config_ini_hash(self, hash: str) -> None:
        """Sets the Grafana config ini hash."""
        self._grafana_config_ini_hash = hash

    @property
    def grafana_datasources_hash(self) -> str:
        """Returns the hash for the Grafana ini file."""
        return self._grafana_datasources_hash or self._get_hash_for_file(DATASOURCES_PATH)

    @grafana_datasources_hash.setter
    def grafana_datasources_hash(self, hash: str) -> None:
        """Sets the Grafana config ini hash."""
        self._grafana_datasources_hash = hash

    def _get_hash_for_file(self, file: str) -> str:
        """Tries to connect to the container and hash a file.

        Args:
            file: a `str` filepath to read
        """
        if self.containers["workload"].can_connect():
            try:
                content = self.containers["workload"].pull(file)
                hash = hashlib.sha256(str(content.read()).encode("utf-8")).hexdigest()
                return hash
            except (FileNotFoundError, ProtocolError, PathError) as e:
                logger.warning(
                    "Could not read configuration from the Grafana workload container: {}".format(
                        e
                    )
                )

        return ""

    @property
    def build_info(self) -> dict:
        """Returns information about the running Grafana service."""
        return self.grafana_service.build_info

    def _generate_datasource_config(self) -> str:
        """Template out a Grafana datasource config.

        Template using the sources (and removed sources) the consumer knows about, and dump it to
        YAML.

        Returns:
            A a string-dumped YAML config for the datasources
        """
        # Boilerplate for the config file
        datasources_dict = {"apiVersion": 1, "datasources": [], "deleteDatasources": []}

        for source_info in self.source_consumer.sources:
            source = {
                "orgId": "1",
                "access": "proxy",
                "isDefault": "false",
                "name": source_info["source_name"],
                "type": source_info["source_type"],
                "url": source_info["url"],
            }
            if source_info.get("extra_fields", None):
                source["jsonData"] = source_info.get("extra_fields")

            # set timeout for querying this data source
            timeout = source.get("jsonData", {}).get("timeout", 0)
            configured_timeout = self.model.config.get("datasource_query_timeout")
            if timeout < configured_timeout:
                json_data = source.get("jsonData", {})
                json_data.update({"timeout": configured_timeout})
                source["jsonData"] = json_data

            datasources_dict["datasources"].append(source)  # type: ignore[attr-defined]

        # Also get a list of all the sources which have previously been purged and add them
        for name in self.source_consumer.sources_to_delete:
            source = {"orgId": 1, "name": name}
            datasources_dict["deleteDatasources"].append(source)  # type: ignore[attr-defined]

        datasources_string = yaml.dump(datasources_dict)
        return datasources_string

    def _on_get_admin_password(self, event: ActionEvent) -> None:
        """Returns the password for the admin user as an action response."""
        if not self.grafana_service.is_ready:
            event.fail("Grafana is not reachable yet. Please try again in a few minutes")
            return
        if self.grafana_service.password_has_been_changed(
            self.model.config["admin_user"], self._get_admin_password()
        ):
            event.set_results(
                {"admin-password": "Admin password has been changed by an administrator"}
            )
        else:
            event.set_results({"admin-password": self._get_admin_password()})

    def _get_admin_password(self) -> str:
        """Returns the password for the admin user."""
        if not self._stored.admin_password:
            self._stored.admin_password = self._generate_password()

        return self._stored.admin_password  # type: ignore

    def _poll_container(self, func: Callable, timeout: float = 2.0, delay: float = 0.1) -> bool:
        """Try to poll the container to work around Container.is_connect() being point-in-time.

        Args:
            func: a :Callable: to check, which should return a boolean.
            timeout: a :float: to time out after
            delay: a :float: to wait between checks

        """
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                if func():
                    return True

                time.sleep(delay)
            except (APIError, ConnectionError, ProtocolError):
                logger.debug("Failed to poll the container due to a Pebble error")

        return False

    def _generate_password(self) -> str:
        """Generates a random 12 character password."""
        # Really limited by what can be passed into shell commands, since this all goes
        # through subprocess. So much for complex password
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(12))

    def _resource_reqs_from_config(self) -> ResourceRequirements:
        limits = {"cpu": self.model.config.get("cpu"), "memory": self.model.config.get("memory")}
        requests = {"cpu": "0.25", "memory": "200Mi"}
        return adjust_resource_requirements(limits, requests, adhere_to_requests=True)

    def _on_resource_patch_failed(self, event: K8sResourcePatchFailedEvent):
        self.unit.status = BlockedStatus(event.message)

    @property
    def external_url(self) -> str:
        """Return the external hostname configured, if any."""
        baseurl = "http://{}:{}".format(socket.getfqdn(), PORT)
        web_external_url = self.model.config.get("web_external_url", "")

        if web_external_url:
            return web_external_url

        if self.ingress.is_ready():
            return "{}/{}".format(baseurl, "{}-{}".format(self.model.name, self.model.app.name))

        return baseurl

    @property
    def _ingress_config(self) -> dict:
        """Build a raw ingress configuration for Traefik."""
        fqdn = urlparse(socket.getfqdn()).path
        pattern = r"^{}\..*?{}\.".format(self.model.unit.name.replace("/", "-"), self.model.name)
        domain = re.split(pattern, fqdn)[1]

        external_path = urlparse(self.external_url).path or "{}-{}".format(
            self.model.name, self.model.app.name
        )

        routers = {
            "juju-{}-{}-router".format(self.model.name, self.model.app.name): {
                "entryPoints": ["web"],
                "rule": "PathPrefix(`{}`)".format(external_path),
                "service": "juju-{}-{}-service".format(self.model.name, self.app.name),
            }
        }

        services = {
            "juju-{}-{}-service".format(self.model.name, self.model.app.name): {
                "loadBalancer": {
                    "servers": [
                        {
                            "url": "http://{}.{}-endpoints.{}.{}:{}/".format(
                                self.model.unit.name.replace("/", "-"),
                                self.model.app.name,
                                self.model.name,
                                domain,
                                PORT,
                            )
                        }
                    ]
                }
            }
        }

        return {"http": {"routers": routers, "services": services}}

    @property
    def _auth_env_vars(self):
        return self.get_peer_data("auth_conf_env_vars")

    def _on_grafana_auth_conf_available(self, event: AuthRequirerCharmEvents):
        """Event handler for the auth_conf_available event.

        It sets authentication configuration environment variables if they have not been set yet.
        Environment variables are stored in peer data.
        The event can be emitted even there are no changes to the configuration so call `_configure` to check
        and avoid restarting if that is not needed.

        Args:
            event: a :class:`AuthRequirerCharmEvents` auth config sent from the provider
        """
        if not self.unit.is_leader():
            return
        if not self._auth_env_vars:
            env_vars = self.generate_auth_env_vars(event.auth)  # type: ignore[attr-defined]
            if env_vars:
                self.set_peer_data("auth_conf_env_vars", env_vars)
                self._configure()

    def generate_auth_env_vars(self, conf: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """Generates a dictionary of environment variables from the authentication config it gets.

        Args:
            conf: grafana authentication configuration that has the authentication mode as top level key.
        """
        auth_mode = next(iter(conf))
        if auth_mode not in VALID_AUTHENTICATION_MODES:
            logger.warning("Invalid authentication mode")
            return {}
        env_vars = {}
        auth_var_prefix = "GF_AUTH_" + auth_mode.upper() + "_"
        mode_enabled_var = auth_var_prefix + "ENABLED"
        env_vars[mode_enabled_var] = "True"
        for var in conf[auth_mode].keys():
            env_vars[auth_var_prefix + str(var).upper()] = str(conf[auth_mode][var])
        return env_vars


if __name__ == "__main__":
    main(GrafanaCharm, use_juju_for_storage=True)
