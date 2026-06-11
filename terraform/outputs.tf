output "app_name" {
  value = juju_application.grafana.name
}

output "provides" {
  value = {
    metrics_endpoint = "metrics-endpoint",
    provide_cmr_mesh = "provide-cmr-mesh",
  }
}

output "requires" {
  value = {
    catalogue         = "catalogue",
    certificates      = "certificates",
    charm_tracing     = "charm-tracing",
    pgsql             = "pgsql",
    grafana_auth      = "grafana-auth",
    grafana_dashboard = "grafana-dashboard",
    grafana_source    = "grafana-source",
    ingress           = "ingress",
    logging           = "logging",
    oauth             = "oauth",
    receive_ca_cert   = "receive-ca-cert",
    require_cmr_mesh  = "require-cmr-mesh",
    service_mesh      = "service-mesh",
  }
}
