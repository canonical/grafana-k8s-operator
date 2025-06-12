resource "juju_application" "grafana" {
  name               = var.app_name
  config             = var.config
  constraints        = var.constraints
  model              = var.model
  storage_directives = var.storage_directives
  trust              = true
  units              = var.units

  charm {
    name     = "grafana-k8s"
    channel  = var.channel
    revision = var.revision
  }
}