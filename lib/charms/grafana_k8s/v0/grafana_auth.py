# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""grafana-auth library.

This library implements the grafana-auth relation interface,
it contains the Requirer and Provider classes for handling
the interface.
With this library charms can to configure authentication to Grafana.
The provider will set the authentication mode that it needs,
and will pass the necessary configuration of that authentication mode.
The requirer will consume the authentication configuration to authenticate to Grafana.

## Getting Started
From a charm directory, fetch the library using `charmcraft`:
```shell
charmcraft fetch-lib charms.grafana_k8s.v0.grafana_auth
```
You will also need to add the following library to the charm's `requirements.txt` file:
- jsonschema

### Provider charm
Example:
An example on how to use the AuthProvider with proxy mode using default configuration options.
The default arguments are:
    `charm : CharmBase`
    `relation_name: str : grafana-auth`
    `header_name: str : X-WEBAUTH-USER`
    `header_property: str : username`
    `auto_sign_up: bool : True`
    `sync_ttl: int : None`
    `whitelist: list[str] : None`
    `headers: list[str] : None`
    `headers_encoded: bool : None`
    `enable_login_token: bool : None`
```python
from charms.grafana_k8s.v0.grafana_auth import GrafanaAuthProxyProvider
from ops.charm import CharmBase
class ExampleProviderCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        ...
        self.grafana_auth_proxy_provider = GrafanaAuthProxyProvider(self)
        self.framework.observe(
            self.grafana_auth_proxy_provider.on.urls_available, self._on_urls_available
        )
        ...
```
Values different than defaults must be set from the class constructor.
The [official documentation](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/auth-proxy/)
of Grafana provides further explanation on the values that can be assigned to the different variables.
Example:
```python
from charms.grafana_k8s.v0.grafana_auth import GrafanaAuthProxyProvider
from ops.charm import CharmBase
class ExampleProviderCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        ...
        self.grafana_auth_proxy_provider = GrafanaAuthProxyProvider(
            self,
            header_property="email",
            auto_sign_up=False,
            whitelist=["localhost","canonical.com"],
        )
        self.framework.observe(
            self.grafana_auth_proxy_provider.on.urls_available, self._on_urls_available
        )
        ...
```
### Requirer charm
Example:
An example on how to use the auth requirer.
```python
from charms.grafana_k8s.v0.grafana_auth import AuthRequirer
from ops.charm import CharmBase
class ExampleRequirerCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.auth_requirer = AuthRequirer(
            self,
            auth_requirer=["https://example.com/"]
        )
        self.framework.observe(
            self.auth_requirer.on.auth_conf_available, self._on_auth_conf_available
        )
```
"""  # noqa

import json
import logging
from typing import Any, Dict, List, Optional, Union

from jsonschema import validate  # type: ignore[import]
from ops.charm import (
    CharmBase,
    CharmEvents,
    LeaderElectedEvent,
    PebbleReadyEvent,
    RelationChangedEvent,
    RelationJoinedEvent,
)
from ops.framework import (
    BoundEvent,
    EventBase,
    EventSource,
    Object,
    StoredDict,
    StoredList,
)

# The unique Charmhub library identifier, never change it
LIBID = "e9e05109343345d4bcea3bce6eacf8ed"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 4

AUTH_PROXY_PROVIDER_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "$id": "https://canonical.github.io/charm-relation-interfaces/grafana_auth/schemas/provider.json",
    "type": "object",
    "title": "`grafana_auth` provider schema",
    "description": "The `grafana_auth` root schema comprises the entire provider databag for this interface.",
    "documentation": "https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/auth-proxy/",
    "default": {},
    "examples": [
        {
            "application-data": {
                "auth": {
                    "proxy": {
                        "enabled": True,
                        "header_name": "X-WEBAUTH-USER",
                        "header_property": "username",
                        "auto_sign_up": True,
                    }
                }
            }
        }
    ],
    "required": ["application-data"],
    "properties": {
        "application-data": {
            "$id": "#/properties/application-data",
            "title": "Application Databag",
            "type": "object",
            "additionalProperties": True,
            "required": ["auth"],
            "properties": {
                "auth": {
                    "additionalProperties": True,
                    "anyOf": [{"required": ["proxy"]}],
                    "type": "object",
                    "properties": {
                        "proxy": {
                            "$id": "#/properties/application-data/proxy",
                            "type": "object",
                            "required": ["header_name", "header_property"],
                            "additionalProperties": True,
                            "properties": {
                                "enabled": {
                                    "$id": "#/properties/application-data/proxy/enabled",
                                    "type": "boolean",
                                    "default": True,
                                },
                                "header_name": {
                                    "$id": "#/properties/application-data/proxy/header_name",
                                    "type": "string",
                                },
                                "header_property": {
                                    "$id": "#/properties/application-data/proxy/header_property",
                                    "type": "string",
                                },
                                "auto_sign_up": {
                                    "$id": "#/properties/application-data/proxy/auto_sign_up",
                                    "type": "boolean",
                                    "default": True,
                                },
                                "sync_ttl": {
                                    "$id": "#/properties/application-data/proxy/sync_ttl",
                                    "type": "integer",
                                    "default": 60,
                                },
                                "whitelist": {
                                    "$id": "#/properties/application-data/proxy/whitelist",
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "headers": {
                                    "$id": "#/properties/application-data/proxy/headers",
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "headers_encoded": {
                                    "$id": "#/properties/application-data/proxy/headers_encoded",
                                    "type": "boolean",
                                    "default": False,
                                },
                                "enable_login_token": {
                                    "$id": "#/properties/application-data/proxy/enable_login_token",
                                    "type": "boolean",
                                    "default": False,
                                },
                            },
                        }
                    },
                }
            },
        }
    },
    "additionalProperties": True,
}
REQUIRER_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "$id": "https://canonical.github.io/charm-relation-interfaces/interfaces/grafana_auth/schemas/requirer.json",
    "type": "object",
    "title": "`grafana_auth` requirer schema",
    "description": "The `grafana_auth` root schema comprises the entire consumer databag for this interface.",
    "default": {},
    "examples": [{"application-data": {"urls": ["https://grafana.example.com/"]}}],
    "required": ["application-data"],
    "properties": {
        "application-data": {
            "$id": "#/properties/application-data",
            "title": "Application Databag",
            "type": "object",
            "additionalProperties": True,
            "required": ["urls"],
            "urls": {"$id": "#/properties/application-data/urls", "type": "list"},
        }
    },
    "additionalProperties": True,
}

DEFAULT_RELATION_NAME = "grafana-auth"
AUTH = "auth"
logger = logging.getLogger(__name__)


def _type_convert_stored(obj):
    """Convert Stored* to their appropriate types, recursively."""
    if isinstance(obj, StoredList):
        return list(map(_type_convert_stored, obj))
    if isinstance(obj, StoredDict):
        return {k: _type_convert_stored(obj[k]) for k in obj.keys()}
    return obj


class UrlsAvailableEvent(EventBase):
    """Charm event triggered when provider charm extracts the urls from relation data."""

    def __init__(self, handle, urls: list, relation_id: int):
        super().__init__(handle)
        self.urls = urls
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            "urls": self.urls,
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot: dict):
        """Restores snapshot."""
        self.urls = _type_convert_stored(snapshot["urls"])
        self.relation_id = snapshot["relation_id"]


class AuthProviderCharmEvents(CharmEvents):
    """List of events that the auth provider charm can leverage."""

    urls_available = EventSource(UrlsAvailableEvent)


class AuthProvider(Object):
    """Base class for authentication configuration provider classes.

    This class shouldn't be initialized,
    Its children classes define the authentication mode and configuration to be used.
    """

    on = AuthProviderCharmEvents()  # pyright: ignore

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str,
        refresh_event: Optional[BoundEvent] = None,
    ):
        super().__init__(charm, relation_name)
        self._auth_config: Dict[str, Dict[str, Any]] = {}
        self._charm = charm
        self._relation_name = relation_name
        if not refresh_event:
            container = list(self._charm.meta.containers.values())[0]
            if len(self._charm.meta.containers) == 1:
                refresh_event = self._charm.on[container.name.replace("-", "_")].pebble_ready
            else:
                logger.warning(
                    "%d containers are present in metadata.yaml and "
                    "refresh_event was not specified. Defaulting to update_status. ",
                    len(self._charm.meta.containers),
                )
                refresh_event = self._charm.on.update_status

        assert type(refresh_event) is BoundEvent  # for static checker
        self.framework.observe(refresh_event, self._get_urls_from_relation_data)
        self.framework.observe(
            self._charm.on[relation_name].relation_joined,
            self._set_auth_config_in_relation_data,
        )
        self.framework.observe(
            self._charm.on.leader_elected, self._set_auth_config_in_relation_data
        )
        self.framework.observe(
            self._charm.on[relation_name].relation_changed, self._get_urls_from_relation_data
        )

    def _set_auth_config_in_relation_data(
        self, event: Union[LeaderElectedEvent, RelationJoinedEvent]
    ) -> None:
        """Handler triggered on relation joined and leader elected events.

        Adds authentication config to relation data.

        Args:
            event: Juju event

        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not self._auth_config:
            return
        if not self._validate_auth_config_json_schema():
            return
        relation_data = relation.data[self._charm.app]
        relation_data[AUTH] = json.dumps(self._auth_config)

    def _get_urls_from_relation_data(
        self, event: Union[PebbleReadyEvent, RelationChangedEvent]
    ) -> None:
        """Handler triggered on relation changed and pebble_ready events.

        Extracts urls from relation data and emits the urls_available event

        Args:
            event: Juju event

        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return
        urls_json = relation.data[relation.app].get("urls", "")  # type: ignore
        if not urls_json:
            logger.warning("No urls found in %s relation data", self._relation_name)
            return

        urls = json.loads(urls_json)

        self.on.urls_available.emit(urls=urls, relation_id=relation.id)  # pyright: ignore

    def _validate_auth_config_json_schema(self) -> bool:
        """Implemented in children classes."""
        raise NotImplementedError


class AuthConfAvailableEvent(EventBase):
    """Charm Event triggered when authentication config is ready."""

    def __init__(self, handle, auth: dict, relation_id: int):
        super().__init__(handle)
        self.auth = auth
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            AUTH: self.auth,
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot: dict):
        """Restores snapshot."""
        self.auth = _type_convert_stored(snapshot[AUTH])
        self.relation_id = snapshot["relation_id"]


class AuthRequirerCharmEvents(CharmEvents):
    """List of events that the auth requirer charm can leverage."""

    auth_conf_available = EventSource(AuthConfAvailableEvent)


class AuthRequirer(Object):
    """Authentication configuration requirer class."""

    on = AuthRequirerCharmEvents()  # pyright: ignore

    def __init__(
        self,
        charm,
        urls: List[str],
        relation_name: str = DEFAULT_RELATION_NAME,
        refresh_event: Optional[BoundEvent] = None,
    ):
        """Constructs an authentication requirer that consumes authentication configuration.

        The charm initializing this class requires authentication configuration,
        and it's expected to provide a list of url(s) to the service it's authenticating to.
        This class can be initialized as follows:

            self.auth_requirer = AuthRequirer(
            self,
            auth_requirer=["https://example.com/"]
            )

        Args:
            charm: CharmBase: the charm which manages this object.
            urls: List[str]: a list of urls to access the service the charm needs to authenticate to.
            relation_name: str: name of the relation in `metadata.yaml` that has the `grafana_auth` interface.
            refresh_event: an optional bound event which will be observed to re-set authentication configuration.
        """
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        self._urls = urls
        if not refresh_event:
            container = list(self._charm.meta.containers.values())[0]
            if len(self._charm.meta.containers) == 1:
                refresh_event = self._charm.on[container.name.replace("-", "_")].pebble_ready
            else:
                logger.warning(
                    "%d containers are present in metadata.yaml and "
                    "refresh_event was not specified. Defaulting to update_status.",
                    len(self._charm.meta.containers),
                )
                refresh_event = self._charm.on.update_status

        assert type(refresh_event) is BoundEvent  # for static checker
        self.framework.observe(refresh_event, self._get_auth_config_from_relation_data)

        self.framework.observe(
            self._charm.on[relation_name].relation_changed,
            self._get_auth_config_from_relation_data,
        )
        self.framework.observe(
            self._charm.on[relation_name].relation_joined, self._set_urls_in_relation_data
        )
        self.framework.observe(self._charm.on.leader_elected, self._set_urls_in_relation_data)

    def _set_urls_in_relation_data(
        self, event: Union[LeaderElectedEvent, RelationJoinedEvent]
    ) -> None:
        """Handler triggered on relation joined events. Adds URL(s) to relation data.

        Args:
            event: Juju event

        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relation_name)
        if not relation or not self._urls:
            return
        try:
            validate({"application-data": {"urls": self._urls}}, REQUIRER_JSON_SCHEMA)
        except:  # noqa: E722
            return
        relation_data = relation.data[self._charm.app]
        relation_data["urls"] = json.dumps(self._urls)

    def _get_auth_config_from_relation_data(
        self, event: Union[PebbleReadyEvent, RelationChangedEvent]
    ) -> None:
        """Handler triggered on relation changed and pebble_ready events.

        Extracts authentication config from relation data.
        Emits an event that contains the config.

        Args:
            event: Juju event

        Returns:
            None
        """
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return

        auth_conf_json = relation.data[relation.app].get(AUTH, "")

        if not auth_conf_json:
            logger.warning(
                "No authentication config found in %s relation data", self._relation_name
            )
            return

        auth_conf = json.loads(auth_conf_json)

        self.on.auth_conf_available.emit(  # pyright: ignore
            auth=auth_conf,
            relation_id=relation.id,
        )


