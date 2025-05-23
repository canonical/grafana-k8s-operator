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
import socket
import string
import subprocess
import time
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict, cast, Optional
from urllib.parse import urlparse

import yaml
from cosl import JujuTopology
from ops import main
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
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, Port
from ops.pebble import (
    APIError,
    ConnectionError,
    ChangeError,
    ExecError,
    Layer,
    PathError,
    ProtocolError,
)
from secret_storage import SecretStorage

from charms.catalogue_k8s.v1.catalogue import CatalogueConsumer, CatalogueItem
from charms.certificate_transfer_interface.v0.certificate_transfer import (
    CertificateAvailableEvent,
    CertificateRemovedEvent,
    CertificateTransferRequires,
)
from charms.grafana_k8s.v0.grafana_auth import AuthRequirer, AuthRequirerCharmEvents
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardConsumer
from charms.grafana_k8s.v0.grafana_metadata import GrafanaMetadataProvider
from charms.grafana_k8s.v0.grafana_source import (
    GrafanaSourceConsumer,
    GrafanaSourceEvents,
    SourceFieldsMissingError,
)
from charms.hydra.v0.oauth import (
    ClientConfig as OauthClientConfig,
    OAuthInfoChangedEvent,
    OAuthRequirer,
)
from charms.observability_libs.v0.kubernetes_compute_resources_patch import (
    K8sResourcePatchFailedEvent,
    KubernetesComputeResourcesPatch,
    ResourceRequirements,
    adjust_resource_requirements,
)
from charms.observability_libs.v1.cert_handler import CertHandler
from charms.parca_k8s.v0.parca_scrape import ProfilingEndpointProvider
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider
from charms.tempo_coordinator_k8s.v0.charm_tracing import trace_charm
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer, charm_tracing_config
from charms.traefik_k8s.v0.traefik_route import TraefikRouteRequirer
from grafana_client import Grafana, GrafanaCommError
from secret_storage import generate_password

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
GRAFANA_CRT_PATH = "/etc/grafana/grafana.crt"
GRAFANA_KEY_PATH = "/etc/grafana/grafana.key"
CA_CERT_PATH = Path("/usr/local/share/ca-certificates/cos-ca.crt")

DATABASE = "database"
PEER = "grafana"
PORT = 3000
PROFILING_PORT = 8080
DATABASE_PATH = "/var/lib/grafana/grafana.db"

# Template for storing trusted certificate in a file.
TRUSTED_CA_TEMPLATE = string.Template(
    "/usr/local/share/ca-certificates/trusted-ca-cert-$rel_id-ca.crt"
)
# https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/generic-oauth
OAUTH_SCOPES = "openid email offline_access"
OAUTH_GRANT_TYPES = ["authorization_code", "refresh_token"]


