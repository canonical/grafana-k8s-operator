"""grafana_metadata.

This library implements data accessors the grafana-metadata interface.  The grafana-metadata interface is used to
transfer information about an instance of Grafana, such information to access and uniquely identify it.  Typically, this
is useful for charms that create a Grafana instance and want other applications to be able to access it.

## Usage

### Requirer

Add the following to your `charmcraft.yaml` or `metadata.yaml`:

```yaml
requires:
  grafana-metadata:
    # The example below uses the API for when limit=1.  If you need to support multiple related applications, remove
    # this and use the list-based data accessor method.
    limit: 1
    interface: grafana_metadata
```

To implement handling this relation:

* observe the relation-changed event for this relation wherever your charm needs to use this data (this relation DOES
  NOT automatically observe any events)
* wherever you need access to the data, create a `GrafanaMetadataRequirer` instance and use `.get_data()`

An example implementation is:

```python
class FooCharm(CharmBase):
    def __init__(self, framework):
        super().__init__(framework)
        self.framework.observe(self.on["grafana-metadata"].relation_changed, self._on_grafana_metadata_changed)

    def do_something_with_metadata(self):
        # Get exactly one related application's data, raising if more than one is available
        grafana_metadata = GrafanaMetadataRequirer(self.model.relations, "grafana-metadata")
        metadata = grafana_metadata.get_data()
        ...
```

### Provider

Add the following to your `charmcraft.yaml` or `metadata.yaml`:

```yaml
provides:
  grafana-metadata:
    interface: grafana_metadata
```

To manage sending data to related applications in your charm, use `GrafanaMetadataProvider`.  Note that
`GrafanaMetadataProvider` *does not* manage any events, but instead provides a `publish` method for sending data to
all related applications.  Triggering `publish` appropriately is left to the charm author, although generally you want
to do this at least during relation_joined and leader_elected events.  An example implementation is:

```python
class FooCharm(CharmBase):
    def __init__(self, framework):
        super().__init__(framework)
        self.grafana_metadata = GrafanaMetadataProvider(
            relations=self.model.relations,
            app=self.app,
            grafana_uid=self.unique_name,
            direct_url=self.direct_url,
            ingress_url=self.external_url,
            relation_name="grafana-metadata"
        )

        self.framework.observe(self.on.leader_elected, self.do_something_to_publish)
        self.framework.observe(self._charm.on["grafana-metadata"].relation_joined, self.do_something_to_publish)
        self.framework.observe(self.on.some_event_that_changes_grafanas_url, self.do_something_to_publish)
```
"""
import json
import logging
from typing import Optional

from ops import RelationMapping, Application
from pydantic import AnyHttpUrl, BaseModel, Field

# The unique Charmhub library identifier, never change it
LIBID = "26290f24974540adb4464b695bd01ea3"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

PYDEPS = ["pydantic>=2"]

log = logging.getLogger(__name__)

GRAFANA_METADATA_RELATION_NAME = "grafana-metadata"


class GrafanaMetadataAppData(BaseModel):
    """Data model for the grafana-metadata interface."""

    ingress_url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="The non-internal URL at which this application can be reached.  Typically, this is an ingress URL.",

    )
    direct_url: AnyHttpUrl = Field(
        description="The cluster-internal URL at which this application can be reached.  Typically, this is a"
                    " Kubernetes FQDN like name.namespace.svc.cluster.local for connecting to the prometheus api"
                    " from inside the cluster, with scheme."
    )
    grafana_uid: str = Field(description="The UID of this Grafana application.")


class GrafanaMetadataRequirer:
    """The requirer side of the grafana-metadata relation."""

    def __init__(
        self,
        relations: RelationMapping,
        relation_name: str = GRAFANA_METADATA_RELATION_NAME,
    ) -> None:
        """Initialize the GrafanaMetadataRequirer object.

        This object is for accessing data from relations that use the grafana-metadata interface.  It **does not**
        autonomously handle the events associated with that relation.  It is up to the charm using this object to
        observe those events as they see fit.  Typically, that charm should observe this relation's relation-changed
        event.

        This object is for interacting with a relation that has limit=1 set in charmcraft.yaml.  In particular, the
        get_data method will raise if more than one related application is available.

        Args:
            relations: The RelationMapping of a charm (typically `self.model.relations` from within a charm object).
            relation_name: The name of the relation.
        """
        self._charm_relation_mapping = relations
        self._relation_name = relation_name

    @property
    def relations(self):
        """Return the relation instances for applications related to us on the monitored relation."""
        return self._charm_relation_mapping.get(self._relation_name, ())

    def get_data(self) -> Optional[BaseModel]:
        """Return data for at most one related application, raising if more than one is available.

        Useful for charms that always expect exactly one related application.  It is recommended that those charms also
        set limit=1 for that relation in charmcraft.yaml.  Returns None if no data is available (either because no
        applications are related to us, or because the related application has not sent data).
        """
        relations = self.relations
        if len(relations) == 0:
            return None
        if len(relations) > 1:
            # TODO: Different exception type?
            raise ValueError("Cannot get_info when more than one application is related.")

        raw_data_dict = relations[0].data.get(relations[0].app)
        if not raw_data_dict:
            return None

        # Static analysis errors saying the keys may not be strings.  Protect against this by converting them.
        raw_data_dict = {str(k): v for k, v in raw_data_dict.items()}

        return GrafanaMetadataAppData.model_validate_json(json.dumps(raw_data_dict))  # type: ignore


class GrafanaMetadataProvider:
    """The provider side of the grafana-metadata relation."""

    def __init__(
        self,
        relations: RelationMapping,
        app: Application,
        grafana_uid: str,
        direct_url: AnyHttpUrl,
        ingress_url: Optional[AnyHttpUrl] = None,
        relation_name: str = GRAFANA_METADATA_RELATION_NAME,
    ):
        """Initialize the GrafanaMetadataProvider object.

        This object is for serializing and sending data to a relation that uses the grafana-metadata interface - it does
        not automatically observe any events for that relation.  It is up to the charm using this to call publish when
        it is appropriate to do so, typically on at least the charm's leader_elected event and this relation's
        relation_joined event.

        Args:
            relations: The RelationMapping of a charm (typically `self.model.relations` from within a charm object).
            app: This application.
            grafana_uid: The UID of this Grafana instance.
            direct_url: The cluster-internal URL at which this application can be reached.  Typically, this is a
                        Kubernetes FQDN like name.namespace.svc.cluster.local for connecting to the prometheus api
                        from inside the cluster, with scheme.
            ingress_url: The non-internal URL at which this application can be reached.  Typically, this is an ingress
                         URL.
            relation_name: The name of the relation.
        """
        self._charm_relation_mapping = relations
        self._data = GrafanaMetadataAppData(ingress_url=ingress_url, direct_url=direct_url, grafana_uid=grafana_uid)
        self._app = app
        self._relation_name = relation_name

    @property
    def relations(self):
        """Return the applications related to us under the monitored relation."""
        return self._charm_relation_mapping.get(self._relation_name, ())

    def publish(self):
        """Post grafana-metadata to all related applications.

        This method writes to the relation's app data bag, and thus should never be called by a unit that is not the
        leader otherwise ops will raise an exception.
        """
        info_relations = self.relations
        for relation in info_relations:
            databag= relation.data[self._app]
            databag.update(self._data.model_dump(mode="json", by_alias=True, exclude_defaults=True, round_trip=True))
