# Copyright 2026 Canonical
# See LICENSE file for licensing details.

from unittest.mock import Mock
from pytest_bdd import scenarios, given, then, parsers
from grafana_config import GrafanaConfig


# Load all scenarios from the feature file
scenarios('features/role_attribute_path.feature')


def config_factory(admin_roles=None, editor_roles=None):
    """Factory function to create GrafanaConfig with specified roles."""
    return GrafanaConfig(
        datasources_config=Mock(),
        admin_roles=admin_roles or [],
        editor_roles=editor_roles or []
    )


def csv_to_list(roles: str) -> list[str]:
    return [role.strip() for role in roles.split(',') if role.strip()]


@given(parsers.re(r'a GrafanaConfig with admin roles "(?P<admin_roles>.*)", and editor roles "(?P<editor_roles>.*)"'), target_fixture="grafana_config")
def grafana_config_with_roles(admin_roles, editor_roles):
    """Create GrafanaConfig with specified admin and editor roles."""
    return config_factory(admin_roles=csv_to_list(admin_roles), editor_roles=csv_to_list(editor_roles))


@then("the role attribute path should be None")
def role_attribute_path_is_none(grafana_config):
    """Verify the role_attribute_path is None."""
    assert grafana_config.role_attribute_path is None


@then(parsers.parse('the role attribute path should contain "{expected_substring}"'))
def role_attribute_path_contains(grafana_config, expected_substring):
    """Verify the role_attribute_path contains the expected substring."""
    result = grafana_config.role_attribute_path
    assert result is not None, "Result should not be None"
    assert expected_substring in result, \
        f"Expected '{expected_substring}' in result, but got: {result}"


@then(parsers.parse('the role attribute path should be separated by "{separator}", comprising of {count:d} items'))
def role_attribute_path_uses_separator(grafana_config, separator, count):
    """Verify the role_attribute_path uses the expected separator."""
    result = grafana_config.role_attribute_path
    assert result is not None, "Result should not be None"
    assert len(result.split(separator)) == count, \
        f"Expected {count} items separated by '{separator}', but got: {result}"
