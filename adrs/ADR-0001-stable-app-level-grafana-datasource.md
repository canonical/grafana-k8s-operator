# ADR-0001: Stable application-level Grafana datasource for HA providers

- **Status:** Accepted — Implemented (library + this repo); coordinated provider rollout pending
- **Date:** 2026-06-26
- **Issue:** [canonical/mimir-operators#49](https://github.com/canonical/mimir-operators/issues/49) —
  "Mimir datasource in Grafana keeps changing ID, breaking all alerts and dashboards
  defined in Grafana that use the Mimir datasource."
- **Component:** `grafana-k8s` charm and the shared `grafana_source` charm library
- **Library version:** `grafana_k8s` `grafana_source` `LIBAPI` 0 → **1** (`LIBPATCH` reset to 0)

---

## 1. Context and problem statement

`grafana-k8s` is a Kubernetes Juju charm (Canonical Observability Stack). Datasource
providers (Mimir, Loki, Tempo, Alertmanager, Prometheus) integrate with it over the
`grafana-source` relation using a **shared, vendored** library
(`charms.grafana_k8s.*.grafana_source`), so the behaviour described here is identical
across every COS datasource provider.

In the (pre-fix) v0 library, the datasource UID/name is constructed by the consumer in
`GrafanaSourceConsumer._get_source_config()`:

```python
unique_source_name = "juju_{}_{}_{}_{}".format(
    source_data["model"],
    source_data["model_uuid"],
    source_data["application"],
    unit_name.split("/")[1],   # <-- trailing unit number
)
```

In an HA deployment behind an ingress (gated by the old `is_ingress_per_app=True`
constructor arg), only the **leader** unit publishes a datasource address; non-leader
units publish an empty string. The consumer mints one datasource per advertising unit,
**keyed by unit number**.

When Juju re-elects the leader (e.g. `mimir/0` → `mimir/1`), the advertising unit
changes, the unit number embedded in the UID changes, and Grafana treats it as a
brand-new datasource. Every manually-created dashboard or alert referencing the old UID
silently breaks.

**Root cause:** the interface only ever expresses addresses **per-unit, in unit
databags**, and the consumer mints **one datasource per unit, keyed by unit number**.
There is no way to express *"one logical, load-balanced datasource for the whole
application"* — exactly what an HA coordinator (N units behind a single load-balanced
address) requires.

### Reproduction (from the issue)

Deploy COS via Terraform with 3 Mimir coordinator units (+ an S3-compatible store such
as seaweedfs); force a Mimir leadership change; observe the Mimir datasource in Grafana
get a new UID (effectively duplicated), while manually-created dashboards keep pointing
at the old, now-orphaned UID.

---

## 2. Decision drivers

- The datasource UID for an HA, load-balanced backend must be **stable across leader
  re-elections**.
- Per-unit datasources must remain possible — they are **semantically correct** for
  non-clustered backends (e.g. a standalone Prometheus where each unit is its own scrape
  target).
- The fix lives in a **shared library**; it must be backward-compatible at the wire
  level and rolled out in a coordinated way across COS.
- Avoid reintroducing a single point of failure.

---

## 3. Considered options

### Option A — Additive interface change (chosen)

Extend the `grafana-source` interface so a provider can publish **one logical,
load-balanced address in the application databag**, which the consumer turns into a
single datasource with a **unit-number-free, leader-election-stable UID**
(`juju_{model}_{model_uuid}_{application}`). Per-unit datasources are retained; the
provider chooses the topology.

### Option B — Pin a single advertising unit (rejected)

Always elect the same unit (e.g. `unit/0`) to advertise, keeping the UID stable across
leader changes with a provider-only change. **Rejected:** it ties the entire datasource
to the health of a single, non-load-balanced unit — reintroducing a single point of
failure and undermining the HA guarantee the deployment is trying to achieve.

---

## 4. Decision outcome

**Chosen: Option A.** It correctly represents the HA topology (one stable, load-balanced
datasource per application), preserves the per-unit model for non-clustered providers,
and is backward-compatible: app-level data is *additive* on top of the existing unit
data, so an old Grafana simply ignores the new field.

The provider explicitly chooses its datasource topology via two independent flags; the
consumer performs **no decision logic** — it ingests whatever data is present.

### Resulting per-charm classification (coordinated rollout)

| Charm        | Mode | Flags                                          | Ingress | URL fed to provider                          |
|--------------|------|------------------------------------------------|---------|----------------------------------------------|
| Mimir        | app  | `app_datasource=True, unit_datasources=False`  | IPA     | app ingress URL → `app_datasource_url`       |
| Loki         | app  | same                                           | IPA     | app ingress URL                              |
| Tempo        | app  | same                                           | IPA     | app ingress URL                              |
| Alertmanager | app  | same                                           | IPA     | app ingress URL                              |
| Prometheus   | unit | `app_datasource=False, unit_datasources=True`  | **IPU** | each unit's IPU URL → `unit_datasource_url`  |

