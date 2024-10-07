resource "juju_application" "grafana" {
  name = var.app_name
  # Coordinator and worker must be in the same model
  model = var.model_name
  trust = var.trust

  charm {
    name     = "grafana-k8s"
    channel  = var.channel
    revision = var.revision
  }
  units  = var.units
  config = var.config
}