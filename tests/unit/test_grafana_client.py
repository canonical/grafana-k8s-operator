# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import json
from unittest.mock import patch
import urllib3

@patch("src.grafana.urllib3.PoolManager.request")
def test_grafana_client_returns_valid_data(request, ctx, base_state):
    # GIVEN a mocked http request
    version = "7.2.1"
    request.return_value.data = bytes(
        json.dumps(
            {
                "commit": "12345abcd",
                "database": "ok",
                "version": version,
            }
        ),
        encoding="utf-8",
    )
    # WHEN any event is fired
    with ctx(ctx.on.update_status(), base_state) as mgr:
        mgr.run()
        charm = mgr.charm
        build_info = charm._grafana_service.build_info
        got_version = build_info.get("version", None)
        # THEN assert version is the same as we mocked
        assert got_version
        assert got_version == version


@patch("src.grafana.urllib3.PoolManager.request")
def test_grafana_client_max_retry_test(request, ctx, base_state):
    # Ignore mypy here so we don't have to mock out absolutely everything
    request.side_effect = urllib3.exceptions.MaxRetryError(None, "/", "We shouldn't get here")  # type: ignore
    # WHEN any event is fired
    with ctx(ctx.on.update_status(), base_state) as mgr:
        mgr.run()
        charm = mgr.charm
        build_info = charm._grafana_service.build_info
        # THEN assert build info is empty
        assert build_info == {}


@patch("src.grafana.urllib3.PoolManager.request")
def test_grafana_client_becomes_ready(request, ctx, base_state):
    version = "7.2.1"
    request.return_value.data = bytes(
        json.dumps(
            {
                "commit": "12345abcd",
                "database": "ok",
                "version": version,
            }
        ),
        encoding="utf-8",
    )
    # WHEN any event is fired
    with ctx(ctx.on.update_status(), base_state) as mgr:
        mgr.run()
        charm = mgr.charm
        is_ready = charm._grafana_service.is_ready
        # THEN is_ready is True
        assert is_ready

@patch("src.grafana.urllib3.PoolManager.request")
def test_grafana_client_is_unready(request, ctx, base_state):
    request.return_value.data = bytes(
        json.dumps(
            {
                "database": "fail",
            }
        ),
        encoding="utf-8",
    )
    # WHEN any event is fired
    with ctx(ctx.on.update_status(), base_state) as mgr:
        mgr.run()
        charm = mgr.charm
        is_ready = charm._grafana_service.is_ready
        # THEN is_ready is False
        assert is_ready is not None
        assert not is_ready