IPA = ingress-per-app, IPU = ingress-per-unit.

---

## 5. Detailed design decisions

The following decisions are settled and were implemented as described.

1. **App-level address value.** Use the explicit URL if provided (`app_datasource_url`,
   typically the ingress URL), else fall back to the Kubernetes service DNS name
   `http://{app}.{model}.svc.cluster.local:{source_port}`. Do **not** use
   `socket.getfqdn()` for the app path — it returns the *pod* FQDN, which is
   unit-specific and wrong for an app-level address.

2. **New app databag field.** `grafana_source_app_host` (distinct from the unit-level
   `grafana_source_host`, so it is unambiguous in `juju show-unit`).

3. **Coexistence.** Unit data and app data may both be written. Unit-databag behaviour
   is unchanged. The app field is purely additive. Keeping unit data is not only for
   backward compatibility — it is the correct representation for per-unit providers.

4. **Additive consumer ingest.** The consumer creates a datasource for **every** source
   it finds — per-unit entries from unit data, plus one app-level entry if
   `grafana_source_app_host` is present:
   - app mode (writes app data only) → exactly 1 stable datasource;
   - unit mode (writes unit data only) → N per-unit datasources;
   - both → 1 app + N unit datasources (tolerated; see decision 9).

5. **Provider constructor API (BREAKING).** Replace `is_ingress_per_app` and
   `source_url` with two independent booleans and two URL overrides:
   - `app_datasource: bool = True`
   - `unit_datasources: bool = False`
   - `app_datasource_url: Optional[str] = None`
   - `unit_datasource_url: Optional[str] = None`
   - retain `source_port` (shared by both fallback URL constructions).

   Rationale: decouples datasource *topology* (one logical source vs per-unit sources)
   from the *reason* (ingress); the library should not know about ingress at all. The
   singular/plural naming encodes cardinality (`app_datasource` → one,
   `unit_datasources` → one-per-unit). `unit_datasource_url` is naturally *per-unit*
   because the provider runs as a separate instance in each unit and writes
   `relation.data[self._charm.unit]` — which maps cleanly onto ingress-per-unit.

6. **UID formats.**
   - App-level: `juju_{model}_{model_uuid}_{application}` (**no** unit number).
   - Per-unit: `juju_{model}_{model_uuid}_{application}_{unit_number}` (unchanged, so
     existing per-unit dashboards are not disturbed).

7. **Publish-back to provider.** Keep the existing unit-keyed `datasource_uids` JSON
   map; **add** a bare string field `app_datasource_uid` in the consumer's app databag.
   `GrafanaSourceData` gains `app_datasource_uid: Optional[str]` and a `get_app_uid()`
   accessor; `get_unit_uid()` stays.

8. **Migration / cleanup.** No new cleanup code in the relation-changed path: the
   existing `_sources_to_delete` diff compares old vs new `source_name` lists per
   relation, so when a provider switches unit→app, the stale `juju_..._{n}` lands in
   `deleteDatasources` automatically. (See decision 14 for the one place this did need a
   guard.)

9. **Edge cases.**
   - Both flags `True`: tolerated (1 app + N unit). Not forbidden.
   - Both flags `False`: log a `warning` and publish nothing. Do **not** raise — a
     questionable-but-harmless config must not crash the charm.
   - Default flip: defaults are `app_datasource=True, unit_datasources=False`, so the
     four app-mode charms need no explicit args; Prometheus must explicitly set
     `app_datasource=False, unit_datasources=True`.

10. **Versioning (BREAKING → bump LIBAPI).** Bump `LIBAPI` 0 → 1, reset `LIBPATCH` → 0.
    Add the new lib at `lib/charms/grafana_k8s/v1/grafana_source.py`; update imports to
    `charms.grafana_k8s.v1.grafana_source`. Leave `v0` in tree for legacy consumers
    until they migrate. **Hard-remove** `source_url` and `is_ingress_per_app` (no
    deprecation shim) — the LIBAPI bump + release notes signal the break in a
    coordinated, internally-controlled ecosystem.

11. **Mimir `/prometheus` suffix.** The `/prometheus` suffix applied for
    `source_type == "mimir"` must apply to **both** the unit and app URLs. The
    URL-building (scheme sanitization + `mimir` suffix) is factored into a single shared
    helper `_build_url(...)` used by both write paths.

12. **Ingress-mode pairing (charm-author guidance, not library logic).**
    - `app_datasource=True` ↔ ingress-per-app; feed the single app URL to
      `app_datasource_url`.
    - `unit_datasources=True` ↔ ingress-per-unit; feed each unit's own URL to
      `unit_datasource_url`.

    The library never talks to the ingress library; it only receives the URL. Documented
    in the `GrafanaSourceProvider` docstring; enforced in each rollout PR.

