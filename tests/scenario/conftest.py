from unittest.mock import patch

import pytest
from ops.testing import Context

from charm import GrafanaCharm


def tautology(*_, **__) -> bool:
    return True


@pytest.fixture
def ctx():
    patches = (
        patch("charm.GrafanaCharm._push_sqlite_static", new=lambda _: None),
        patch("lightkube.core.client.GenericSyncClient"),
        patch("socket.getfqdn", new=lambda *args: "grafana-k8s-0.testmodel.svc.cluster.local"),
        patch("socket.gethostbyname", new=lambda *args: "1.2.3.4"),
        patch.multiple(
            "charm.KubernetesComputeResourcesPatch",
            _namespace="test-namespace",
            _patch=tautology,
            is_ready=tautology,
        ),
        patch.object(GrafanaCharm, "grafana_version", "0.1.0"),
    )
    for p in patches:
        p.__enter__()

    yield Context(GrafanaCharm)

    for p in patches:
        p.__exit__(None, None, None)
