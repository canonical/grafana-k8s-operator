# Copyright 2025 Canonical
# See LICENSE file for licensing details.
"""Grafana config generator."""

import configparser
import json
import logging
from io import StringIO
from typing import Any, Callable, Dict, Optional

import yaml
from charms.hydra.v0.oauth import OauthProviderConfig
from ops import ActiveStatus, BlockedStatus

import custom_ini_config
from constants import DATABASE_PATH, DASHBOARDS_DIR
from models import DatasourceConfig


logger = logging.getLogger()

ORGID_HEADER_NAME = "X-Scope-OrgID"


def _csv_to_list(roles: Optional[str]) -> list[str]:
    if not roles:
        return []
    return [role.strip().strip("'") for role in roles.split(',') if role.strip()]


def _tenant_org_mapping_to_dict(mapping: Optional[str]) -> Dict[str, int]:
    """Parse the ``tenant_org_mapping`` config into a ``tenant -> org_id`` mapping."""
    if not mapping:
        return {}
    try:
        raw = json.loads(mapping)
    except json.JSONDecodeError:
        logger.error(
            "Invalid tenant_org_mapping: expected a JSON object of the form "
            '{"<org_id>": ["<tenant>", ...]}. Got: %s',
            mapping,
        )
        return {}
    if not isinstance(raw, dict):
        logger.error("Invalid tenant_org_mapping: expected a JSON object, got %s", type(raw).__name__)
        return {}

    mapping_dict: Dict[str, int] = {}
    for org_id, tenants in raw.items():
        if not isinstance(tenants, list) or not all(isinstance(t, str) for t in tenants):
            logger.error(
                "Invalid tenant_org_mapping: value for org id %r must be a list of tenant "
                "strings",
                org_id,
            )
            continue
        try:
            int_org_id = int(org_id)
        except (TypeError, ValueError):
            logger.error("Invalid tenant_org_mapping: org id %r is not an integer", org_id)
            continue
        for tenant in tenants:
            if tenant in mapping_dict and mapping_dict[tenant] != int_org_id:
                logger.warning(
                    "tenant %r mapped to multiple orgs (%d and %d); using the last mapping",
                    tenant,
                    mapping_dict[tenant],
                    int_org_id,
                )
            mapping_dict[tenant] = int_org_id
    return mapping_dict


def _tenant_from_source(source_info: dict) -> Optional[str]:
    """Extract the Mimir tenant from a datasource's custom HTTP headers.

    Multi-tenant Mimir backends are reached through the standard ``X-Scope-OrgID``
    header. Grafana stores these as ``httpHeaderNameN`` (in ``jsonData``) /
    ``httpHeaderValueN`` (in ``secureJsonData`` or ``jsonData``).
    """
    json_data = source_info.get("extra_fields") or {}
    secure_json_data = source_info.get("secure_extra_fields") or {}

    headers = {
        **json_data,
        **secure_json_data,
    }

    for key, value in headers.items():
        if not str(key).startswith("httpHeaderName"):
            continue
        index = str(key)[len("httpHeaderName"):]
        if value != ORGID_HEADER_NAME:
            continue
        tenant = headers.get(f"httpHeaderValue{index}")
        if tenant:
            return str(tenant)
    return None


