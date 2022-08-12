## Development environment

Initial setup (ensure microk8s is a clean slate with `microk8s.reset` or a fresh install with `snap install microk8s --classic`:
```bash
microk8s.enable dns storage
juju bootstrap microk8s mk8s
juju add-model lma
juju create-storage-pool operator-storage kubernetes storage-class=microk8s-hostpath
```

Deploy Grafana on its own:
```bash
git clone git@github.com:canonical/grafana-k8s.git
cd grafana-k8s
charmcraft pack
juju deploy ./grafana-k8s_ubuntu-20.04-amd64.charm --resource grafana-image=ubuntu/grafana:latest --resource litestream-image=docker.io/litestream/litestream:0.3.9
```

View the dashboard in a browser:
1. `juju status` to check the IP of the of the running Grafana application
2. Navigate to `http://IP_ADDRESS:3000`
3. Log in with the default credentials username=admin, password=admin.

Add Prometheus as a datasource. See the [contributing guide](https://github.com/canonical/prometheus-operator/blob/main/CONTRIBUTING.md)
for Prometheus to build and deploy, then:
```bash
juju add-relation grafana-k8s prometheus-k8s
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

```sh
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## Testing

The tests are run with `tox`; the following `tox` targets are available:

* `lint` runs the linting checks based on [`pflake8`](https://flake8.pycqa.org/en/latest/), [`isort`](https://pypi.org/project/isort/) and [`black`](https://github.com/psf/black), in order; the first to fail interrupts the `tox -e lint` run.
* `static` runs static checks with [`mypy`](http://mypy-lang.org/).
* `unit` runs the unit tests.

## Debugging
### Data sources
When data sources are related to grafana, they should appear in the
`datasources.yaml` file. This can be manually verified by ssh-ing into the
grafana container:

```shell
juju ssh --container grafana grafana/0
cat /etc/grafana/provisioning/datasources/datasources.yaml
```

or querying the
[grafana HTTP API](https://grafana.com/docs/grafana/latest/http_api/):
```shell
curl --user admin:password http://IP_ADDRESS:3000/api/datasources/
```
