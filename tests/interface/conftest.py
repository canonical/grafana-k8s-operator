from contextlib import ExitStack
from unittest.mock import patch

import pytest
from scenario import State, Container

from charm import GrafanaCharm


@pytest.fixture
def containers():
    """Mocks for standard containers grafana needs to work."""
    return [
        Container(name="grafana", can_connect=True),
        Container(name="litestream", can_connect=True),
    ]


@pytest.fixture(autouse=True, scope="module")
def patches():
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
        yield


@pytest.fixture
def grafana_source_tester(interface_tester, containers):
    interface_tester.configure(
        charm_type=GrafanaCharm,
        state_template=State(
            leader=True,
            containers=containers,
        ),
    )
    yield interface_tester
