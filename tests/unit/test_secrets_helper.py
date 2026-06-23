#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the secrets_helper module."""

from unittest.mock import MagicMock

import pytest
from ops.model import ModelError, SecretNotFoundError

from src.secrets_helper import SecretError, SecretGetter


@pytest.fixture
def model():
    return MagicMock()


@pytest.fixture
def getter(model):
    return SecretGetter(model)


def test_get_value_empty_url(getter):
    # GIVEN an empty secret URL
    # WHEN get_value is called
    result = getter.get_value("")

    # THEN returns None
    assert result is None


def test_get_value_valid_url(getter, model):
    # GIVEN a valid secret URL
    url = "secret://abc123/password"
    secret_mock = MagicMock()
    secret_mock.get_content.return_value = {"password": "super-secret"}
    model.get_secret.return_value = secret_mock

    # WHEN get_value is called
    result = getter.get_value(url)

    # THEN the secret value is returned
    assert result == "super-secret"
    model.get_secret.assert_called_once_with(id="abc123")
    secret_mock.get_content.assert_called_once_with(refresh=True)


def test_get_value_missing_key(getter, model):
    # GIVEN a valid secret URL but the key is missing from the secret
    url = "secret://abc123/password"
    secret_mock = MagicMock()
    secret_mock.get_content.return_value = {"other": "value"}
    model.get_secret.return_value = secret_mock

    # WHEN get_value is called
    # THEN a SecretError is raised
    with pytest.raises(SecretError, match="Secret not found"):
        getter.get_value(url)


@pytest.mark.parametrize(
    "url",
    [
        "not-a-secret",
        "secret://",
        "secret://abc123",
        "secret://abc123/extra/path",
        "http://abc123/password",
    ],
)
def test_get_value_invalid_url(getter, url):
    # GIVEN an invalid secret URL
    # WHEN get_value is called
    # THEN a SecretError is raised
    with pytest.raises(SecretError, match="Invalid secret URL"):
        getter.get_value(url)


def test_get_value_secret_not_found(getter, model):
    # GIVEN a secret that does not exist
    url = "secret://abc123/password"
    model.get_secret.side_effect = SecretNotFoundError("not found")

    # WHEN get_value is called
    # THEN a SecretError is raised
    with pytest.raises(SecretError, match="Secret not found"):
        getter.get_value(url)


def test_get_value_model_error(getter, model):
    # GIVEN a secret that the charm cannot access
    url = "secret://abc123/password"
    model.get_secret.side_effect = ModelError("permission denied")

    # WHEN get_value is called
    # THEN a SecretError is raised with a permissions message
    with pytest.raises(SecretError, match="missing charm permissions"):
        getter.get_value(url)


def test_get_value_unexpected_error(getter, model):
    # GIVEN an unexpected error from get_secret
    url = "secret://abc123/password"
    model.get_secret.side_effect = RuntimeError("boom")

    # WHEN get_value is called
    # THEN a SecretError is raised
    with pytest.raises(SecretError, match="Unexpected error fetching secret"):
        getter.get_value(url)


def test_get_value_get_content_raises(getter, model):
    # GIVEN an unexpected error from get_content
    url = "secret://abc123/password"
    secret_mock = MagicMock()
    secret_mock.get_content.side_effect = RuntimeError("boom")
    model.get_secret.return_value = secret_mock

    # WHEN get_value is called
    # THEN a SecretError is raised
    with pytest.raises(SecretError, match="Unexpected error fetching secret"):
        getter.get_value(url)
