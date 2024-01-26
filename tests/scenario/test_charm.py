import pytest
from scenario import State, PeerRelation


@pytest.mark.parametrize("leader", (True, False))
def test_peer_data_does_not_raise_if_no_peers(ctx, leader):
    state = State(leader=leader)
    with ctx.manager("update-status", state) as mgr:
        charm = mgr.charm
        assert not charm.peers
        charm.set_peer_data("1", 2)
        assert charm.get_peer_data("1") == {}


def test_peer_data_if_peers(ctx):
    state = State(leader=True, relations=[PeerRelation("grafana")])
    with ctx.manager("update-status", state) as mgr:
        charm = mgr.charm
        assert charm.peers
        charm.set_peer_data("1", 2)
        assert charm.get_peer_data("1") == 2
