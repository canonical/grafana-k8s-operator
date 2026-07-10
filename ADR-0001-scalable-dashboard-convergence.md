# ADR-0001: Scalable dashboard/rule convergence for large fan-in aggregators

- Status: Proposed
- Date: 2026-07-09
- Deciders: Observability team
- Related:
  - https://github.com/canonical/opentelemetry-collector-operator/issues/297
  - https://github.com/canonical/opentelemetry-collector-operator/issues/331
- Affects: `GrafanaDashboardProvider` (this repo, `lib/charms/grafana_k8s/v0/grafana_dashboard.py`),
  consuming aggregator charms (e.g. `opentelemetry-collector-k8s-operator`)

## Context

Central aggregator charms (notably OpenTelemetry Collector) fan-in configuration
assets — Grafana dashboards over `grafana_dashboard`, and alert rules over the
OTLP interface — from a large number of related applications (~300 relations,
each potentially providing more than one asset).

Dashboards and rules are transported **LZMA+base64-compressed** to keep Juju
relation databags under size limits. This compression is a deliberate and
necessary feature at scale.

The current model is **full reconcile on every hook** ("recreate the world"):

1. The aggregator iterates over *all* relations, `relation-get`s each databag,
   `LZMABase64.decompress`es every asset, and writes files to the workload disk.
2. For dashboards, the aggregator delegates publishing to
   `GrafanaDashboardProvider.reload_dashboards()`, which calls
   `_update_all_dashboards_from_dir()`. That method **rescans the entire
   dashboards directory** (`load_dashboards_from_dir` globs `**/*`),
   **re-compresses every file** with `LZMABase64.compress`, wipes all `file:`
   entries from `StoredState`, and rebuilds them.
3. Rules follow an analogous disk round-trip: received rules are staged to disk
   and then re-read and re-published by the send-side consumers.

### Observed bottlenecks at ~300 relations

- **Juju/Pebble I/O dominates.** `relation-get` is a synchronous round-trip to
  the controller; `pebble push`/`pull` add I/O and communication overhead. Doing
  this for all relations on every hook produces long settlement times.
- **Redundant compute.** The receive→decompress→disk→re-compress→publish cycle
  spends CPU decompressing and re-compressing content that has usually not
  changed since the previous hook. A TLS cert renewal or unrelated config change
  reprocesses all ~300 relations for no benefit.
- **Change-detection via workload state is also expensive.** Comparing file
  hashes requires a `pebble pull` to read current workload state, which is just
  as costly and does not solve the latency problem.

### The structural correlation gap

A per-relation ("delta") fast path requires both layers to be relation-scoped,
but they are not:

- The aggregator's fan-in is inherently `O(all relations)`.
- `GrafanaDashboardProvider` has **no concept of a relation**. Its keying is
  `id = "file:{path.stem}"`, derived from the filename on disk. `reload_dashboards()`
  is unconditionally `O(all files on disk)`: it globs the whole directory and
  re-compresses everything.

The relation id survives only as a substring inside the aggregator's filenames
(`juju_{title}-{charm}-{rel_id}.json`), which the library treats opaquely.
Consequently, even if the aggregator writes a single file for the changed
relation, `reload_dashboards()` still rescans and re-compresses **all** files.

This means: scoping to `event.relation` makes the **disk write** O(1), but the
**publish path stays O(N)** because the library rebuilds from the full directory.
**Deletion** *can* be made O(1)-ish (via a `rel_id` filename prefix +
`container.list_files`, no databag reads), but **publish cannot** without a
library change.

## Decision

Adopt a **delta-as-fast-path, full-reconcile-as-safety-net** architecture, and
introduce the library support needed to make the publish path relation-scoped.

1. **Event-scoped delta convergence.** On `relation-changed`, process only
   `event.relation` (one `relation-get`, not N); on `relation-departed`/`broken`,
   remove only that relation's assets. This collapses the common-case per-hook
   cost from `O(N)` to `O(1)`.

2. **Relation-id-prefixed filenames + `list_files` for deletion deltas.** Use a
   reliably parseable prefix (e.g. `rel_{id}__…`). Deletion becomes a single
   cheap metadata call (`list_files`) filtered by prefix — no `relation-get`,
   no content `pull`.


3. **Per-relation fingerprint in peer/stored-state (no `pebble pull`).** Store a
   hash of each relation's **raw compressed** databag blob. On `relation-changed`,
   hash only `event.relation`'s raw blob and skip work when unchanged. Change
   detection compares against charm state, never against workload content.

4. **Compressed pass-through where content is forwarded verbatim (dashboards).**
   Add a relation-scoped, pre-compressed, delta API to `GrafanaDashboardProvider`
   (e.g. `add_dashboard_precompressed(key, encoded_content, …)` + keyed removal)
   so the aggregator can hand already-compressed blobs straight through, avoiding
   both the decompress and the re-compress, and eliminating the wholesale
   `reload_dashboards()` rescan. This is the prerequisite that makes an O(1)
   publish path possible. (Rules are **mutated** — topology-label injection and
   validation — so pass-through does not apply to them; they rely on items 1–3.)

5. **Full reconcile becomes explicit and infrequent.** Run the "recreate the
   world" path only on `start` (skippable if dashboards/rules live on a
   persistent volume), `upgrade-charm`, whole-fleet config changes (e.g.
   toggling `forward_alert_rules`), and a mandatory **`reconcile` action**.

6. **A `reconcile` action is a hard requirement, not optional.** Delta-charming
   shifts a correctness burden onto peer/stored-state accuracy. If state and the
   workload disk diverge (crash mid-push, volume loss, manual edits), the fast
   path will not self-correct until a full reconcile. The action (plus persistent
   volume and the `start` trigger) is the invariant that makes delta safe.

## Consequences

### Positive

- Common-case per-hook cost drops from `O(N)` to `O(1)`; settlement times shrink.
- Eliminates redundant `relation-get` fan-in, `pebble pull`-based change
  detection, and (for dashboards) the decompress→re-compress cycle.
- Preserves the small-databag benefit of compression; only *redundant* compute
  is removed.

### Negative / risks

- Reduced automatic self-healing on the fast path; correctness now depends on
  peer/stored-state fidelity, mitigated by the mandatory `reconcile` action.
- Requires a **`GrafanaDashboardProvider` API addition** (item 4) and a coordinated
  change in consuming aggregator charms; a library API/patch bump is needed.
- Filename prefix scheme and fingerprint bookkeeping add implementation complexity.
- Rules cannot use pass-through (content is mutated), so their gains come from
  event-scoping and fingerprinting only.

## Alternatives considered

- **Hash-gating alone (compare against workload/state) without event-scoping.**
  Rejected as the primary fix: it still reads all databags and, when comparing to
  the workload, requires an expensive `pebble pull`. It remains useful as a
  secondary optimization layered on the smaller working set.
- **Keep full reconcile, delta only the disk writes.** Removes fan-in and
  decompress cost but leaves an `O(N)` re-compress on publish because
  `reload_dashboards()` still rebuilds from the whole directory. Acceptable only
  as an interim step until the library API (item 4) lands.
- **Continuous immediate convergence on every hook.** Rejected: this is the
  current behavior and the source of the latency problem at ~300 relations.
