# Copyright 2025 Canonical
# See LICENSE file for licensing details.
"""Grafana config generator."""

import yaml
from models import DatasourceConfig
from typing import Callable, Optional, Dict, Any
from charms.hydra.v0.oauth import (
    OauthProviderConfig
)
from constants import DATABASE_PATH, DASHBOARDS_DIR
import configparser
from io import StringIO

class GrafanaConfig:
    """Grafana config generator."""

    def __init__(self,
                datasources_config: DatasourceConfig,
                oauth_config: Optional[OauthProviderConfig] = None,
                auth_env_config: Callable[[],Any] = lambda: {},
                db_config: Callable[[],Optional[Dict[str, str]]]  = lambda: None,
                db_type: str = "",
                enable_reporting: bool = True,
                enable_external_db: bool = False,
                tracing_endpoint: Optional[str] = None,
                 ):
        self._datasources_config = datasources_config
        self._oauth_config = oauth_config
        self._auth_env_config = auth_env_config
        self._db_config = db_config
        self._db_type = db_type
        self._enable_reporting = enable_reporting
        self._enable_external_db = enable_external_db
        self._tracing_endpoint = tracing_endpoint


    @property
    def oauth_config(self) -> Optional[OauthProviderConfig]:
        """Generate oauth config."""
        return self._oauth_config

    @property
    def auth_env_config(self) -> Any:
        """Generate auth environment config."""
        return self._auth_env_config()

    def generate_grafana_config(self) -> str:
        """Generate a configuration for Grafana."""
        configs = [self._generate_tracing_config(), self._generate_analytics_config(), self._generate_database_config()]
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

        for source_info in self._datasources_config.datasources():
            source = {
                "orgId": "1",
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
