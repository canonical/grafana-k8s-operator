output "app_name" {
  value = juju_application.grafana.name
}

output "requires" {
  value = {
    catalogue         = "catalogue",
    certificates      = "certificates",
    database          = "database",
    grafana_auth      = "grafana-auth",
    grafana_dashboard = "grafana-dashboard",
    grafana_source    = "grafana-source",
    ingress           = "ingress",
    oauth             = "oauth",
    receive_ca_cert   = "receive-ca-cert",
    tracing           = "tracing",
  }
}

output "provides" {
  value = {
    metrics_endpoint = "metrics-endpoint",
  }
}
