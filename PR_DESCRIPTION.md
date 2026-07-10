# Add relation-scoped, pass-through delta API to `GrafanaDashboardProvider`

## What

Adds two backward-compatible methods to `GrafanaDashboardProvider` in
`lib/charms/grafana_k8s/v0/grafana_dashboard.py`:

```python
def add_dashboard_precompressed(
    self, key: str, encoded_content: str, inject_dropdowns: bool = True
) -> None: ...

def remove_dashboard(self, key: str) -> None: ...
```

`add_dashboard_precompressed` stores an **already LZMA+base64-compressed**
dashboard **verbatim** under a caller-controlled key (`prog:{key}`), without
decompressing or re-compressing it. `remove_dashboard` removes a single
dashboard by that key in O(1), without rescanning the dashboards directory.

`LIBPATCH` is bumped `50 -> 51` (feature add, no breaking change, `LIBAPI`
unchanged). The module docstring documents the new API.

## Why

This implements **item 4 of ADR-0001** ("Scalable dashboard/rule convergence
for large fan-in aggregators"), which is the **prerequisite** that unblocks an
O(1) publish path for aggregator charms.

Central aggregators (notably OpenTelemetry Collector) fan-in dashboards from
~300 relations. The existing publish path
(`reload_dashboards()` -> `_update_all_dashboards_from_dir()`) is
unconditionally `O(all files on disk)`: it globs the entire dashboards
directory and **re-compresses every file** on every hook, even when nothing
changed. Dashboards received over `grafana_dashboard` arrive already
compressed and are forwarded **verbatim**, so the incoming compressed blob is
byte-identical to the blob that must be published. The old API forced a
pointless `decompress -> disk -> re-compress -> rescan` round-trip.

These methods let an aggregator hand the compressed blob straight through,
keyed per relation, so the per-hook cost becomes proportional to the *changed*
dashboard rather than to the total number of dashboards.

## API contract

- **Verbatim pass-through:** `encoded_content` is stored exactly as provided.
  No decompress, no re-compress, no `uid`/tag re-rendering (the origin charm
  already rendered those; re-parsing would require a decompress).
- **Caller-controlled keying:** dashboards are stored under `prog:{key}`, in
  the same `prog:` namespace swept by `remove_non_builtin_dashboards()`, so a
  full reconcile still cleans up precompressed dashboards. Callers must use
  stable, unique keys (e.g. `rel_5__my-dashboard`).
- **Caller is trusted (no payload validation):** `encoded_content` is not
  decompressed to validate it — doing so would defeat the entire optimization.
  Malformed content is rejected downstream by Grafana, exactly as today. The
  only guard is a `ValueError` on an empty `key` or empty `encoded_content`.
- **Leadership:** `_stored` is updated regardless of leadership (so state is
  present when the unit becomes leader); the databag is written only by the
  leader. This mirrors the existing `add_dashboard` behavior.
- **Idempotent:** re-adding the same key+content does not churn the databag
  `uuid` (rides the existing "skip write if unchanged" guard in
  `_upset_dashboards_on_relation`); `remove_dashboard` on an unknown key is a
  no-op.

## Testing

New `unittest`/`Harness` tests in
`tests/unit/test_dashboard_provider.py` (class
`TestDashboardProviderPrecompressed`), matching the file's existing style.
Fixtures are **computed live** (`LZMABase64.compress(json.dumps(...))`) so the
tests assert the real invariant — *bytes in == bytes out, and they still
decompress to the original* — rather than coupling to a frozen base64 literal.

Behaviors locked down:

1. **Byte-fidelity pass-through** — published `content` is byte-identical to
   the input and still decompresses to the original dashboard.
2. **Caller key controls the id** — published as `prog:{key}`, correct
   `dashboard_alt_uid`, schema parity with existing entries.
3. **`inject_dropdowns=False`** -> `juju_topology == {}`.
4. **Keyed removal is selective and idempotent** — only the requested key is
   removed; other precompressed and `file:` dashboards remain; unknown key is a
   no-op.
5. **No decompress / re-compress / rescan** — spies assert
   `LZMABase64.compress`, `LZMABase64.decompress`, and
   `CharmedDashboard.load_dashboards_from_dir` are **not** called by the delta
   path. This is the anti-regression net for the O(1) guarantee itself; a
   companion test asserts built-in `file:` dashboards are untouched by a delta.
6. **Empty-arg guard** — empty `key` or `encoded_content` raises `ValueError`.
7. **Leadership** — non-leader updates `_stored` but not the databag; the delta
   is flushed on becoming leader.
8. **Idempotent republish** — re-adding identical key+content leaves the
   databag `uuid` and templates unchanged.

Run:

```sh
tox -e unit
# or, targeting just this file:
PYTHONPATH="$PWD:$PWD/lib:$PWD/src" uv run --frozen --isolated --extra=dev \
  python -m pytest tests/unit/test_dashboard_provider.py
```

Result: `17 passed` (7 existing provider tests + 10 new).

## Compatibility

- Purely additive: no existing method changed; `LIBPATCH` bump only.
- Existing `add_dashboard` / `remove_non_builtin_dashboards` behavior is
  unchanged and still covered by their existing tests.

## Out of scope (fast-follow)

This PR lands **only** the library prerequisite (ADR-0001 item 4). The
consumer-side work that actually calls these methods lives in
`opentelemetry-collector-k8s-operator` and will be a separate PR once this
library is published to Charmhub:

- item 1: event-scoped delta convergence (process only `event.relation`);
- item 2: `rel_{id}__` filename prefixes + `container.list_files` deletion;
- item 3: per-relation fingerprints in peer/stored-state (no `pebble pull`);
- item 5: explicit, infrequent full-reconcile triggers;
- item 6: the mandatory `reconcile` action.
