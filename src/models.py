# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""Data models class."""

import dataclasses
from typing import Callable, List
from cosl import JujuTopology

@dataclasses.dataclass
class TLSConfig:
    """TLS config model."""
    certificate: str
    key: str
    ca: str

@dataclasses.dataclass
class TracingConfig:
    """Grafana tracing config."""
    endpoint: str
    juju_topology: JujuTopology

@dataclasses.dataclass
class DatasourceConfig:
    """Grafana datasource config."""
    datasources: Callable[[], List[dict]]
    datasources_to_delete: Callable[[],List[str]]
    query_timeout: int = 0

@dataclasses.dataclass
class PebbleEnvConfig:
    """Grafana pebble service environment config."""
    log_level:str = "info"
    allow_embedding: bool = False
    allow_anonymous_access: bool = False
    enable_auto_assign_org: bool = True