class GrafanaAuthProxyProvider(AuthProvider):
    """Authentication configuration provider class.

    Provides proxy mode for authentication to Grafana.
    """

    _AUTH_TYPE = "proxy"
    _ENABLED = True

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = DEFAULT_RELATION_NAME,
        refresh_event: Optional[BoundEvent] = None,
        header_name: str = "X-WEBAUTH-USER",
        header_property: str = "username",
        auto_sign_up: bool = True,
        sync_ttl: Optional[int] = None,
        whitelist: Optional[List[str]] = None,
        headers: Optional[List[str]] = None,
        headers_encoded: Optional[bool] = None,
        enable_login_token: Optional[bool] = None,
    ) -> None:
        """Constructs GrafanaAuthProxyProvider.

        The charm initializing this object configures the authentication to grafana using proxy authentication mode.
        This object can be initialized as follows:

            self.grafana_auth_proxy_provider = GrafanaAuthProxyProvider(self)

        Args:
            charm: CharmBase: the charm which manages this object.
            relation_name: str: name of the relation in `metadata.yaml` that has the `grafana_auth` interface.
            refresh_event: an optional bound event which will be observed to re-set urls.
            header_name: str: HTTP Header name that will contain the username or email
            header_property: str: HTTP Header property, defaults to username but can also be `email`.
            auto_sign_up: bool: Set to `true` to enable auto sign-up of users who do not exist in Grafana DB.
            sync_ttl: int: Define cache time to live in minutes.
            whitelist: list[str]: Limits where auth proxy requests come from by configuring a list of IP addresses.
            headers: list[str]: Optionally define more headers to sync other user attributes.
            headers_encoded: bool: Non-ASCII strings in header values are encoded using quoted-printable encoding
            enable_login_token: bool

        Returns:
            None
        """  # noqa
        super().__init__(charm, relation_name, refresh_event)
        self._auth_config[self._AUTH_TYPE] = {}
        self._auth_config[self._AUTH_TYPE]["enabled"] = self._ENABLED
        self._auth_config[self._AUTH_TYPE]["header_name"] = header_name
        self._auth_config[self._AUTH_TYPE]["header_property"] = header_property
        self._auth_config[self._AUTH_TYPE]["auto_sign_up"] = auto_sign_up
        if sync_ttl:
            self._auth_config[self._AUTH_TYPE]["sync_ttl"] = sync_ttl
        if whitelist:
            self._auth_config[self._AUTH_TYPE]["whitelist"] = whitelist
        if headers:
            self._auth_config[self._AUTH_TYPE]["headers"] = headers
        if headers_encoded is not None:
            self._auth_config[self._AUTH_TYPE]["headers_encoded"] = headers_encoded
        if enable_login_token is not None:
            self._auth_config[self._AUTH_TYPE]["enable_login_token"] = enable_login_token

    def _validate_auth_config_json_schema(self) -> bool:
        """Validates authentication configuration using json schemas.

        Returns:
            bool: Whether the configuration is valid or not based on the json schema.
        """
        try:
            validate(
                {"application-data": {"auth": self._auth_config}}, AUTH_PROXY_PROVIDER_JSON_SCHEMA
            )
            return True
        except:  # noqa: E722
            return False
