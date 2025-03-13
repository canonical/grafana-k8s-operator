from contextlib import ExitStack
from unittest.mock import patch

import pytest
from ops.testing import Context

from charm import GrafanaCharm


GRAFANA_FQDN = "grafana-k8s-0.testmodel.svc.cluster.local"

def tautology(*_, **__) -> bool:
    return True


@pytest.fixture
def ctx():
    patches = (
        patch.multiple(
            "charm.KubernetesComputeResourcesPatch",
            _namespace="test-namespace",
            _patch=tautology,
            is_ready=tautology,
        ),
        patch("charm.GrafanaCharm._push_sqlite_static", new=lambda _: None),
        patch("lightkube.core.client.GenericSyncClient"),
        patch("socket.getfqdn", new=lambda *args: GRAFANA_FQDN),
        patch("socket.gethostbyname", new=lambda *args: "1.2.3.4"),
        patch.object(GrafanaCharm, "grafana_version", "0.1.0")
    )
    with ExitStack() as stack:
        for context in patches:
            stack.enter_context(context)
        yield Context(GrafanaCharm)
