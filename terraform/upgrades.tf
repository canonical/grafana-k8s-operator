# -------------- Upgrade logic --------------

## -------- Removed the litestream-image resource ----------
# https://github.com/juju/juju/issues/21648
# https://github.com/juju/juju/issues/22071
resource "terraform_data" "grafana_resources" {
  input = data.juju_charm.grafana_info.resources
}

# -------------- # CharmHub API -------------- #

data "juju_charm" "grafana_info" {
  charm   = "grafana-k8s"
  channel = var.channel
  base    = var.base
}