13. **`update_source` replacement (decided during build).** The old public
    `update_source(source_url="")` is replaced by **two** methods (clearer than one
    method with two args when both modes are active):
    - `update_app_source(app_datasource_url="")`
    - `update_unit_source(unit_datasource_url="")`

    Both re-publish to all relations, preserving the async-ingress workflow (the URL
    arrives after construction, via an ingress-ready event).

14. **Relation-departed guard for app-level sources (decided during build).** The
    separate deletion path `_remove_source_from_datastore` (triggered when a *provider
    unit* departs) assumed every stored source has a real `unit` and indexed `[0]` on the
    match. App-level sources have `unit=None`, so a unit departure in app mode would
    raise `IndexError`. The path was hardened to: (a) skip per-unit removal when no unit
    source matches the departing unit; (b) preserve the app-level source across
    individual unit departures (removed only on full relation-broken); (c) re-publish
    `app_datasource_uid` consistently.

---

## 6. Implementation (as built)

All library work is in `lib/charms/grafana_k8s/v1/grafana_source.py`.

- **`GrafanaSourceProvider`:** new constructor flags/URLs per decision 5; shared
  `_build_url` helper (decision 11); leader writes `grafana_source_app_host` to the app
  databag (folded into the leader-guarded write path and refreshed on `refresh_event`
  and relation events); per-unit write gated by `unit_datasources`; both-False warning;
  `update_app_source` / `update_unit_source` (decision 13).
- **`GrafanaSourceData`:** added `app_datasource_uid` + `get_app_uid()`;
  `get_source_data()` reads the new field.
- **`GrafanaSourceConsumer`:** `_get_source_config()` appends one app-level source when
  `grafana_source_app_host` is present (UID without unit number);
  `_publish_source_uids()` publishes `app_datasource_uid`; relation-departed guard
  (decision 14).
- **`src/charm.py`:** import switched to `charms.grafana_k8s.v1.grafana_source`.
- **`src/grafana_config.py`:** unchanged — app-level sources flow through the generic
  `source_name`/`url`/`source_type` templating.

### Out of scope (intentionally not done here)

- Switching *all* `socket.getfqdn()` usages across the charm (other relations, certs,
  advertised endpoints) to load-balanced addresses — larger per-charm HA work.
- The actual per-charm rollout PRs (Mimir/Loki/Tempo/Alertmanager/Prometheus) —
  coordinated follow-ups in their respective repos. Prometheus specifically must wire
  `IngressPerUnitRequirer` and feed each unit's IPU URL to `unit_datasource_url`; the
  four app-mode charms keep `IngressPerApp` and feed the app URL to `app_datasource_url`.

---

## 7. Consequences

### Positive

- HA, load-balanced backends get a single, stable datasource whose UID survives leader
  re-elections — directly fixing the reported breakage.
