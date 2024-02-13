# Grafana Operator for k8s Terraform Module

This folder contains a base [Terraform][Terraform] module for the grafana-k8s charm.

The module uses the [Terraform Juju provider][Terraform Juju provider] to model the charm
deployment onto any Kubernetes environment managed by [Juju][Juju].

The module can be used to deploy the Grafana to a Kubernetes cluster separately 
as well as a part of a higher level Terraform module, depending on the deployment architecture.

## Module structure

- **main.tf** - Defines the Juju application to be deployed.
- **variables.tf** - Allows customization of the deployment. Except for exposing the deployment
  options (Juju model name, channel or application name) also allows overwriting charm's default
  configuration.
- **output.tf** - Responsible for integrating the module with other Terraform modules, primarily
  by defining potential integration endpoints (charm integrations), but also by exposing
  the application name.
- **terraform.tf** - Defines the Terraform provider.

## Deploying grafana-k8s base module separately

### Pre-requisites

- A Kubernetes cluster
- Juju 3.x
- Juju controller bootstrapped onto the K8s cluster
- Terraform

### Deploying Grafana with Terraform

Clone the [grafana-k8s-operator][grafana-repo] Git repository.

From inside the `terraform` folder, initialize the provider:

```shell
terraform init
```

Create Terraform plan:

```shell
terraform plan
```

While creating the plan, the default configuration can be overwritten with `-var-file`. To do that,
Terraform `tfvars` file should be prepared prior to the plan creation.

Deploy UPF:

```console
terraform apply -auto-approve 
```

### Cleaning up

Destroy the deployment:

```shell
terraform destroy -auto-approve
```

## Using grafana-k8s base module in higher level modules

If you want to use `grafana-k8s` base module as part of your Terraform module, import it
like shown below:

```text
module "grafana" {
  source = "git::https://github.com/canonical/grafana-k8s-operator//terraform"
  
  model_name = "juju_model_name"
  config = Optional config map
}
```

Create integrations, for instance:

```text
resource "juju_integration" "metrics" {
  model = var.model_name
  application {
    name     = module.grafana.app_name
    endpoint = module.grafana.metrics_endpoint
  }
  application {
    name     = module.prometheus.app_name
    endpoint = module.prometheus.metrics_endpoint
  }
}
```

The complete list of available integrations can be found [here][grafana-integrations].

[Terraform]: https://www.terraform.io/
[Terraform Juju provider]: https://registry.terraform.io/providers/juju/juju/latest
[Juju]: https://juju.is
[grafana-repo]: https://github.com/canonical/grafana-k8s-operator
[grafana-integrations]: https://charmhub.io/grafana-k8s/integrations
