# -------------- Upgrade logic --------------

## -------- grafana.revision >= 174 ----------
# the ingress endpoint interface changes from traefik_route to ingress_per_app so we need a
# lifecycle to trigger integration replacement, otherwise the upgrade will fail
resource "terraform_data" "grafana_resources" {
  input = data.juju_charm.grafana_info.resources
}

# -------------- # CharmHub API -------------- #

data "juju_charm" "grafana_info" {
  charm   = "grafana-k8s"
  channel = var.channel
  base    = var.base
}
