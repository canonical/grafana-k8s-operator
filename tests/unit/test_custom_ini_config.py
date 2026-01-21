#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for custom_ini_config module."""

import pytest

from src.custom_ini_config import validate


def test_validate_without_args():
    """WHEN validate called without args THEN returns None."""
    result = validate(None)
    assert result is None


def test_validate_with_invalid_string():
    """WHEN validate called with "hello" THEN ValueError is raised."""
    with pytest.raises(ValueError, match="Invalid ini sections"):
        validate("hello")


def test_validate_with_invalid_section():
    """WHEN validate called with "[section]\\nkey = value" THEN ValueError is raised."""
    with pytest.raises(ValueError, match="unallowed sections"):
        validate("[section]\nkey = value")


def test_validate_with_valid_smtp_section():
    """WHEN validate called with "[smtp]\\nenabled = true" THEN returns None."""
    result = validate("[smtp]\nenabled = true")
    assert result is None


def test_validate_with_invalid_smtp_key():
    """WHEN validate called with "[smtp]\\nenabled = true\\n\\invalid = value" THEN ValueError is raised."""
    with pytest.raises(ValueError, match="Invalid \\[smtp\\] section"):
        validate("[smtp]\nenabled = true\ninvalid = value")