- Per-unit providers keep their correct, unchanged representation.
- One shared-library fix benefits Mimir, Loki, Tempo, Alertmanager (and leaves
  Prometheus's per-unit behaviour intact).

### Negative / costs

- **Breaking library API** (`LIBAPI` 0 → 1): provider charms must update their
  instantiation and re-`fetch-lib`. Coordinated rollout required.
- **One-time UID change on upgrade.** When Grafana and a switching (app-mode) provider
  are upgraded together, that datasource's UID changes **once**
  (`juju_..._{n}` → `juju_..._{app}`), breaking dashboards/alerts that reference the old
  UID a single time; users must re-point them. This is a single, deliberate break, not a
  recurring one.

### Backward compatibility

| provider ↓ / consumer → | old Grafana (unit only)            | new Grafana (unit + app)        |
|-------------------------|------------------------------------|---------------------------------|
| old provider (unit only)| as today (fragile post-leader)     | as today (fragile post-leader)  |
| new provider (app data) | app field ignored; as today        | **stable HA datasource**        |

If a provider is upgraded but Grafana is not, the new app-databag field is simply
ignored and previous behaviour continues (no regression).

---

## 8. Validation

### Unit / scenario tests (this repo)

`tests/unit/test_source_provider.py`, `test_source_consumer.py`, `test_datasources.py`,
and `test_source_matrix.py` assert:

- (a) app data only → exactly 1 app-level datasource, UID without unit number;
- (b) unit data only → N per-unit datasources, UIDs with unit numbers;
- (c) both → N+1 datasources;
- (d) unit→app transition → old `juju_..._0` lands in `deleteDatasources`;
- (e) `app_datasource_uid` is published back to the provider;
- (f) UID invariant across a simulated leader re-election (the core bug);
- (g) ingress/TLS only change the URL string, never the count or UID.

`tests/unit/test_source_matrix.py` parametrizes the full 16-cell matrix
(2 ingress × 2 TLS × 2 scale × 2 mode) deterministically. These run under
`tox -e unit`, with `tox -e lint` and `tox -e static` covering style and types.

### Integration tests (this repo)

`tests/integration/test_grafana_source.py` drives the same 16-cell matrix against real
Juju + Kubernetes + Grafana, using the `grafana-tester` charm (wired with the v1 lib,
`app_datasource`/`unit_datasources` config, and both ingress-per-app and
ingress-per-unit requirers). Per cell it deploys a uniquely-named tester in the right
mode/scale, optionally wires ingress (IPA for app, IPU for unit) and TLS, then asserts
datasource count, UID shape, URL scheme, and — for app mode at scale 2 — UID stability
across a **forced leader re-election** (achieved on Kubernetes by deleting the leader
pod via `kubectl`, which requires a cluster-reachable test environment).

#### Matrix (count and UID shape depend only on `(mode, scale)`; ingress/TLS only change the URL)

| #  | Ingress | TLS | Scale | Mode | Sources | UID(s)        | URL source             | Assertion                                     |
|----|---------|-----|-------|------|---------|---------------|------------------------|-----------------------------------------------|
| 1  | no      | no  | 1     | app  | 1       | `juju_M_U_A`  | `http://A.M.svc…:port` | exactly 1 datasource                          |
| 2  | no      | no  | 2     | app  | 1       | `juju_M_U_A`  | svc DNS                | exactly 1, stable                             |
| 3  | no      | yes | 1     | app  | 1       | `juju_M_U_A`  | `https://A.M.svc…`     | exactly 1 datasource                          |
| 4  | no      | yes | 2     | app  | 1       | `juju_M_U_A`  | svc DNS (https)        | exactly 1, stable                             |
| 5  | yes     | no  | 1     | app  | 1       | `juju_M_U_A`  | ingress URL (http)     | exactly 1 datasource                          |
| 6  | yes     | no  | 2     | app  | 1       | `juju_M_U_A`  | ingress URL            | exactly 1, stable                             |
| 7  | yes     | yes | 1     | app  | 1       | `juju_M_U_A`  | ingress URL (https)    | exactly 1 datasource                          |
| 8  | yes     | yes | 2     | app  | 1       | `juju_M_U_A`  | ingress URL (https)    | exactly 1, stable                             |
| 9  | no      | no  | 1     | unit | 1       | `…_0`         | pod fqdn (http)        | exactly 1, stable                             |
| 10 | no      | no  | 2     | unit | 2       | `…_0`, `…_1`  | pod fqdns              | exactly 2, both stable                        |
| 11 | no      | yes | 1     | unit | 1       | `…_0`         | pod fqdn (https)       | exactly 1, stable                             |
| 12 | no      | yes | 2     | unit | 2       | `…_0`, `…_1`  | pod fqdns (https)      | exactly 2, both stable                        |
| 13 | yes     | no  | 1     | unit | 1       | `…_0`         | IPU URL (http)         | exactly 1, stable                             |
| 14 | yes     | no  | 2     | unit | 2       | `…_0`, `…_1`  | IPU URLs               | exactly 2, both stable                        |
| 15 | yes     | yes | 1     | unit | 1       | `…_0`         | IPU URL (https)        | exactly 1, stable                             |
| 16 | yes     | yes | 2     | unit | 2       | `…_0`, `…_1`  | IPU URLs (https)       | exactly 2, both stable                        |

`M`=model, `U`=model_uuid, `A`=application.

### Manual verification

Reproduce the original bug via the Terraform module from issue #49 (COS with
`mimir_coordinator.units = 3`, backed by seaweedfs), force a Mimir leader election, and
confirm the datasource UID is stable and existing dashboards survive.

---

## 9. Release notes

- Document the `LIBAPI` v0 → v1 move and the new constructor surface
  (`app_datasource` / `unit_datasources` / `app_datasource_url` / `unit_datasource_url`;
  removal of `is_ingress_per_app` / `source_url`; `update_source` →
  `update_app_source` / `update_unit_source`) for all COS provider charms.
- Call out the **one-time UID change** on coordinated upgrade and the IPA↔app / IPU↔unit
  ingress pairing.
- Estimated effort (from issue discussion): ~3–4 days for the library + this repo;
  rollout across COS charms is additional coordinated work.

---

## 10. References

- Issue: [canonical/mimir-operators#49](https://github.com/canonical/mimir-operators/issues/49)
- Related Grafana duplicate-datasource behaviour: canonical/grafana-k8s-operator#568
- Library: `lib/charms/grafana_k8s/v1/grafana_source.py`
- Tests: `tests/unit/test_source_matrix.py`, `tests/integration/test_grafana_source.py`
