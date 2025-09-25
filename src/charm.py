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

import logging
import os
import socket
import subprocess
from pathlib import Path
from typing import Any, Dict, cast, Optional
from urllib.parse import urlparse

from cosl import JujuTopology
from cosl.reconciler import all_events, observe_events
from ops import ActiveStatus, CollectStatusEvent, main
from ops.charm import (
    ActionEvent,
    CharmBase,
    RelationBrokenEvent,
    RelationChangedEvent,
)
from ops.model import Port
from secret_storage import SecretStorage

from charms.catalogue_k8s.v1.catalogue import CatalogueConsumer, CatalogueItem
from charms.certificate_transfer_interface.v1.certificate_transfer import (
    CertificateTransferRequires,
)
from charms.grafana_k8s.v0.grafana_auth import AuthRequirer, AuthRequirerCharmEvents
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardConsumer
from charms.grafana_k8s.v0.grafana_metadata import GrafanaMetadataProvider
from charms.grafana_k8s.v0.grafana_source import (
    GrafanaSourceConsumer,
    SourceFieldsMissingError,
)
from charms.hydra.v0.oauth import (
    ClientConfig as OauthClientConfig,
    OAuthRequirer,
    OauthProviderConfig
)
from charms.observability_libs.v0.kubernetes_compute_resources_patch import (
    KubernetesComputeResourcesPatch,
    ResourceRequirements,
    adjust_resource_requirements,
)
from charms.parca_k8s.v0.parca_scrape import ProfilingEndpointProvider
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider
from charms.tempo_coordinator_k8s.v0.charm_tracing import trace_charm
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer, charm_tracing_config
from charms.traefik_k8s.v0.traefik_route import TraefikRouteRequirer, TraefikRouteRequirerReadyEvent
from grafana import Grafana
from grafana_client import GrafanaClient, GrafanaCommError
from grafana_config import GrafanaConfig
from secret_storage import generate_password
from litestream import Litestream
from relation import Relation
from models import DatasourceConfig, PebbleEnvironment, TLSConfig
from charms.tls_certificates_interface.v4.tls_certificates import (
    CertificateRequestAttributes,
    TLSCertificatesRequiresV4,
)
from constants import (
    PEER_RELATION,
    WORKLOAD_PORT,
    OAUTH_SCOPES,
    CA_CERT_PATH,
    GRAFANA_WORKLOAD,
    DATABASE_RELATION,
    PROFILING_PORT,
    OAUTH_GRANT_TYPES,
    REQUIRED_DATABASE_FIELDS,
    VALID_AUTHENTICATION_MODES)

logger = logging.getLogger()

