# Grafana Charm

## Description

The Grafana Operator provides a data visualization solution using [Grafana](https://grafana.com/), an open-source
observability toolkit.

Grafana allows you to query, visualize, alert on, and visualize metrics from mixed datasources in configurable
dashboards for observability. This repository contains a [Juju](https://juju.is/) Charm for deploying the visualization component of Grafana in a Kubernetes cluster.

The grafana-k8s charm provides an interface which can ingest data from a wide array of data sources, with Prometheus as a common input, then presents that data on configurable dashboards. It is the primary user-facing entrypoint for the Canonical Observability Stack Lite. See the [COS Lite Bundle](https://charmhub.io/cos-lite) for more information.

## Usage

The Grafana Operator may be deployed on a Kubernetes Juju model using the command line via:
```bash
juju deploy grafana-k8s
```

At install time, Grafana does not contain any data sources or dashboards, but [Prometheus](https://charmhub.io/prometheus-k8s) is commonly used, and is deployable with Juju. The Grafana Operator may also accept additional datasources over Juju relations with charms which support the `grafana-datasource` interface, such as [Loki](https://charmhub.io/loki-k8s) log visualization.

For example:
```bash
juju deploy prometheus-k8s
juju relate prometheus-k8s grafana-k8s
```

The Grafana Operator includes a Charm library which may be used by other Charms to easily provide datasources. Currently, Prometheus and Loki are tested, with datasource integration built into those charms, but any Grafana datasource which does not require the addition of a plugin should be supported. See the documentation for the `charms.grafana_k8s.v0.grafana_source` to learn more.

## Web Interface

The Grafana dashboard may be accessed on port `3000` on the IP address of the Grafana unit.
This unit and its IP address can be retrieved using the `juju status` command.

The default password is randomized at first install, and can be retrieved with:
```bash
juju run-action grafana-k8s/0 get-admin-password --wait
```

View the dashboard in a browser:
1. `juju status` to check the IP of the running Grafana application
2. Navigate to `http://IP_ADDRESS:3000`
3. Log in with the username `admin`, and the password you got from the `get-admin-password` action.

To manually set the admin password, see the
[official docs](https://grafana.com/docs/grafana/latest/administration/cli/#reset-admin-password).

Additionally, Grafana can be accessed via the Kubernetes service matching the Juju application name in the namespace matching the Juju model's name.

## Integration with other charms/adding external dashboards

The grafana-k8s charm does not support directly relating to Reactive charms over the `dashboards` interface, and it does not support adding dashboards via an action similar to the [Reactive Grafana Charm](https://charmhub.io/grafana) as a design goal. For scenarios where Reactive charms which provide dashboards should be integrated, the [COS Proxy](https://charmhub.io/cos-proxy) charm can be deployed in a Reactive model, and related to grafana-k8s to provide a migration path.

Dashboards which are not bundled as part of a charm can be added to grafana-k8s with the [COS Config Charm](https://charmhub.io/cos-configuration-k8s), which can keep a git repository holding your infrastructure-as-code configuration. See the `COS Config` documentation for more information.

## To Bundle Dashboards As Part of Your Charm

See the documentation for the [`charm.grafana_k8s.v0.grafana_dashboard`](https://charmhub.io/grafana-k8s/libraries/grafana_dashboard) library. Generally, this only requires adding a `grafana-dashboard` interface to your charm and putting the dashboard templates into a configurable path.

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
