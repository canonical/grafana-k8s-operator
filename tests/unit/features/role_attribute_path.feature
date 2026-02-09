Feature: Role Attribute Path Generation
  As a Grafana operator
  I want to generate role attribute paths based on OAuth group claims
  So that users can be assigned appropriate roles based on their group memberships

  Scenario: No roles configured
    Given a GrafanaConfig with admin roles "", and editor roles ""
    Then the role attribute path should be None

  Scenario: Only admin roles configured
    Given a GrafanaConfig with admin roles "admin-group,superadmin", and editor roles ""
    Then the role attribute path should contain "contains(groups[*], admin-group) && 'Admin'"
    And the role attribute path should contain "contains(groups[*], superadmin) && 'Admin'"
    And the role attribute path should contain "'Viewer'"
    And the role attribute path should be separated by " || ", comprising of 3 items

  Scenario: Only editor roles configured
    Given a GrafanaConfig with admin roles "", and editor roles "editor-group,dev-team"
    Then the role attribute path should contain "contains(groups[*], editor-group) && 'Editor'"
    And the role attribute path should contain "contains(groups[*], dev-team) && 'Editor'"
    And the role attribute path should contain "'Viewer'"
    And the role attribute path should be separated by " || ", comprising of 3 items

  Scenario: Both admin and editor roles configured
    Given a GrafanaConfig with admin roles "admin-group", and editor roles "editor-group"
    Then the role attribute path should contain "contains(groups[*], admin-group) && 'Admin'"
    And the role attribute path should contain "contains(groups[*], editor-group) && 'Editor'"
    And the role attribute path should contain "'Viewer'"
    And the role attribute path should be separated by " || ", comprising of 3 items

  Scenario: Multiple admin and editor roles
    Given a GrafanaConfig with admin roles "admin-1,admin-2", and editor roles "editor-1,editor-2,editor-3"
    Then the role attribute path should contain "contains(groups[*], admin-1) && 'Admin'"
    And the role attribute path should contain "contains(groups[*], admin-2) && 'Admin'"
    And the role attribute path should contain "contains(groups[*], editor-1) && 'Editor'"
    And the role attribute path should contain "contains(groups[*], editor-2) && 'Editor'"
    And the role attribute path should contain "contains(groups[*], editor-3) && 'Editor'"
    And the role attribute path should contain "'Viewer'"
    And the role attribute path should be separated by " || ", comprising of 6 items