@trace_charm(
    tracing_endpoint="charm_tracing_endpoint",
    server_cert="server_cert",
    extra_types=[
        AuthRequirer,
        TLSCertificatesRequiresV4,
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
        self._topology = JujuTopology.from_charm(self)
        self._fqdn = socket.getfqdn()
        self.peers = Relation(app=self.app, relation=self.model.get_relation(PEER_RELATION))
        self._secret_storage = SecretStorage(self, "admin-password",
                                             default=lambda: {"password": generate_password()})


        # -- certificates
        self._csr_attributes = CertificateRequestAttributes(
            # the `common_name` field is required but limited to 64 characters.
            # since it's overridden by sans, we can use a short,
            # constrained value like app name.
            common_name=self.app.name,
            sans_dns=frozenset((self._fqdn,)),
        )
        self._cert_requirer = TLSCertificatesRequiresV4(
            charm=self,
            relationship_name="certificates",
            certificate_requests=[self._csr_attributes],
        )

        # -- trusted_cert_transfer
        self.trusted_cert_transfer = CertificateTransferRequires(self, "receive-ca-cert")

        # -- ingress via raw traefik_route
        # TraefikRouteRequirer expects an existing relation to be passed as part of the constructor,
        # so this may be none. Rely on `self.ingress.is_ready` later to check
        self.ingress = TraefikRouteRequirer(self, self.model.get_relation("ingress"), "ingress")  # type: ignore

        self.metrics_endpoint = MetricsEndpointProvider(
            charm=self,
            jobs=self._metrics_scrape_jobs,
            refresh_event=[
                self.on.grafana_pebble_ready,  # pyright: ignore
                self.on.update_status,
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

        # -- grafana_source relation observations
        self.source_consumer = GrafanaSourceConsumer(
            self,
            grafana_uid=self.unique_name,
            grafana_base_url=self.external_url,
            relation_name="grafana-source",
        )

        # -- grafana_dashboard relation observations
        self.dashboard_consumer = GrafanaDashboardConsumer(self, "grafana-dashboard")


        # -- k8s resource patch
        self.resource_patch = KubernetesComputeResourcesPatch(
            self, GRAFANA_WORKLOAD, resource_reqs_func=self._resource_reqs_from_config
        )

        # oauth relation
        self.oauth = OAuthRequirer(self, self._oauth_client_config)
        self.catalog = CatalogueConsumer(charm=self, item=self._catalogue_item)
        self.grafana_auth_requirer = AuthRequirer(
            self,
            relation_name="grafana-auth",
            urls=[f"{self.app.name}:{WORKLOAD_PORT}"],
            refresh_event=self.on.grafana_pebble_ready,  # pyright: ignore
        )

        self._grafana_client = GrafanaClient(self.internal_url)
        self._grafana_config = GrafanaConfig(
                                            datasources_config=self._datasource_config,
                                            oauth_config = self._oauth_config,
                                            auth_env_config = lambda: self._auth_env_vars,
                                            db_config=lambda: self._db_config,
                                            enable_reporting = bool(self.config["reporting_enabled"]),
                                            enable_external_db=self._enable_external_db,
                                            tracing_endpoint=self._workload_tracing_endpoint,
                                            )
        self._grafana_service = Grafana(
                                        container=self.unit.get_container("grafana"),
                                        is_leader= self.unit.is_leader(),
                                        grafana_config_generator=self._grafana_config,
                                        pebble_env=self._pebble_env,
                                        tls_config = self._tls_config,
                                        trusted_ca_certs = self._trusted_ca_certs,
                                        dashboards = self.dashboard_consumer.dashboards,
                                        provision_own_dashboard = self._provision_own_dashboard,
                                        scheme=self._scheme,
                                        )
        self._litestream = Litestream(self.unit.get_container("litestream"),
                                      is_leader= self.unit.is_leader(),
                                        peers = self.peers)

        self.framework.observe(
            self.on.get_admin_password_action,  # pyright: ignore
            self._on_get_admin_password,
        )

        # FIXME: we still need to observe these events as they contain the required data
        # update the charm lib to work with the reconcile approach
        self.framework.observe(self.on[DATABASE_RELATION].relation_changed, self._on_database_changed)
        self.framework.observe(self.on[DATABASE_RELATION].relation_broken, self._on_database_broken)
        self.framework.observe(
            self.grafana_auth_requirer.on.auth_conf_available,  # pyright: ignore
            self._on_grafana_auth_conf_available,
        )

        # FIXME: we still need to call reconcile since the lib updates peer data on specific events
        # update the charm lib to work with the reconcile approach
        self.framework.observe(
            self.source_consumer.on.sources_changed,  # pyright: ignore
            self._on_grafana_source_changed,
        )
        self.framework.observe(
            self.source_consumer.on.sources_to_delete_changed,  # pyright: ignore
            self._on_grafana_source_changed,
        )

        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)

        all_events.add(TraefikRouteRequirerReadyEvent)
        observe_events(self, all_events, self._reconcile)


    @property
    def _scheme(self) -> str:
        return "https" if self._tls_available else "http"

    @property
    def internal_url(self) -> str:
        """Return workload's internal URL. Used for ingress."""
        return f"{self._scheme}://{self._fqdn}:{WORKLOAD_PORT}"

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
    def _metrics_scrape_jobs(self) -> list:
        parts = urlparse(self.internal_url)
        job = {"static_configs": [{"targets": [parts.netloc]}], "scheme": self._scheme}
        return [job]

    @property
    def _profiling_scrape_jobs(self) -> list:
        job = {"static_configs": [{"targets": [f"*:{PROFILING_PORT}"]}], "scheme": self._scheme}
        return [job]


    @property
    def _trusted_ca_certs(self) -> Optional[str]:
        if certs := self.trusted_cert_transfer.get_all_certificates():
            return "\n".join(certs)
        return None

    @property
    def unique_name(self):
        """Returns a unique identifier for this application."""
        return "juju_{}_{}_{}_{}".format(
            self.model.name,
            self.model.uuid,
            self.model.app.name,
            self.model.unit.name.split("/")[1],  # type: ignore
        )

    @property
    def _catalogue_item(self) -> CatalogueItem:
        api_endpoints = {
            "Search": "/api/search",
            "Data Sources": "/api/datasources",
        }

        return CatalogueItem(
            name="Grafana",
            icon="bar-chart",
            url=self.external_url,
            description=(
                "Grafana allows you to query, visualize, alert on, and "
                "visualize metrics from mixed datasources in configurable "
                "dashboards for observability."
            ),
            api_docs = "https://grafana.com/docs/grafana/latest/developers/http_api/",
            api_endpoints={key: f"{self.external_url}{path}" for key, path in api_endpoints.items()},
        )

    # TRACING PROPERTIES
    @property
    def _workload_tracing_endpoint(self) -> Optional[str]:
        if self.workload_tracing.is_ready():
            endpoint = self.workload_tracing.get_endpoint("otlp_grpc")
            return endpoint
        return None

    @property
    def _datasource_config(self) -> DatasourceConfig:
        return DatasourceConfig(
            datasources=lambda : self.source_consumer.sources,
            datasources_to_delete=lambda : self.source_consumer.sources_to_delete,
            query_timeout=int(self.model.config.get("datasource_query_timeout", 0)),
        )

    def _pebble_env(self) -> PebbleEnvironment:
        topology = self._topology
        tracing_resource_attrs = ((f"juju_application={topology.application},juju_model={topology.model}" + \
                                f",juju_model_uuid={topology.model_uuid},juju_unit={topology.unit},juju_charm={topology.charm_name}") \
                            if self._workload_tracing_endpoint
                            else None)
        return PebbleEnvironment(
            external_url=self.external_url,
            log_level=str(self.model.config["log_level"]),
            allow_embedding=bool(self.model.config["allow_embedding"]),
            allow_anonymous_access=bool(self.model.config["allow_anonymous_access"]),
            enable_auto_assign_org=bool(self.model.config["enable_auto_assign_org"]),
            enable_profiling=bool(self.model.relations.get("profiling-endpoint")),
            tracing_resource_attributes=tracing_resource_attrs,
            admin_password = self.admin_password,
            admin_user = str(self.model.config["admin_user"]),
        )

    @property
    def _provision_own_dashboard(self) -> bool:
        source_related_apps = [rel.app for rel in self.model.relations["grafana-source"]]
        scrape_related_apps = [rel.app for rel in self.model.relations["metrics-endpoint"]]

        return any(
            source for source in source_related_apps if source in scrape_related_apps
        )

    @property
    def _enable_external_db(self) -> bool:
        """Only consider a DB connection if we have config info."""
        rel = self.model.get_relation(DATABASE_RELATION)
        return len(rel.units) > 0 if rel is not None else False

    @property
    def _db_config(self) -> Optional[Dict[str, str]]:
        if self._enable_external_db:
            peer_data = self.peers.get_app_data("database")
            if not peer_data:
                return None
            return peer_data
        return None

    @property
    def _oauth_client_config(self) -> OauthClientConfig:
        return OauthClientConfig(
            os.path.join(self.external_url, "login/generic_oauth"),
            OAUTH_SCOPES,
            OAUTH_GRANT_TYPES,
        )

    @property
    def _oauth_config(self) -> Optional[OauthProviderConfig]:
        if self.oauth.is_client_created():
            return self.oauth.get_provider_info()
        return None

    @property
    def _auth_env_vars(self):
        return self.peers.get_app_data("auth_conf_env_vars")

    @property
    def _tls_config(self) -> Optional[TLSConfig]:
        certificates, key = self._cert_requirer.get_assigned_certificate(
            certificate_request=self._csr_attributes
        )
        if not (key and certificates):
            return None
        return TLSConfig(
            certificate=certificates.certificate.raw,
            ca=certificates.ca.raw,
            key=key.raw)

    @property
    def _tls_available(self) -> bool:
        return bool(self._tls_config)

    @property
    def admin_password(self) -> Optional[str]:
        """The admin password."""
        contents = self._secret_storage.contents
        if not contents:
            return None
        return contents.get('password')

    def _reconcile(self):
        """Unconditional control logic."""
        self._set_ports()
        self.unit.set_workload_version(self._grafana_service.grafana_version)
        if not self.resource_patch.is_ready():
            logger.debug("Resource patch not ready yet. Skipping cluster update step.")
            return
        self._reconcile_relations()
        self._grafana_service.reconcile()
        self._litestream.reconcile()
        self._reconcile_tls_config()


    def _reconcile_tls_config(self) -> None:
        """Update the TLS certificates for the charm container."""
        # push CA cert to charm container
        cacert_path = Path(CA_CERT_PATH)
        if tls_config := self._tls_config:
            cacert_path.parent.mkdir(parents=True, exist_ok=True)
            cacert_path.write_text(tls_config.ca)
        else:
            cacert_path.unlink(missing_ok=True)
        subprocess.run(["update-ca-certificates", "--fresh"])

    def _reconcile_relations(self):
        self._reconcile_ingress()
        self.metrics_endpoint.set_scrape_job_spec()
        self.source_consumer.upgrade_keys()
        self.dashboard_consumer.update_dashboards()
        self.oauth.update_client_config(client_config=self._oauth_client_config)
        self._reconcile_grafana_metadata()
        self.catalog.update_item(item=self._catalogue_item)

    def _reconcile_ingress(self):
        if not self.unit.is_leader():
            return
        if self.ingress.is_ready():
            self.ingress.submit_to_traefik(self._ingress_config)

    def _reconcile_grafana_metadata(self):
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

    def _on_collect_unit_status(self, e: CollectStatusEvent):
        e.add_status(ActiveStatus())
        e.add_status(self.resource_patch.get_status())


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
        self.peers.set_app_data("database", db_info)
        self._grafana_service.reconcile()

    def _on_database_broken(self, _: RelationBrokenEvent) -> None:
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
        self.peers.set_app_data("database", {})
        logger.info("Removing the grafana-k8s database backend config")
        # Cleanup the config file
        self._grafana_service.reconcile()

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

        if not self._grafana_client.is_ready:
            return event.fail(self.GetAdminPWDFailures.not_reachable)

        try:
            pw_changed = self._grafana_client.password_has_been_changed(
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
        if not self.peers.get_app_data("auth_conf_env_vars"):
            env_vars = self._generate_auth_env_vars(event.auth)  # type: ignore[attr-defined]
            if env_vars:
                self.peers.set_app_data("auth_conf_env_vars", env_vars)
                self._grafana_service.reconcile()

    def _on_grafana_source_changed(self, _) -> None:
        """When a grafana-source is added or modified, update the config."""
        self._grafana_service.reconcile()

    def _generate_auth_env_vars(self, conf: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
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

    def _set_ports(self):
        """Open necessary (and close no longer needed) workload ports."""
        planned_ports = {Port(protocol="tcp", port=WORKLOAD_PORT)} if self.unit.is_leader() else set()
        actual_ports = self.unit.opened_ports()

        # Ports may change across an upgrade, so need to sync
        ports_to_close = actual_ports.difference(planned_ports)
        for p in ports_to_close:
            self.unit.close_port(p.protocol, p.port)

        new_ports_to_open = planned_ports.difference(actual_ports)
        for p in new_ports_to_open:
            self.unit.open_port(p.protocol, p.port)

    def _resource_reqs_from_config(self) -> ResourceRequirements:
        limits = {"cpu": self.model.config.get("cpu"), "memory": self.model.config.get("memory")}
        requests = {"cpu": "0.25", "memory": "200Mi"}
        return adjust_resource_requirements(limits, requests, adhere_to_requests=True)

if __name__ == "__main__":
    main(GrafanaCharm, use_juju_for_storage=True)
