# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.grafana.name
}

# Required integration endpoints

output "grafana_source_endpoint" {
  description = "Name of the endpoint used by Grafana for accepting data source configurations sent by client applications."
  value       = "grafana-source"
}

output "grafana_dashboard_endpoint" {
  description = "Name of the endpoint used by Grafana for handling dashboards sent by client applications."
  value       = "grafana-dashboard"
}

output "grafana_auth_endpoint" {
  description = "Name of the endpoint used by Grafana for allowing client applications to configure authentication to Grafana."
  value       = "grafana-auth"
}

output "database_endpoint" {
  description = "Name of the endpoint used to integrate with the database."
  value       = "database"
}

output "catalogue_endpoint" {
  description = "Name of the endpoint used by Grafana for the Catalogue integration."
  value       = "catalogue"
}

output "ingress_endpoint" {
  description = "Name of the endpoint used by Grafana for the ingress configuration."
  value       = "ingress"
}

output "certificates_endpoint" {
  description = "Name of the endpoint used to integrate with the TLS certificates provider."
  value       = "certificates"
}

output "receive_ca_cert_endpoint" {
  description = "Name of the endpoint used with a local CA to obtain the CA cert that was used to sign proxied endpoints."
  value       = "receive-ca-cert"
}

output "oauth_endpoint" {
  description = "Name of the endpoint used to integrate Grafana with an oAuth2/OIDC Provider."
  value       = "oauth"
}

output "tracing_endpoint" {
  description = "Name of the endpoint used by Grafana for pushing traces to a tracing endpoint provided by Tempo."
  value       = "tracing"
}

# Provided integration endpoints

output "metrics_endpoint" {
  description = "Exposes the Prometheus metrics endpoint providing telemetry about the Grafana instance."
  value       = "metrics-endpoint"
}
