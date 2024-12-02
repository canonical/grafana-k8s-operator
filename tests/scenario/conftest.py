from contextlib import ExitStack
from unittest.mock import patch

import pytest
from ops.testing import Context

from charm import GrafanaCharm


@pytest.fixture
def ctx():
    with ExitStack() as stack:
        stack.enter_context(patch("charm.GrafanaCharm._push_sqlite_static", new=lambda _: None))
        stack.enter_context(patch("lightkube.core.client.GenericSyncClient"))
        stack.enter_context(
            patch("socket.getfqdn", new=lambda *args: "grafana-k8s-0.testmodel.svc.cluster.local")
        )
        stack.enter_context(patch("socket.gethostbyname", new=lambda *args: "1.2.3.4"))
        stack.enter_context(
            patch.multiple(
                "charm.KubernetesComputeResourcesPatch",
                _namespace="test-namespace",
                _patch=lambda *_a, **_k: True,
                is_ready=lambda *_a, **_k: True,
            )
        )
        stack.enter_context(patch.object(GrafanaCharm, "grafana_version", "0.1.0"))
        yield Context(GrafanaCharm)
