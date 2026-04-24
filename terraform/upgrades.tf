# -------------- Upgrade logic --------------

## -------- Removed the litestream-image resource ----------
# The litestream-image resource was removed and given a Juju bug, we need to add a lifecycle to
# trigger integration replacement, otherwise the upgrade will fail
# https://github.com/juju/juju/issues/21648
# https://github.com/juju/juju/issues/22071
resource "terraform_data" "grafana_litestream_resource" {
  triggers_replace = contains(keys(data.juju_charm.grafana_info.resources), "litestream-image")
}

# -------------- # CharmHub API -------------- #

data "juju_charm" "grafana_info" {
  charm   = "grafana-k8s"
  channel = var.channel
  base    = var.base
}
