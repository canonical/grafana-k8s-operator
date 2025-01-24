# External probes

These probes are meant to be run from the host where the juju client is installed,

```bash
juju export-bundle | ./probe_bundle.py
juju status --format=yaml | ./probe_status.py
juju show-unit --format=yaml | ./probe_show_unit.py
```

or by piping in the bundle or status yaml,

```bash
cat bundle.yaml | ./probe_bundle.py
cat status.yaml | ./probe_status.py
cat show_unit.yaml | ./probe_show_unit.py
```