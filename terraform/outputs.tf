output "app_name" {
  value = juju_application.grafana.name
}

# Required integration endpoints

output "catalogue_endpoint" {
  description = "Name of the endpoint used by Garana for the Catalogue integration."
  value       = "catalogue"
}

output "certificates_endpoint" {
  description = "Name of the endpoint used to integrate with the TLS certificates provider."
  value       = "certificates"
}

output "database_endpoint" {
  value       = "database"
}

output "grafana_auth_endpoint" {
  description = "Name of the endpoint used by Grafana to obtain the authentication configuration data"
  value       = "grafana-auth"
}

output "grafana_dashboard_endpoint" {
  description = "Forwards the built-in Grafana dashboard(s) for monitoring applications."
  value       = "grafana-dashboard"
}

output "grafana_source_endpoint" {
  description = "Name of the endpoint used by apps to create a datasource in Grafana."
  value       = "grafana-source"
}

output "ingress_endpoint" {
  description = "Name of the endpoint used by Grafana for the ingress configuration."
  value       = "ingress"
}

output "oauth_endpoint" {
  description = "Name of the endpoint for interfacing with an OAuth2/OIDC Provider."
  value       = "oauth"
}

output "receive_ca_cert_endpoint" {
  value       = "receive-ca-cert"
}

output "tracing_endpoint" {
  description = "Name of the endpoint used by Grafana for pushing traces to a tracing endpoint provided by Tempo."
  value       = "tracing"
}

# Provided integration endpoints

output "metrics_endpoint" {
  description = "Name of the endpoint used by Prometheus to get metrics from client applications."
  value       = "metrics-endpoint"
}
