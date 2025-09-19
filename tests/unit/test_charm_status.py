#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from ops import BlockedStatus, WaitingStatus, ActiveStatus
from ops.testing import Relation, State


@pytest.mark.parametrize("db_relation_data,expected_status,expected_message", [
    (
        # No database relation
        None,
        BlockedStatus,
        "missing database relation"
    ),
    (
        # Incomplete database relation (missing required fields)
        {"type": "mysql"},  # Missing host, name, user, password
        WaitingStatus,
        "waiting for database provider"
    ),
    (
        # Complete database relation
        {
            "type": "mysql",
            "host": "1.1.1.1:3306",
            "name": "mysqldb",
           "user": "grafana",
            "password": "grafana",
        },
        ActiveStatus,
        ""
    ),
])
def test_charm_status_based_on_database_relation(
    ctx, peer_relation, grafana_container, db_relation_data, expected_status, expected_message
):
    """Test that the charm status reflects database relation state correctly.

    Verifies that the charm sets appropriate status based on database relation:
    - BlockedStatus when no database relation exists
    - WaitingStatus when database relation has incomplete data
    - ActiveStatus when database relation has all required fields
    """
    # GIVEN a state with varying database relation configurations
    relations = {peer_relation}

    if db_relation_data is not None:
        db_relation = Relation("database", remote_app_name="mysql", remote_app_data=db_relation_data)
        relations.add(db_relation)

    state = State(
        planned_units=3,
        leader=True,
        containers={grafana_container},
        relations=relations
    )

    # WHEN collect-unit-status event fires
    out = ctx.run(ctx.on.collect_unit_status(), state)

    # THEN the unit status should match expectations
    assert isinstance(out.unit_status, expected_status)
    assert expected_message in out.unit_status.message