class GrafanaConfig:
    """Grafana config generator."""

    def __init__(self,
                *,
                datasources_config: DatasourceConfig,
                oauth_config: Optional[OauthProviderConfig] = None,
                auth_env_config: Callable[[],Any] = lambda: {},
                admin_roles: Optional[str] = None,
                editor_roles: Optional[str] = None,
                db_config: Callable[[],Optional[Dict[str, str]]]  = lambda: None,
                db_type: str = "",
                enable_reporting: bool = True,
                enable_external_db: bool = False,
                tracing_endpoint: Optional[str] = None,
                custom_config: Optional[str] = None,
                secret_getter: Callable[[str], Optional[str]] = lambda _: None,
                tenant_org_mapping_config: Callable[[], str] = lambda: "",
                 ):
        self._datasources_config = datasources_config
        self._oauth_config = oauth_config
        self._auth_env_config = auth_env_config
        self._db_config = db_config
        self._admin_roles = _csv_to_list(admin_roles)
        self._editor_roles = _csv_to_list(editor_roles)
        self._db_type = db_type
        self._enable_reporting = enable_reporting
        self._enable_external_db = enable_external_db
        self._tracing_endpoint = tracing_endpoint
        self._custom_config = custom_config
        self._secret_getter = secret_getter
        self._tenant_org_mapping_config = tenant_org_mapping_config


    @property
    def oauth_config(self) -> Optional[OauthProviderConfig]:
        """Generate oauth config."""
        return self._oauth_config

    @property
    def auth_env_config(self) -> Any:
        """Generate auth environment config."""
        return self._auth_env_config()

    @property
    def role_attribute_path(self) -> Optional[str]:
        """Generate role attribute path."""
        group_claim_path  = "groups[*]"
        if not self._admin_roles and not self._editor_roles:
            return None

        role_paths = []
        for admin_role in self._admin_roles:
            role_paths.append(f"contains({group_claim_path}, '{admin_role}') && 'Admin'")
        for editor_role in self._editor_roles:
            role_paths.append(f"contains({group_claim_path}, '{editor_role}') && 'Editor'")

        role_paths.append("'Viewer'")

        return " || ".join(role_paths)

    def get_status(self):
        """Intended to be called by collect-unit-status."""
        try:
            custom_ini_config.validate(self._custom_config)
            custom_ini_config.resolve_secrets(self._custom_config, self._secret_getter)
        except ValueError as e:
            logger.error("Invalid custom_config: %s", e)
            return BlockedStatus("Invalid custom_config; see debug-log")
        return ActiveStatus()

    def generate_grafana_config(self) -> str:
        """Generate a configuration for Grafana."""
        configs = [self._generate_tracing_config(), self._generate_analytics_config(), self._generate_database_config()]
        if self._custom_config is not None:
            try:
                custom_ini_config.validate(self._custom_config)
                resolved_config = custom_ini_config.resolve_secrets(
                    self._custom_config, self._secret_getter
                )
            except ValueError:
                pass
            else:
                if resolved_config is not None:
                    configs.append(resolved_config)

        if not self._enable_external_db:
            with StringIO() as data:
                config_ini = configparser.ConfigParser()
                config_ini["database"] = {
                    "type": "sqlite3",
                    "path": DATABASE_PATH,
                }
                config_ini.write(data)
                data.seek(0)
                configs.append(data.read())
        return "\n".join(filter(bool, configs))

    def generate_datasource_config(self) -> str:
        """Template out a Grafana datasource config.

        Template using the sources (and removed sources) the consumer knows about, and dump it to
        YAML.

        Returns:
            A string-dumped YAML config for the datasources
        """
        # Boilerplate for the config file
        datasources_dict = {"apiVersion": 1, "datasources": [], "deleteDatasources": []}

        tenant_to_org_id = _tenant_org_mapping_to_dict(self._tenant_org_mapping_config())

        for source_info in self._datasources_config.datasources():
            tenant = _tenant_from_source(source_info)
            org_id = tenant_to_org_id.get(tenant, 1) if tenant else 1
            source = {
                "orgId": str(org_id),
                "access": "proxy",
                "isDefault": "false",
                "name": source_info["source_name"],
                "type": source_info["source_type"],
                "url": source_info["url"],
            }
            if source_info.get("extra_fields", None):
                source["jsonData"] = source_info.get("extra_fields")
            if source_info.get("secure_extra_fields", None):
                source["secureJsonData"] = source_info.get("secure_extra_fields")

            # set timeout for querying this data source
            timeout = int(source.get("jsonData", {}).get("timeout", 0))
            configured_timeout = self._datasources_config.query_timeout
            if timeout < configured_timeout:
                json_data = source.get("jsonData", {})
                json_data.update({"timeout": configured_timeout})
                source["jsonData"] = json_data

            datasources_dict["datasources"].append(source)  # type: ignore[attr-defined]

        # Also get a list of all the sources which have previously been purged and add them
        for name in self._datasources_config.datasources_to_delete():
            source = {"orgId": 1, "name": name}
            datasources_dict["deleteDatasources"].append(source)  # type: ignore[attr-defined]

        datasources_string = yaml.dump(datasources_dict)
        return datasources_string

    def generate_dashboard_config(self) -> str:
        """Generate a configuration for watching Grafana dashboards in a directory."""
        dashboard_config = {
            "apiVersion": 1,
            "providers": [
                {
                    "name": "Default",
                    "updateIntervalSeconds": "5",
                    "type": "file",
                    "options": {"path": DASHBOARDS_DIR},
                }
            ],
        }
        return yaml.dump(dashboard_config)


    def _generate_tracing_config(self) -> str:
        """Generate tracing configuration.

        Returns:
            A string containing the required tracing information to be stubbed into the config
            file.
        """
        if self._tracing_endpoint is None:
            return ""

        config_ini = configparser.ConfigParser()
        config_ini["tracing.opentelemetry"] = {
            "sampler_type": "probabilistic",
            "sampler_param": "0.01",
        }
        # ref: https://github.com/grafana/grafana/blob/main/conf/defaults.ini#L1505
        config_ini["tracing.opentelemetry.otlp"] = {
            "address": self._tracing_endpoint,
        }

        # This is silly, but a ConfigParser() handles this nicer than
        # raw string manipulation
        data = StringIO()
        config_ini.write(data)
        ret = data.getvalue()
        return ret


    def _generate_analytics_config(self) -> str:
        """Generate analytics configuration.

        Returns:
            A string containing the analytics config to be stubbed into the config file.
        """
        if self._enable_reporting:
            return ""
        config_ini = configparser.ConfigParser()
        # Ref: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#analytics
        config_ini["analytics"] = {
            "application_insights_auto_route_tracking": "false",
            "application_insights_connection_string": "false",
            "feedback_links_enabled": "false",
            "reporting_enabled": "false",
            "check_for_updates": "false",
            "check_for_plugin_updates": "false",
        }

        data = StringIO()
        config_ini.write(data)
        ret = data.getvalue()
        return ret


    def _generate_database_config(self) -> str:
        """Generate a database configuration.

        Returns:
            A string containing the required database information to be stubbed into the config
            file.
        """
        config_ini = configparser.ConfigParser()
        db_type = self._db_type
        db_config = self._db_config()
        if not db_config:
            return ""

        db_url = f"{db_type}://{db_config.get('user')}:{db_config.get('password')}@{db_config.get('host')}/{db_config.get('name')}"
        config_ini["database"] = {
            "type": db_type,
            "host": db_config.get("host", ""),
            "name": db_config.get("name", ""),
            "user": db_config.get("user", ""),
            "password": db_config.get("password", ""),
            "url": db_url,
        }

        # This is still silly
        data = StringIO()
        config_ini.write(data)
        ret = data.getvalue()
        return ret