@trace_charm(
    tracing_endpoint="charm_tracing_endpoint",
    server_cert="server_cert",
    extra_types=[
        AuthRequirer,
        CertHandler,
        GrafanaDashboardConsumer,
        GrafanaSourceConsumer,
        KubernetesComputeResourcesPatch,
        MetricsEndpointProvider,
    ],
)
class GrafanaCharm(CharmBase):
    """Charm to run Grafana on Kubernetes.

    This charm allows for high-availability
    (as long as a non-sqlite database relation is present).

    Developers of this charm should be aware of the Grafana provisioning docs:
    https://grafana.com/docs/grafana/latest/administration/provisioning/
    """

    def __init__(self, *args):
        super().__init__(*args)

        # -- initialize states --
        self.name = "grafana"
        self.containers = {
            "workload": self.unit.get_container(self.name),
            "replication": self.unit.get_container("litestream"),
        }
        self._grafana_config_ini_hash = None
        self._grafana_datasources_hash = None
        self._topology = JujuTopology.from_charm(self)
        self._secret_storage = SecretStorage(self, "admin-password",
                                             default=lambda: {"password": generate_password()})

        # -- cert_handler
        self.cert_handler = CertHandler(
            charm=self,
            key="grafana-server-cert",
            peer_relation_name="replicas",
            sans=[socket.getfqdn()],
        )

        # -- trusted_cert_transfer
        self.trusted_cert_transfer = CertificateTransferRequires(self, "receive-ca-cert")

        # -- ingress via raw traefik_route
        # TraefikRouteRequirer expects an existing relation to be passed as part of the constructor,
        # so this may be none. Rely on `self.ingress.is_ready` later to check
        self.ingress = TraefikRouteRequirer(self, self.model.get_relation("ingress"), "ingress")  # type: ignore
        self.framework.observe(self.on["ingress"].relation_joined, self._configure_ingress)
        self.framework.observe(self.ingress.on.ready, self._on_ingress_ready)  # pyright: ignore
        self.framework.observe(self.on.leader_elected, self._configure_ingress)
        self.framework.observe(self.on.config_changed, self._configure_ingress)
        self.framework.observe(self.cert_handler.on.cert_changed, self._configure_ingress)

        # Assuming FQDN is always part of the SANs DNS.
        self.grafana_service = Grafana(f"{self._scheme}://{socket.getfqdn()}:{PORT}")

        self.metrics_endpoint = MetricsEndpointProvider(
            charm=self,
            jobs=self._metrics_scrape_jobs,
            refresh_event=[
                self.on.grafana_pebble_ready,  # pyright: ignore
                self.on.update_status,
                self.cert_handler.on.cert_changed,  # pyright: ignore
            ],
        )
        self.charm_tracing = TracingEndpointRequirer(
            self, relation_name="charm-tracing", protocols=["otlp_http"]
        )
        self.workload_tracing = TracingEndpointRequirer(
            self, relation_name="workload-tracing", protocols=["otlp_grpc"]
        )
        self.charm_tracing_endpoint, self.server_cert = charm_tracing_config(
            self.charm_tracing, CA_CERT_PATH
        )
        self.profiling = ProfilingEndpointProvider(self, jobs=self._profiling_scrape_jobs)

        # -- standard events
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(
            self.on.grafana_pebble_ready,
            self._on_pebble_ready,  # pyright: ignore
        )
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(
            self.on.get_admin_password_action,  # pyright: ignore
            self._on_get_admin_password,
        )

        # -- grafana_source relation observations
        self.source_consumer = GrafanaSourceConsumer(
            self,
            grafana_uid=self.unique_name,
            grafana_base_url=self.external_url,
            relation_name="grafana-source",
        )
        self.framework.observe(
            self.source_consumer.on.sources_changed,  # pyright: ignore
            self._on_grafana_source_changed,
        )
        self.framework.observe(
            self.source_consumer.on.sources_to_delete_changed,  # pyright: ignore
            self._on_grafana_source_changed,
        )

        # -- self-monitoring
        self.framework.observe(
            self.source_consumer.on.sources_changed,  # pyright: ignore
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
            self.dashboard_consumer.on.dashboards_changed,  # pyright: ignore
            self._on_dashboards_changed,
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
        self.framework.observe(
            self.resource_patch.on.patch_failed,
            self._on_resource_patch_failed,  # pyright: ignore
        )
        # -- grafana_auth relation observations
        self.grafana_auth_requirer = AuthRequirer(
            self,
            relation_name="grafana-auth",
            urls=[f"{self.app.name}:{PORT}"],
            refresh_event=self.on.grafana_pebble_ready,  # pyright: ignore
        )
        self.framework.observe(
            self.grafana_auth_requirer.on.auth_conf_available,  # pyright: ignore
            self._on_grafana_auth_conf_available,
        )
        # -- profiling observations
        self.framework.observe(
            self.on.profiling_endpoint_relation_created,  # type: ignore
            self._on_profiling_endpoint_created,
        )
        self.framework.observe(
            self.on.profiling_endpoint_relation_broken,  # type: ignore
            self._on_profiling_endpoint_broken,
        )
        # -- workload tracing observations
        self.framework.observe(
            self.workload_tracing.on.endpoint_changed,  # type: ignore
            self._on_workload_tracing_endpoint_changed,
        )
        self.framework.observe(
            self.workload_tracing.on.endpoint_removed,  # type: ignore
            self._on_workload_tracing_endpoint_removed,
        )

        # -- cert_handler observations
        self.framework.observe(
            self.cert_handler.on.cert_changed,
            self._on_server_cert_changed,  # pyright: ignore
        )

        # -- trusted_cert_transfer observations
        self.framework.observe(
            self.trusted_cert_transfer.on.certificate_available,
            self._on_trusted_certificate_available,  # pyright: ignore
        )
        self.framework.observe(
            self.trusted_cert_transfer.on.certificate_removed,
            self._on_trusted_certificate_removed,  # pyright: ignore
        )
        # oauth relation
        self.oauth = OAuthRequirer(self, self._oauth_client_config)

        # oauth relation observations
        self.framework.observe(
            self.oauth.on.oauth_info_changed,
            self._on_oauth_info_changed,  # pyright: ignore
        )
        self.framework.observe(
            self.oauth.on.oauth_info_removed,
            self._on_oauth_info_changed,  # pyright: ignore
        )

        # self.catalog = CatalogueConsumer(charm=self, item=self._catalogue_item)

        self.catalog = CatalogueConsumer(charm=self, item=self._catalogue_item)

        # -- grafana-metadata relation handling
        self.framework.observe(self.on.leader_elected, self._send_grafana_metadata)
        self.framework.observe(
            self.on["grafana-metadata"].relation_joined, self._send_grafana_metadata
        )
        self.framework.observe(self.ingress.on.ready, self._send_grafana_metadata)
        self.framework.observe(self.cert_handler.on.cert_changed, self._send_grafana_metadata)

    @property
    def _catalogue_item(self) -> CatalogueItem:
        return CatalogueItem(
            name="Grafana",
            icon="bar-chart",
            url=self.external_url,
            description=(
                "Grafana allows you to query, visualize, alert on, and "
                "visualize metrics from mixed datasources in configurable "
                "dashboards for observability."
            ),
        )

    def _on_install(self, _):
        """Handler for the "install" event during which we will update the K8s service."""
        self.set_ports()

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

    def _on_ingress_ready(self, _) -> None:
        """Once Traefik tells us our external URL, make sure we reconfigure Grafana."""
        self._configure()

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

        litestream_config = {"addr": ":9876", "dbs": [{"path": DATABASE_PATH}]}

        if not leader:
            litestream_config["dbs"][0].update(
                {"upstream": {"url": "http://${LITESTREAM_UPSTREAM_URL}"}}
            )  # type: ignore

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
            source for source in source_related_apps if source in scrape_related_apps
        )

        dashboards_dir_path = os.path.join(PROVISIONING_PATH, "dashboards")
        self.init_dashboard_provisioning(dashboards_dir_path)

        dashboard_path = os.path.join(dashboards_dir_path, "self_dashboard.json")
        if has_relation and self.unit.is_leader():
            # This is not going through the library due to the massive refactor needed in order
            # to squash all the `validate_relation_direction` and structure around smashing
            # the datastructures for a self-monitoring use case.
            container.push(
                dashboard_path, Path("src/self_dashboard.json").read_bytes(), make_dirs=True
            )
        elif not has_relation or isinstance(event, RelationBrokenEvent):
            if container.list_files(dashboards_dir_path, pattern="self_dashboard.json"):
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

    def _check_datasource_provisioning(self) -> bool:
        """Check whether datasources need to be (re)provisioned."""
        grafana_datasources = self._generate_datasource_config()
        datasources_hash = hashlib.sha256(str(grafana_datasources).encode("utf-8")).hexdigest()
        if not self.grafana_datasources_hash == datasources_hash:
            self.grafana_datasources_hash = datasources_hash
            self._update_datasource_config(grafana_datasources)
            logger.info("Updated Grafana's datasource configuration")

            return True
        return False

    def _configure(self, force_restart: bool = False) -> None:
        """Configure Grafana.

        Generate configuration files and check the sums against what is
        already stored in the charm. If either the base Grafana config
        or the datasource config differs, restart Grafana.

        If ``force_restart``: restart grafana regardless.
        """
        if not self.containers["workload"].can_connect():
            return
        logger.debug("Handling grafana-k8s configuration change")
        restart = force_restart

        # Generate a new base config and see if it differs from what we have.
        # If it does, store it and signal that we should restart Grafana
        grafana_config_ini = self._generate_grafana_config()
        config_ini_hash = hashlib.sha256(str(grafana_config_ini).encode("utf-8")).hexdigest()
        if not self.grafana_config_ini_hash == config_ini_hash:
            self.grafana_config_ini_hash = config_ini_hash
            self._update_grafana_config_ini(grafana_config_ini)
            logger.info("Updated Grafana's base configuration")

            restart = True

        self.oauth.update_client_config(client_config=self._oauth_client_config)

        if self._check_datasource_provisioning():
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
            # We can basically only get here if the charm is completely restarted, but all
            # the configs are correct, with the correct pebble plan, such as a node reboot.
            #
            # A node reboot does not send any identifiable events (`start`, `pebble_ready`), so
            # this is more or less the 'fallthrough' part of a case statement
            if not isinstance(self.unit.status, ActiveStatus):
                self.unit.status = ActiveStatus()

        self.catalog.update_item(item=self._catalogue_item)

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
        """Check whether there are any other Grafanas as peers."""
        rel = self.model.get_relation(PEER)
        return len(rel.units) > 0 if rel is not None else False

    @property
    def peers(self):
        """Fetch the peer relation."""
        return self.model.get_relation(PEER)

    def set_peer_data(self, key: str, data: Any) -> None:
        """Put information into the peer data bucket instead of `StoredState`."""
        if self.peers:
            self.peers.data[self.app][key] = json.dumps(data)

    def get_peer_data(self, key: str) -> Any:
        """Retrieve information from the peer data bucket instead of `StoredState`."""
        if not self.peers:
            return {}
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

        if not container.exists(dashboard_path):
            try:
                container.push(default_config, default_config_string, make_dirs=True)
                self.restart_grafana()
            except ConnectionError:
                logger.warning(
                    "Could not push default dashboard configuration. Pebble shutting down?"
                )

    def _on_dashboards_changed(self, event) -> None:
        self._update_dashboards(event)

    def _update_dashboards(self, event) -> None:
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

    def set_ports(self):
        """Open necessary (and close no longer needed) workload ports."""
        planned_ports = {Port(protocol="tcp", port=PORT)} if self.unit.is_leader() else set()
        actual_ports = self.unit.opened_ports()

        # Ports may change across an upgrade, so need to sync
        ports_to_close = actual_ports.difference(planned_ports)
        for p in ports_to_close:
            self.unit.close_port(p.protocol, p.port)

        new_ports_to_open = planned_ports.difference(actual_ports)
        for p in new_ports_to_open:
            self.unit.open_port(p.protocol, p.port)

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
            field: event.relation.data[event.app].get(field)
            for field in REQUIRED_DATABASE_FIELDS  # type: ignore
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
        `datastore.database` is all we need for the change to be propagated
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

    def _on_workload_tracing_endpoint_changed(self, event: RelationChangedEvent) -> None:
        """Adds workload tracing information to grafana's config."""
        self._configure()

    def _on_workload_tracing_endpoint_removed(self, event: RelationBrokenEvent) -> None:
        """Removes workload tracing information from grafana's config."""
        self._configure()

    def _on_profiling_endpoint_created(self, _) -> None:
        """Turn on grafana server profiling."""
        self._configure()

    def _on_profiling_endpoint_broken(self, _) -> None:
        """Turn off grafana server profiling (if no other profiling relations exist)."""
        self._configure()

    def _generate_grafana_config(self) -> str:
        """Generate a database configuration for Grafana.

        For now, this only creates database information, since everything else
        can be set in ENV variables, but leave for expansion later so we can
        hide auth secrets
        """
        configs = [self._generate_tracing_config(), self._generate_analytics_config()]
        if self.has_db:
            configs.append(self._generate_database_config())
        else:
            with StringIO() as data:
                config_ini = configparser.ConfigParser()
                config_ini["database"] = {
                    "type": "sqlite3",
                    "path": DATABASE_PATH,
                }
                config_ini.write(data)
                data.seek(0)
                configs.append(data.read())

        return "\n".join(filter(bool, configs))

    def _generate_tracing_config(self) -> str:
        """Generate tracing configuration.

        Returns:
            A string containing the required tracing information to be stubbed into the config
            file.
        """
        tracing = self.workload_tracing
        if not tracing.is_ready():
            return ""
        endpoint = tracing.get_endpoint("otlp_grpc")
        if endpoint is None:
            return ""

        config_ini = configparser.ConfigParser()
        config_ini["tracing.opentelemetry"] = {
            "sampler_type": "probabilistic",
            "sampler_param": "0.01",
        }
        # ref: https://github.com/grafana/grafana/blob/main/conf/defaults.ini#L1505
        config_ini["tracing.opentelemetry.otlp"] = {
            "address": endpoint,
        }

        # This is silly, but a ConfigParser() handles this nicer than
        # raw string manipulation
        data = StringIO()
        config_ini.write(data)
        ret = data.getvalue()
        return ret

    def _generate_analytics_config(self) -> str:
        """Generate analytics configuration.

        Returns:
            A string containing the analytics config to be stubbed into the config file.
        """
        if self.config["reporting_enabled"]:
            return ""
        config_ini = configparser.ConfigParser()
        # Ref: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#analytics
        config_ini["analytics"] = {
            "reporting_enabled": "false",
            "check_for_updates": "false",
            "check_for_plugin_updates": "false",
        }

        data = StringIO()
        config_ini.write(data)
        ret = data.getvalue()
        return ret

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

        # This is still silly
        data = StringIO()
        config_ini.write(data)
        ret = data.getvalue()
        return ret

    #####################################

    # PEBBLE OPERATIONS

    #####################################

    def _on_pebble_ready(self, event) -> None:
        """When Pebble is ready, start everything up."""
        self._configure()
        self.source_consumer.upgrade_keys()
        self.dashboard_consumer.update_dashboards()
        self._update_dashboards(event)

        # Create provisioning subfolders to avoid errors on startup
        workload = self.containers["workload"]
        for d in ("plugins", "notifiers", "alerting"):
            workload.make_dir(Path(PROVISIONING_PATH) / d, make_parents=True)

        # In case of a restart caused by an error, we collect all trusted certs from relation
        # receive-ca-cert
        self._update_trusted_ca_certs()

        version = self.grafana_version
        if version is not None:
            self.unit.set_workload_version(version)
        else:
            logger.debug(
                "Cannot set workload version at this time: could not get Alertmanager version."
            )

    def _cert_ready(self):
        # Verify that the certificate and key are correctly configured
        workload = self.containers["workload"]
        return (
                self.cert_handler.server_cert
                and self.cert_handler.private_key
                and workload.exists(GRAFANA_CRT_PATH)
                and workload.exists(GRAFANA_KEY_PATH)
        )

    def restart_grafana(self) -> None:
        """Restart the pebble container.

        `container.replan()` is intentionally avoided, since if no environment
        variables are changed, this will not actually restart Grafana, which is
        necessary to reload the provisioning files.

        Note that Grafana does not support SIGHUP, so a full restart is needed.
        """
        # Before building the layer, we update our certificates if tls is enabled.
        # This is needed here to circumvent a code ordering issue that results in:
        #   *api.HTTPServer run error: cert_file cannot be empty when using HTTPS
        #   ERROR cannot start service: exited quickly with code 1
        if self.cert_handler.enabled:
            logger.debug("TLS enabled: updating certs")
            self._update_cert()
            # now that this is done, build_layer should include cert and key into the config and we'll
            # be sure that the files are actually there before grafana is (re)started.

        # If available, we collect all trusted certs from the receive-ca-cert relation
        # we do this here, downstream from a container readiness check
        self._update_trusted_ca_certs()

        layer = self._build_layer()
        try:
            self.containers["workload"].add_layer(self.name, layer, combine=True)
            if self.containers["workload"].get_service(self.name).is_running():
                self.containers["workload"].stop(self.name)

            self.containers["workload"].start(self.name)
            logger.info("Restarted grafana-k8s")

            if self._poll_container(self.containers["workload"].can_connect):
                # We should also make sure sqlite is in WAL mode for replication
                self._push_sqlite_static()

                pragma = self.containers["workload"].exec(
                    [
                        "/usr/local/bin/sqlite3",
                        DATABASE_PATH,
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
        except ChangeError as e:
            logger.error("Could not restart grafana at this time: %s", e)

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

    def _build_layer(self) -> Layer:
        """Construct the pebble layer information.

        Ref: https://github.com/grafana/grafana/blob/main/conf/defaults.ini
        """
        # Placeholder for when we add "proper" mysql support for HA
        extra_info = {
            "GF_DATABASE_TYPE": "sqlite3",
        }

        # Juju Proxy settings
        extra_info.update(
            {
                "https_proxy": os.environ.get("JUJU_CHARM_HTTPS_PROXY", ""),
                "http_proxy": os.environ.get("JUJU_CHARM_HTTP_PROXY", ""),
                "no_proxy": os.environ.get("JUJU_CHARM_NO_PROXY", ""),
            }
        )

        if self._auth_env_vars:
            extra_info.update(self._auth_env_vars)

        # For stripPrefix middleware to work correctly, we need to set serve_from_sub_path and
        # root_url in a particular way.
        extra_info.update(
            {
                "GF_SERVER_SERVE_FROM_SUB_PATH": "True",
                # https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#root_url
                "GF_SERVER_ROOT_URL": self.external_url,
                "GF_SERVER_ENFORCE_DOMAIN": "false",
                # When traefik provides TLS termination then traefik is https, but grafana is http.
                # We need to set GF_SERVER_PROTOCOL.
                # https://grafana.com/tutorials/run-grafana-behind-a-proxy/#1
                "GF_SERVER_PROTOCOL": self._scheme,
            }
        )

        # For consistency, set cert entries on the same condition as scheme is set to https.
        # NOTE: On one hand, we want to tell grafana to use TLS as soon as the tls relation is in
        # place; on the other hand, the certs may not be written to disk yet (they need to be
        # returned over relation data, go to peer data, and eventually be written to disk). When
        # grafana is restarted in HTTPS mode but without certs in place, we'll see a brief error:
        # "error: cert_file cannot be empty when using HTTPS".
        if self._scheme == "https":
            extra_info.update(
                {
                    "GF_SERVER_CERT_KEY": GRAFANA_KEY_PATH,
                    "GF_SERVER_CERT_FILE": GRAFANA_CRT_PATH,
                }
            )

        if self.oauth.is_client_created():
            oauth_provider_info = self.oauth.get_provider_info()

            if oauth_provider_info:
                extra_info.update(
                    {
                        "GF_AUTH_GENERIC_OAUTH_ENABLED": "True",
                        "GF_AUTH_GENERIC_OAUTH_NAME": "external identity provider",
                        "GF_AUTH_GENERIC_OAUTH_CLIENT_ID": cast(
                            str, oauth_provider_info.client_id
                        ),
                        "GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET": cast(
                            str, oauth_provider_info.client_secret
                        ),
                        "GF_AUTH_GENERIC_OAUTH_SCOPES": OAUTH_SCOPES,
                        "GF_AUTH_GENERIC_OAUTH_AUTH_URL": oauth_provider_info.authorization_endpoint,
                        "GF_AUTH_GENERIC_OAUTH_TOKEN_URL": oauth_provider_info.token_endpoint,
                        "GF_AUTH_GENERIC_OAUTH_API_URL": oauth_provider_info.userinfo_endpoint,
                        "GF_AUTH_GENERIC_OAUTH_USE_REFRESH_TOKEN": "True",
                        # TODO: This toggle will be removed on grafana v10.3, remove it
                        "GF_FEATURE_TOGGLES_ENABLE": "accessTokenExpirationCheck",
                    }
                )

        if self.workload_tracing.is_ready():
            topology = self._topology
            extra_info.update(
                {
                    "OTEL_RESOURCE_ATTRIBUTES": f"juju_application={topology.application},juju_model={topology.model}"
                                                + f",juju_model_uuid={topology.model_uuid},juju_unit={topology.unit},juju_charm={topology.charm_name}",
                }
            )

        # if we have any profiling relations, switch on profiling
        if self.model.relations.get("profiling-endpoint"):
            # https://grafana.com/docs/grafana/v9.5/setup-grafana/configure-grafana/configure-tracing/#turn-on-profiling
            extra_info.update(
                {
                    "GF_DIAGNOSTICS_PROFILING_ENABLED": "true",
                    "GF_DIAGNOSTICS_PROFILING_ADDR": "0.0.0.0",
                    "GF_DIAGNOSTICS_PROFILING_PORT": str(PROFILING_PORT),
                }
            )

        # If we're followers, we don't need to set any credentials on the grafana process.
        # This Grafana instance will inherit them automatically from the replication primary (the leader).
        if self.unit.is_leader():
            # self.admin_password is guaranteed str if this unit is leader
            extra_info["GF_SECURITY_ADMIN_PASSWORD"] = cast(str, self.admin_password)
            extra_info["GF_SECURITY_ADMIN_USER"] = cast(str, self.model.config["admin_user"])

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
                            "GF_LOG_LEVEL": cast(str, self.model.config["log_level"]),
                            "GF_PLUGINS_ENABLE_ALPHA": "true",
                            "GF_PATHS_PROVISIONING": PROVISIONING_PATH,
                            "GF_SECURITY_ALLOW_EMBEDDING": str(
                                self.model.config["allow_embedding"]
                            ).lower(),
                            "GF_AUTH_ANONYMOUS_ENABLED": str(
                                self.model.config["allow_anonymous_access"]
                            ).lower(),
                            "GF_USERS_AUTO_ASSIGN_ORG": str(
                                self.model.config["enable_auto_assign_org"]
                            ).lower(),
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
            A string-dumped YAML config for the datasources
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
            if source_info.get("secure_extra_fields", None):
                source["secureJsonData"] = source_info.get("secure_extra_fields")

            # set timeout for querying this data source
            timeout = int(source.get("jsonData", {}).get("timeout", 0))
            configured_timeout = int(self.model.config.get("datasource_query_timeout", 0))
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

    class GetAdminPWDFailures:
        """Possible failure messages for get-admin-password failures."""
        waiting_for_leader = "Still waiting for the leader to generate an admin password..."
        not_reachable = 'Grafana is not reachable yet. Please try again in a few minutes'
        perhaps_changed_by_admin = ("Admin password may have been changed by an administrator. "
                                    "To be sure, run this action on the leader unit.")
        changed_by_admin = "Admin password has been changed by an administrator."

    def _on_get_admin_password(self, event: ActionEvent):
        """Returns the grafana url and password for the admin user as an action response."""
        admin_password = self.admin_password

        if not self.unit.is_leader() and admin_password is None:
            return event.fail(self.GetAdminPWDFailures.waiting_for_leader)

        if not admin_password:
            # if we got here this means this unit is leader; so we must have generated a password.
            # this should never happen. No Way Jose.
            raise RuntimeError()

        if not self.grafana_service.is_ready:
            return event.fail(self.GetAdminPWDFailures.not_reachable)

        try:
            pw_changed = self.grafana_service.password_has_been_changed(
                cast(str, self.model.config["admin_user"]), admin_password
            )
        except GrafanaCommError:
            logger.exception("failed getting admin password from service")
            event.log("Unexpected exception encountered while getting admin password from service: "
                      "see logs for more.")
            return event.fail(self.GetAdminPWDFailures.not_reachable)

        if pw_changed:
            if self.unit.is_leader():
                msg = self.GetAdminPWDFailures.changed_by_admin
            else:
                # it takes a little bit of time for grafana to settle on the
                # authentication data provided by the leader unit
                msg = self.GetAdminPWDFailures.perhaps_changed_by_admin

            event.set_results(
                {
                    "url": self.external_url,
                    "admin-password": msg,
                }
            )
        else:
            event.set_results(
                {"url": self.external_url, "admin-password": admin_password}
            )
        return None

    @property
    def admin_password(self) -> Optional[str]:
        """The admin password."""
        contents = self._secret_storage.contents
        if not contents:
            return None
        return contents.get('password')

    def _poll_container(
            self, func: Callable[[], bool], timeout: float = 2.0, delay: float = 0.1
    ) -> bool:
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

    def _resource_reqs_from_config(self) -> ResourceRequirements:
        limits = {"cpu": self.model.config.get("cpu"), "memory": self.model.config.get("memory")}
        requests = {"cpu": "0.25", "memory": "200Mi"}
        return adjust_resource_requirements(limits, requests, adhere_to_requests=True)

    def _on_resource_patch_failed(self, event: K8sResourcePatchFailedEvent):
        self.unit.status = BlockedStatus(str(event.message))

    @property
    def _scheme(self) -> str:
        return "https" if self.cert_handler.server_cert else "http"

    @property
    def internal_url(self) -> str:
        """Return workload's internal URL. Used for ingress."""
        return f"{self._scheme}://{socket.getfqdn()}:{PORT}"

    @property
    def external_url(self) -> str:
        """Return the external hostname configured, if any."""
        if self.ingress.external_host:
            path_prefix = f"{self.model.name}-{self.model.app.name}"
            # The scheme we use here needs to be the ingress URL's scheme:
            # If traefik is providing TLS termination then the ingress scheme is https, but
            # grafana's scheme is still http.
            return f"{self.ingress.scheme or 'http'}://{self.ingress.external_host}/{path_prefix}"
        return self.internal_url

    @property
    def _ingress_config(self) -> dict:
        """Build a raw ingress configuration for Traefik."""
        # The path prefix is the same as in ingress per app
        external_path = f"{self.model.name}-{self.model.app.name}"

        redirect_middleware = (
            {
                f"juju-sidecar-redir-https-{self.model.name}-{self.model.app.name}": {
                    "redirectScheme": {
                        "permanent": True,
                        "port": 443,
                        "scheme": "https",
                    }
                }
            }
            if self._scheme == "https"
            else {}
        )

        middlewares = {
            f"juju-sidecar-noprefix-{self.model.name}-{self.model.app.name}": {
                "stripPrefix": {"forceSlash": False, "prefixes": [f"/{external_path}"]},
            },
            **redirect_middleware,
        }

        routers = {
            "juju-{}-{}-router".format(self.model.name, self.model.app.name): {
                "entryPoints": ["web"],
                "rule": f"PathPrefix(`/{external_path}`)",
                "middlewares": list(middlewares.keys()),
                "service": "juju-{}-{}-service".format(self.model.name, self.app.name),
            },
            "juju-{}-{}-router-tls".format(self.model.name, self.model.app.name): {
                "entryPoints": ["websecure"],
                "rule": f"PathPrefix(`/{external_path}`)",
                "middlewares": list(middlewares.keys()),
                "service": "juju-{}-{}-service".format(self.model.name, self.app.name),
                "tls": {
                    "domains": [
                        {
                            "main": self.ingress.external_host,
                            "sans": [f"*.{self.ingress.external_host}"],
                        },
                    ],
                },
            },
        }

        services = {
            "juju-{}-{}-service".format(self.model.name, self.model.app.name): {
                "loadBalancer": {"servers": [{"url": self.internal_url}]}
            }
        }

        return {"http": {"routers": routers, "services": services, "middlewares": middlewares}}

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

    @property
    def _metrics_scrape_jobs(self) -> list:
        parts = urlparse(self.internal_url)
        job = {"static_configs": [{"targets": [parts.netloc]}], "scheme": self._scheme}
        return [job]

    @property
    def _profiling_scrape_jobs(self) -> list:
        job = {"static_configs": [{"targets": [f"*:{PROFILING_PORT}"]}], "scheme": self._scheme}
        return [job]

    def _on_server_cert_changed(self, _):
        # this triggers a restart, which triggers a cert update.
        self._configure(force_restart=True)

    def _update_cert(self):
        container = self.containers["workload"]
        if self.cert_handler.server_cert:
            # Save the workload certificates
            container.push(
                GRAFANA_CRT_PATH,
                self.cert_handler.server_cert,
                make_dirs=True,
            )
        else:
            container.remove_path(GRAFANA_CRT_PATH, recursive=True)

        if self.cert_handler.private_key:
            container.push(
                GRAFANA_KEY_PATH,
                self.cert_handler.private_key,
                make_dirs=True,
            )
        else:
            container.remove_path(GRAFANA_KEY_PATH, recursive=True)

        if self.cert_handler.ca_cert:
            # Save the CA among the trusted CAs and trust it
            container.push(
                CA_CERT_PATH,
                self.cert_handler.ca_cert,
                make_dirs=True,
            )

            # Repeat for the charm container. We need it there for grafana client requests.
            CA_CERT_PATH.parent.mkdir(exist_ok=True, parents=True)
            CA_CERT_PATH.write_text(self.cert_handler.ca_cert)
        else:
            container.remove_path(CA_CERT_PATH, recursive=True)
            # Repeat for the charm container.
            CA_CERT_PATH.unlink(missing_ok=True)

        container.exec(["update-ca-certificates", "--fresh"]).wait()
        subprocess.run(["update-ca-certificates", "--fresh"])

    def _on_trusted_certificate_available(self, event: CertificateAvailableEvent):
        if not self.containers["workload"].can_connect():
            logger.warning("Cannot connect to Pebble. Deferring event.")
            event.defer()
            return

        self.restart_grafana()

    def _update_trusted_ca_certs(self):
        """This function receives the trusted certificates from the certificate_transfer integration.

        Grafana needs to restart to use newly received certificates. Certificates attached to the
        relation need to be pulled before Grafana is started.
        This function is needed because relation events are not emitted on upgrade, and because we
        do not have (nor do we want) persistent storage for certs.
        """
        if not self.model.get_relation(relation_name=self.trusted_cert_transfer.relationship_name):
            return

        logger.info(
            "Pulling trusted ca certificates from %s relation.",
            self.trusted_cert_transfer.relationship_name,
        )
        container = self.containers["workload"]
        for relation in self.model.relations.get(self.trusted_cert_transfer.relationship_name, []):
            # For some reason, relation.units includes our unit and app. Need to exclude them.
            for unit in set(relation.units).difference([self.app, self.unit]):
                # Note: this nested loop handles the case of multi-unit CA, each unit providing
                # a different ca cert, but that is not currently supported by the lib itself.
                cert_path = TRUSTED_CA_TEMPLATE.substitute(rel_id=relation.id)
                if cert := relation.data[unit].get("ca"):
                    container.push(cert_path, cert, make_dirs=True)

        container.exec(["update-ca-certificates", "--fresh"]).wait()

    def _on_trusted_certificate_removed(self, event: CertificateRemovedEvent):
        # All certificates received from the relation are in separate files marked by the relation id.
        container = self.containers["workload"]
        cert_path = TRUSTED_CA_TEMPLATE.substitute(rel_id=event.relation_id)
        container.remove_path(cert_path, recursive=True)
        self.restart_grafana()

    @property
    def _oauth_client_config(self) -> OauthClientConfig:
        return OauthClientConfig(
            os.path.join(self.external_url, "login/generic_oauth"),
            OAUTH_SCOPES,
            OAUTH_GRANT_TYPES,
        )

    def _on_oauth_info_changed(self, event: OAuthInfoChangedEvent) -> None:
        """Event handler for the oauth_info_changed event."""
        self._configure()

    def _push_sqlite_static(self):
        # for ease of mocking in unittests, this is a standalone function
        self.containers["workload"].push(
            "/usr/local/bin/sqlite3",
            Path("sqlite-static").read_bytes(),
            permissions=0o755,
            make_dirs=True,
        )

    @property
    def unique_name(self):
        """Returns a unique identifier for this application."""
        return "juju_{}_{}_{}_{}".format(
            self.model.name,
            self.model.uuid,
            self.model.app.name,
            self.model.unit.name.split("/")[1],  # type: ignore
        )

    def _send_grafana_metadata(self, _):
        """Send metadata to related applications on the grafana-metadata relation."""
        if not self.unit.is_leader():
            return

        # grafana-metadata should only send an external URL if it's set, otherwise it leaves that empty
        internal_url = self.internal_url
        external_url = self.external_url
        if external_url == internal_url:
            # external_url is not set and just defaulted back to internal_url.  Set it to None
            external_url = None

        grafana_metadata = GrafanaMetadataProvider(
            relation_mapping=self.model.relations,
            app=self.app,
            relation_name="grafana-metadata",
        )
        grafana_metadata.publish(
            grafana_uid=self.unique_name,
            ingress_url=external_url,
            direct_url=internal_url,
        )


if __name__ == "__main__":
    main(GrafanaCharm, use_juju_for_storage=True)
