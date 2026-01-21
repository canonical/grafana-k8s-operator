#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for custom_ini_config module."""

import pytest

from src.custom_ini_config import validate


def test_validate_without_args():
    # WHEN validate called without
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
    # THEN ValueError is raised."""
    with pytest.raises(ValueError, match="Invalid \\[smtp\\] section"):
        validate("[smtp]\nenabled = true\ninvalid = value")
        validate(ini)
