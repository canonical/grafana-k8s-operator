# Grafana Charm

## Description

This is the Grafana K8S charm for Kubernetes using the Operator Framework.

Grafana allows you to query, visualize, alert on, and visualize metrics from mixed datasources in configurable
dashboards for observability.

The grafana-k8s charm provides an interface which can ingest data from a wide array of data sources, with Prometheus
as a common input, then presents that data on configurable dashboards.

## Deployment

Initial setup (ensure microk8s is a clean slate with `microk8s.reset` or a fresh install with `snap install microk8s --classic`:
```bash
juju deploy ./grafana-k8s.charm --resource grafana-image=grafana/grafana:7.2.1
```

View the dashboard in a browser:
1. `juju status` to check the IP of the of the running Grafana application
2. Navigate to `http://IP_ADDRESS:3000`
3. Log in with the default credentials username=admin, password=admin.

Add Prometheus as a datasource:
```bash
juju deploy prometheus-k8s
juju add-relation grafana prometheus
watch -c juju status --color  # wait for things to settle down
```
> Once the deployed charm and relation settles, you should be able to see Prometheus data propagating to the Grafana dashboard.

### High Availability Grafana

This charm is written to support a high-availability Grafana cluster, but a database relation is required (MySQL or Postgresql).

If HA is not required, there is no need to add a database relation.

> NOTE: HA should not be considered for production use.

...

## Provides Relations

```
grafana-source - An input for grafana-k8s datasources
grafana-dash - an input for base64 encoded dashboard data
```
