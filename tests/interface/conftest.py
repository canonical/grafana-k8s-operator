from contextlib import ExitStack
from unittest.mock import patch

import pytest
from scenario import State, Container

from charm import GrafanaCharm


GRAFANA_FQDN = "grafana-k8s-0.testmodel.svc.cluster.local"

def tautology(*_, **__) -> bool:
    return True


@pytest.fixture
def containers():
    """Mocks for standard containers grafana needs to work."""
    return [
        Container(name="grafana", can_connect=True),
        Container(name="litestream", can_connect=True),
    ]


@pytest.fixture(autouse=True, scope="module")
def apply_all_patches():
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
