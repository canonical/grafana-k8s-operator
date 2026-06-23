#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for custom_ini_config module."""

from unittest.mock import MagicMock

from ops import BlockedStatus, ActiveStatus
import pytest
from src.custom_ini_config import resolve_secrets, validate
from src.grafana_config import GrafanaConfig


def test_validate_without_args():
    # WHEN validate called without args
    r1 = validate()
    r2 = validate(None)

    # THEN returns None
    assert r1 is None
    assert r2 is None


def test_validate_with_invalid_string():
    # GIVEN string without sections
    ini = "hello"

    # WHEN validate called
    # THEN ValueError is raised
    with pytest.raises(ValueError, match="Invalid ini sections"):
        validate(ini)


def test_validate_with_invalid_section():
    # GIVEN valid ini but invalid schema
    ini = """[section]
    key = value
    """

    # WHEN validate called with
    # THEN ValueError is raised.
    with pytest.raises(ValueError, match="unallowed sections"):
        validate(ini)


def test_validate_with_valid_smtp_section():
    # GIVEN a valid ini with valid schema
    ini = """[smtp]
    enabled = true"""

    # WHEN validate called
    # THEN returns None
    assert validate(ini) is None


def test_validate_with_invalid_smtp_key():
    # GIVEN a valid ini with the correct schema but also with some unexpected extras
    ini = """[smtp]
    enabled = true
    surprise = wow
    """

    # WHEN validate called
    # THEN ValueError is raised.
    with pytest.raises(ValueError, match="Invalid \\[smtp\\] section"):
        validate("[smtp]\nenabled = true\ninvalid = value")
        validate(ini)


def test_resolve_secrets_without_args():
    # WHEN resolve_secrets called without args
    r1 = resolve_secrets(None, lambda _: "x")

    # THEN returns None
    assert r1 is None


def test_resolve_secrets_with_no_secret_urls():
    # GIVEN an ini without secret URLs
    ini = "[smtp]\nenabled = true"

    # WHEN resolve_secrets is called
    result = resolve_secrets(ini, lambda _: pytest.fail("should not be called"))

    # THEN the original string is returned unchanged
    assert result == ini


def test_resolve_secrets_with_secret_url():
    # GIVEN an ini with a secret URL
    ini = "[smtp]\npassword = secret://abc123/password"

    def getter(url: str) -> str:
        assert url == "secret://abc123/password"
        return "super-secret"

    # WHEN resolve_secrets is called
    result = resolve_secrets(ini, getter)

    # THEN the secret URL is replaced with the resolved value
    assert result is not None
    assert "password = super-secret" in result
    assert "secret://" not in result


def test_resolve_secrets_with_multiple_secret_urls():
    # GIVEN an ini with multiple secret URLs
    ini = """[smtp]
user = secret://abc123/user
password = secret://abc123/password"""

    secrets = {
        "secret://abc123/user": "grafana",
        "secret://abc123/password": "super-secret",
    }

    # WHEN resolve_secrets is called
    result = resolve_secrets(ini, secrets.get)

    # THEN both secret URLs are replaced
    assert result is not None
    assert "user = grafana" in result
    assert "password = super-secret" in result


def test_resolve_secrets_missing_secret():
    # GIVEN an ini with a secret URL that cannot be resolved
    ini = "[smtp]\npassword = secret://abc123/password"

    def getter(_: str) -> None:
        return None

    # WHEN resolve_secrets is called
    # THEN a ValueError is raised
    with pytest.raises(ValueError, match="Could not resolve secret URL"):
        resolve_secrets(ini, getter)


def test_resolve_secrets_getter_raises():
    # GIVEN an ini with a secret URL and a getter that raises
    ini = "[smtp]\npassword = secret://abc123/password"

    def getter(_: str):
        raise RuntimeError("boom")

    # WHEN resolve_secrets is called
    # THEN the error is wrapped in a ValueError
    with pytest.raises(ValueError, match="Failed to resolve secrets"):
        resolve_secrets(ini, getter)


def test_grafana_config_status_with_valid_secret():
    # GIVEN a valid custom_config with a secret URL
    custom_config = "[smtp]\npassword = secret://abc123/password"

    def getter(url: str) -> str:
        assert url == "secret://abc123/password"
        return "super-secret"

    config = GrafanaConfig(
        datasources_config=MagicMock(),
        custom_config=custom_config,
        secret_getter=getter,
    )

    # WHEN get_status is called
    status = config.get_status()

    # THEN the status is active
    assert isinstance(status, ActiveStatus)


def test_grafana_config_status_with_invalid_secret():
    # GIVEN a custom_config with an invalid secret URL
    custom_config = "[smtp]\npassword = secret://bad-url"

    config = GrafanaConfig(
        datasources_config=MagicMock(),
        custom_config=custom_config,
        secret_getter=lambda _: None,
    )

    # WHEN get_status is called
    status = config.get_status()

    # THEN the status is blocked
    assert isinstance(status, BlockedStatus)


def test_grafana_config_status_with_missing_secret():
    # GIVEN a custom_config with a secret URL that cannot be resolved
    custom_config = "[smtp]\npassword = secret://abc123/password"

    config = GrafanaConfig(
        datasources_config=MagicMock(),
        custom_config=custom_config,
        secret_getter=lambda _: None,
    )

    # WHEN get_status is called
    status = config.get_status()

    # THEN the status is blocked
    assert isinstance(status, BlockedStatus)


def test_grafana_config_generates_config_with_resolved_secret():
    # GIVEN a custom_config with a secret URL
    custom_config = "[smtp]\npassword = secret://abc123/password"

    def getter(url: str) -> str:
        assert url == "secret://abc123/password"
        return "super-secret"

    config = GrafanaConfig(
        datasources_config=MagicMock(),
        custom_config=custom_config,
        secret_getter=getter,
    )

    # WHEN generate_grafana_config is called
    generated = config.generate_grafana_config()

    # THEN the secret is resolved in the generated config
    assert "password = super-secret" in generated
    assert "secret://" not in generated
