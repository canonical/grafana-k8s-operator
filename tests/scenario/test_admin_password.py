import re
from contextlib import ExitStack, contextmanager
from unittest.mock import patch, PropertyMock

import pytest
from ops import testing

from charm import GrafanaCharm, generate_password


@contextmanager
def grafana_ready(ready: bool):
    with patch("grafana_client.Grafana.is_ready", PropertyMock(return_value=ready)):
        yield


@contextmanager
def password_changed(changed: bool):
    with patch("grafana_client.Grafana.password_has_been_changed", return_value=changed):
        yield


@pytest.fixture(autouse=True)
def patch_all():
    with ExitStack() as stack:
        for p in [
            patch("lightkube.core.client.GenericSyncClient"),
            patch("socket.getfqdn", new=lambda *args: "grafana-k8s-0.testmodel.svc.cluster.local"),
            patch("socket.gethostbyname", new=lambda *args: "1.2.3.4"),
            patch.multiple(
                "charm.KubernetesComputeResourcesPatch",
                _namespace="test-namespace",
                _patch=lambda *a, **kw: True,
                is_ready=lambda *a, **kw: True,
            ),
            patch.object(GrafanaCharm, "grafana_version", "0.1.0"),
        ]:
            stack.enter_context(p)

        yield


@pytest.fixture
def ctx():
    return testing.Context(GrafanaCharm)


def test_generate_password():
    # run this test some 1000 times since generate_password is stochastic
    for n in range(1000):
        pwd = generate_password()
        assert len(pwd) == 12
        assert re.match(r"[A-Za-z0-9]{12}", pwd)


def test_can_get_password(ctx):
    # GIVEN a grafana leader unit
    state = testing.State(leader=True)

    # WHEN we receive any hook
    with ctx(ctx.on.update_status(), state) as mgr:
        # THEN the .admin_password attribute returns something
        pwd = mgr.charm.admin_password
        state_out = mgr.run()

    # AND THEN the output state contains a secret with the expected contents
    assert len(state_out.secrets) == 1
    secret = list(state_out.secrets)[0]
    assert pwd, "password is empty"
    assert secret.latest_content["password"] == pwd


@pytest.mark.parametrize("leader", (True, False))
def test_action_happy_path(ctx, leader):
    # GIVEN a grafana unit with the secret created already
    pwd = "abcde"
    state = testing.State(
        leader=leader,
        secrets={testing.Secret(tracked_content={"password": pwd}, label="admin-password")},
    )

    # WHEN we run the get-admin-password action
    with grafana_ready(True):
        with password_changed(False):
            ctx.run(ctx.on.action("get-admin-password"), state)

    # THEN the secret's password matches the pre-existing password
    assert ctx.action_results["admin-password"] == pwd


def test_action_no_secret_yet_follower(ctx):
    # GIVEN a non-leader grafana unit
    state = testing.State()

    # WHEN we run the get-admin-password action
    with password_changed(False):
        with grafana_ready(True):
            with pytest.raises(testing.ActionFailed) as failure:
                ctx.run(ctx.on.action("get-admin-password"), state)

    # THEN the action fails with this message
    assert failure.value.message == GrafanaCharm.GetAdminPWDFailures.waiting_for_leader


@pytest.mark.parametrize("leader", (True, False))
def test_action_grafana_down(ctx, leader):
    # GIVEN a grafana unit, leader or not, with the secret ready
    pwd = "abcde"
    state = testing.State(
        leader=leader,
        secrets={testing.Secret(tracked_content={"password": pwd}, label="admin-password")},
    )

    # AND GIVEN grafana is not ready
    # WHEN we run the get-admin-password action
    with grafana_ready(False):
        with pytest.raises(testing.ActionFailed) as failure:
            ctx.run(ctx.on.action("get-admin-password"), state)

    # THEN the action fails with this message
    assert failure.value.message == GrafanaCharm.GetAdminPWDFailures.not_reachable


@pytest.mark.parametrize("leader", (True, False))
def test_action_password_changed(ctx, leader):
    # GIVEN a grafana unit with the secret created already
    pwd = "abcde"
    state = testing.State(
        leader=leader,
        secrets={testing.Secret(tracked_content={"password": pwd}, label="admin-password")},
    )

    # AND GIVEN the admin password was changed behind the scenes
    # WHEN we run the get-admin-password action
    with password_changed(True):
        with grafana_ready(True):
            ctx.run(ctx.on.action("get-admin-password"), state)

    # THEN we obtain an error message
    if leader:
        assert (
            ctx.action_results["admin-password"]
            == GrafanaCharm.GetAdminPWDFailures.changed_by_admin
        )
    else:
        assert (
            ctx.action_results["admin-password"]
            == GrafanaCharm.GetAdminPWDFailures.perhaps_changed_by_admin
        )
