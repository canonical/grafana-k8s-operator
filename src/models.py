# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""Data models class."""

import dataclasses
from typing import Callable, List, Optional

@dataclasses.dataclass
class TLSConfig:
    """TLS config model."""
    certificate: str
    key: str
    ca: str

@dataclasses.dataclass
class DatasourceConfig:
    """Grafana datasource config."""
    datasources: Callable[[], List[dict]]
    datasources_to_delete: Callable[[],List[str]]
    query_timeout: int = 0

@dataclasses.dataclass
class PebbleEnvironment:
    """Grafana pebble service environment config."""
    external_url: str
    log_level:str = "info"
    allow_embedding: bool = False
    allow_anonymous_access: bool = False
    enable_auto_assign_org: bool = True
    enable_profiling: bool = False
    tracing_resource_attributes: Optional[str] = None
    admin_user: Optional[str] = None
    admin_password: Optional[str] = None


