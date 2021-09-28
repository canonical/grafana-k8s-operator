# Grafana Charm

## Description

The Grafana Operator provides a data visualization solution using [Grafana](https://grafana.com/), an open-source
observability toolkit.

Grafana allows you to query, visualize, alert on, and visualize metrics from mixed datasources in configurable
dashboards for observability. This repository contains a [Juju](https://jaas.ai/) Charm for deploying the visualization
component of Grafana in a Kuberenetes cluster. 

The grafana-k8s charm provides an interface which can ingest data from a wide array of data sources, with Prometheus
as a common input, then presents that data on configurable dashboards.

## Usage

The Grafana Operator may be deployed using the Juju command line via:
```bash
juju deploy grafana-k8s
```

By default, Grafana does not contain any data sources or dashboards, but [Prometheus](https://charmhub.io/prometheus-k8s)
is commonly used, and is deployable with Juju. The Grafana Operator may also accept additional datasources over Juju
relations with charms which support the `grafana-datasource` interface.

For example:
```bash
juju deploy prometheus-k8s
juju relate prometheus-k8s grafana-k8s
```

The Grafana Operator includes a Charm library which may be used by other Charms to easily provide datasources with a
`add_source` method.

View the dashboard in a browser:
1. `juju status` to check the IP of the of the running Grafana application
2. Navigate to `http://IP_ADDRESS:3000`
3. Log in with the default credentials username=admin, password=admin (these credentials are configurable at deploy time)

## Web Interface

The Grafana dashboard may be accessed on port `3000` on the IP address of the Grafana unit.
This unit and its IP address can be retrieved using the `juju status` command.
Additionally, Grafana can be accessed via the Kubernetes service matching the Juju application name in the namespace matching the Juju model's name.

## High Availability Grafana

This charm is written to support a high-availability Grafana cluster, but a database relation is required (MySQL or Postgresql).

If HA is not required, there is no need to add a database relation.

> NOTE: HA should not be considered for production use.

## Relations

```
grafana_datasource - An input for grafana-k8s datasources
grafana_dashboard - an input for zlib compressed base64 encoded dashboard data
```

## OCI Images

This charm defaults to the latest version of the [ubuntu/grafana](https://hub.docker.com/r/ubuntu/grafana) image.

## Contributing

See the Juju SDK docs for guidelines on configuring a development environment and best practices for authoring.
