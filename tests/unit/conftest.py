from unittest.mock import MagicMock, patch

from ops import ActiveStatus
from ops.testing import PeerRelation, Container, State, Exec
from charms.tempo_coordinator_k8s.v0.charm_tracing import charm_tracing_disabled

import pytest
from ops.testing import Context

from charm import GrafanaCharm
from grafana import Grafana


GRAFANA_FQDN = "grafana-k8s-0.testmodel.svc.cluster.local"


def tautology(*_, **__) -> bool:
    return True


@pytest.fixture(autouse=True, scope="session")
def disable_charm_tracing():
    with charm_tracing_disabled():
        yield


@pytest.fixture
def ctx():
    patches = (
        patch("grafana.Grafana._push_sqlite_static", new=lambda _: None),
        patch("lightkube.core.client.GenericSyncClient"),
        patch("socket.getfqdn", new=lambda *args: GRAFANA_FQDN),
        patch("socket.gethostbyname", new=lambda *args: "1.2.3.4"),
        patch.multiple(
            "charm.KubernetesComputeResourcesPatch",
            _namespace="test-namespace",
            _patch=tautology,
            get_status=MagicMock(return_value=ActiveStatus()),
            is_ready=tautology,
        ),
        patch.object(Grafana, "grafana_version", "0.1.0"),
    )
    for p in patches:
        p.__enter__()

    yield Context(GrafanaCharm)

    for p in patches:
        p.__exit__(None, None, None)


@pytest.fixture
def peer_relation():
    return PeerRelation("grafana")


@pytest.fixture(scope="function")
def grafana_container():
    return Container(
        "grafana", can_connect=True, execs={Exec(("update-ca-certificates", "--fresh"))}
    )


@pytest.fixture(scope="function")
def litestream_container():
    return Container(
        "litestream",
        can_connect=True,
    )


@pytest.fixture
def containers(grafana_container, litestream_container):
    return {grafana_container, litestream_container}


@pytest.fixture
def base_state(containers, peer_relation):
    return State(
        leader=True,
        containers=containers,
        relations={peer_relation},
    )
