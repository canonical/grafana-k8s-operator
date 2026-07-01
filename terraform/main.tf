resource "juju_application" "grafana" {
  name               = var.app_name
  config             = var.config
  constraints        = var.constraints
  model_uuid         = var.model_uuid
  resources          = var.resources
  storage_directives = var.storage_directives
  trust              = true
  units              = var.units

  charm {
    base     = var.base
    name     = "grafana-k8s"
    channel  = var.channel
    revision = var.revision
  }

  lifecycle { replace_triggered_by = [terraform_data.replace_triggers] }
}
