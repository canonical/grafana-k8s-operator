# Grafana Charm

## Description

This is the Grafana charm for Kubernetes using the Operator Framework.

## Usage

Initial setup (ensure microk8s is a clean slate with `microk8s.reset` or a fresh install with `snap install microk8s --classic`:
```bash
microk8s.enable dns storage registry dashboard
juju bootstrap microk8s mk8s
juju add-model lma
juju create-storage-pool operator-storage kubernetes storage-class=microk8s-hostpath
```

Deploy Grafana on its own:
```bash
git clone git@github.com:canonical/grafana-operator.git
cd grafana-operator
charmcraft build
juju deploy ./grafana.charm --resource grafana-image=grafana/grafana:7.2.1
```

View the dashboard in a browser:
1. `juju status` to check the IP of the of the running Grafana application
2. Navigate to `http://IP_ADDRESS:3000`
3. Log in with the default credentials username=admin, password=admin.

Add Prometheus as a datasource:
```bash
git clone git@github.com:canonical/prometheus-operator.git
cd prometheus-operator
charmcraft build
juju deploy ./prometheus.charm
juju add-relation grafana prometheus
watch -c juju status --color  # wait for things to settle down
```
> Once the deployed charm and relation settles, you should be able to see Prometheus data propagating to the Grafana dashboard.

### High Availability Grafana

This charm is written to support a high-availability Grafana cluster, but a database relation is required (MySQL or Postgresql).

If HA is not required, there is no need to add a database relation.

> NOTE: HA should not be considered for production use.

...

## Developing

Create and activate a virtualenv,
and install the development requirements,

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt

## Testing

Just run `run_tests`:

    ./run_tests
