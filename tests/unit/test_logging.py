# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the logging (LogForwarder) integration."""

from dataclasses import replace

from ops.testing import Context, Relation


def test_charm_initializes_with_logging_relation(ctx: Context, base_state):
    """The charm should initialize without errors when a logging relation is present."""
    # GIVEN a logging relation
    logging_relation = Relation("logging")
    state = replace(base_state, relations=base_state.relations | {logging_relation})

    # WHEN a relation-changed event fires on the logging relation
    with ctx(ctx.on.relation_changed(logging_relation), state) as mgr:
        mgr.run()

    # THEN no exceptions are raised (charm handles the relation gracefully)


def test_charm_starts_without_logging_relation(ctx: Context, base_state):
    """The charm should start fine without the optional logging relation."""
    # GIVEN no logging relation (base_state has only peer relation)
    # WHEN an install event fires
    with ctx(ctx.on.install(), base_state) as mgr:
        mgr.run()

    # THEN no exceptions are raised
