# Changelog

Changes on `track/12.4` since the common ancestor with `track/2` (`c5bf263`).

## Breaking Changes

- fix!: rework data sources to be stable ([#571](https://github.com/canonical/grafana-k8s-operator/pull/571))
- feat!: long DB name ([#543](https://github.com/canonical/grafana-k8s-operator/pull/543))

## Features

- feat(tf): base input variable ([#573](https://github.com/canonical/grafana-k8s-operator/pull/573)) (#575)
- feat: add charms blueprint ([#572](https://github.com/canonical/grafana-k8s-operator/pull/572))
- feat: support Juju secrets for sensitive custom config fields ([#567](https://github.com/canonical/grafana-k8s-operator/pull/567))
- feat: bump to 26.04 ([#560](https://github.com/canonical/grafana-k8s-operator/pull/560))
- feat(terraform): Support for Juju provider v2 ([#551](https://github.com/canonical/grafana-k8s-operator/pull/551))
- feat: TF resources variable ([#548](https://github.com/canonical/grafana-k8s-operator/pull/548))
- feat: TF service mesh outputs ([#547](https://github.com/canonical/grafana-k8s-operator/pull/547))
- feat: add send-logs integration via LogForwarder ([#539](https://github.com/canonical/grafana-k8s-operator/pull/539))
- feat: migrate charm-tracing to ops[tracing] ([#540](https://github.com/canonical/grafana-k8s-operator/pull/540))
- feat: User-defined TF replace_triggered_by ([#536](https://github.com/canonical/grafana-k8s-operator/pull/536))
- feat(terraform): add channel validation ([#532](https://github.com/canonical/grafana-k8s-operator/pull/532))
- feat: add Grafana 12.4.2 ([#525](https://github.com/canonical/grafana-k8s-operator/pull/525))
- feat: Manually trigger release CI ([#516](https://github.com/canonical/grafana-k8s-operator/pull/516))
- feat(config): add charm config option for custom grafana config ([#499](https://github.com/canonical/grafana-k8s-operator/pull/499))
- feat: change default track to 'dev' in release workflow ([e69670f](https://github.com/canonical/grafana-k8s-operator/commit/e69670f55d1550aed36f2a6e795b18fd13ac5cfa))

## Fixes

- fix: validate for correct track name ([#576](https://github.com/canonical/grafana-k8s-operator/pull/576))
- fix(lib): only update dashboard databag when templates change ([#570](https://github.com/canonical/grafana-k8s-operator/pull/570))
- fix: disable all analytics features in the config when requested ([#565](https://github.com/canonical/grafana-k8s-operator/pull/565))
- fix: uncaught `FileNotFoundError` in `grafana_version()` during pod termination ([#531](https://github.com/canonical/grafana-k8s-operator/pull/531))
- fix: TF module pgsql output ([#558](https://github.com/canonical/grafana-k8s-operator/pull/558))
- fix: Make unit-unavailable alert less noisy ([#555](https://github.com/canonical/grafana-k8s-operator/pull/555))
- fix: update docs link ([#553](https://github.com/canonical/grafana-k8s-operator/pull/553))
- fix: Update Grafana description in Catalogue ([#541](https://github.com/canonical/grafana-k8s-operator/pull/541))
- fix: Split TF endpoints output to requires/provides ([#515](https://github.com/canonical/grafana-k8s-operator/pull/515))
- fix: inclusive namecheck ([#526](https://github.com/canonical/grafana-k8s-operator/pull/526))
- fix: load dashboards recursively ([#522](https://github.com/canonical/grafana-k8s-operator/pull/522))
- fix: only inject dropdowns if they are not already in provider's temp… ([#505](https://github.com/canonical/grafana-k8s-operator/pull/505))

## Others

- chore: update terraform-docs ([1f903be](https://github.com/canonical/grafana-k8s-operator/commit/1f903be9db527e39e8132e13952d214fec9f2f2f))
- chore(blueprints): refresh charms.just ([52e8c61](https://github.com/canonical/grafana-k8s-operator/commit/52e8c61954ad4801526ed72920d9373c041c9074))
- chore: refresh charms.just from canonical/observability ([23b8626](https://github.com/canonical/grafana-k8s-operator/commit/23b86263aa9ec76df92ccc5dc7ab39989dd1ea3f))
- chore: update charm libraries ([#561](https://github.com/canonical/grafana-k8s-operator/pull/561))
- chore: update charm libraries ([#559](https://github.com/canonical/grafana-k8s-operator/pull/559))
- chore: update charm libraries ([#552](https://github.com/canonical/grafana-k8s-operator/pull/552))
- ci: fix token permissions for release workflow ([#550](https://github.com/canonical/grafana-k8s-operator/pull/550))
- ci: add explicit workflow permissions for CodeQL ([#549](https://github.com/canonical/grafana-k8s-operator/pull/549))
- chore: update charm libraries ([#544](https://github.com/canonical/grafana-k8s-operator/pull/544))
- chore(ci): bump reusable workflows to v2 ([#538](https://github.com/canonical/grafana-k8s-operator/pull/538))
- chore: update charm libraries ([#527](https://github.com/canonical/grafana-k8s-operator/pull/527))
- docs: improve charmcraft.yaml description field ([#529](https://github.com/canonical/grafana-k8s-operator/pull/529))
- chore: add .wokeignore ([94d9d12](https://github.com/canonical/grafana-k8s-operator/commit/94d9d12fd20ecba2a24253deeb7b1b8355b9768c))
- update prometheus_scrape lib ([#523](https://github.com/canonical/grafana-k8s-operator/pull/523))
- chore: update charm libraries ([#512](https://github.com/canonical/grafana-k8s-operator/pull/512))
- add role_attribute_path ([#502](https://github.com/canonical/grafana-k8s-operator/pull/502))
- OBC-1398 Provision only the latest version per dashboard UID ([#484](https://github.com/canonical/grafana-k8s-operator/pull/484))
- chore: update charm libraries ([#482](https://github.com/canonical/grafana-k8s-operator/pull/482))
- Service Mesh Support ([#489](https://github.com/canonical/grafana-k8s-operator/pull/489))
- 1/3 - Proper HA support with mysql/postgres ([#463](https://github.com/canonical/grafana-k8s-operator/pull/463))
- chore: update charm libraries ([#477](https://github.com/canonical/grafana-k8s-operator/pull/477))

