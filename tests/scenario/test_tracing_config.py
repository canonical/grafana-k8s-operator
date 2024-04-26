import json

import pytest
import scenario

from charm import CONFIG_PATH, DATABASE_PATH


@pytest.fixture
def grafana_container():
    return scenario.Container(
        "grafana",
        can_connect=True,
        exec_mock={
            (
                "/usr/local/bin/sqlite3",
                DATABASE_PATH,
                "pragma journal_mode=wal;",
            ): scenario.ExecOutput()
        },
    )


def test_tracing_config_no_tracing_relation(ctx, grafana_container):
    state = scenario.State(
        containers=[grafana_container], relations=[scenario.PeerRelation("grafana")]
    )
    with ctx.manager(grafana_container.pebble_ready_event, state) as mgr:
        charm = mgr.charm
        assert charm._generate_tracing_config() == ""
        assert "tracing" not in charm._generate_grafana_config()


def test_tracing_v2_request(ctx, grafana_container):
    tracing_relation = scenario.Relation("tracing")
    state = scenario.State(
        leader=True, containers=[grafana_container], relations=[tracing_relation]
    )
    state_out = ctx.run(tracing_relation.joined_event, state)
    tracing_relation_out = state_out.get_relations("tracing")[0]
    requested = tracing_relation_out.local_app_data["receivers"]
    assert "otlp_http" in requested
    assert "jaeger_thrift_http" in requested


def test_tracing_config_no_receivers(ctx, grafana_container):
    tracing_relation = scenario.Relation(
        "tracing",
        remote_app_data={
            "host": '"remotefqdn.local.foo"',
        },
    )
    state = scenario.State(
        leader=True,
        containers=[grafana_container],
        relations=[tracing_relation, scenario.PeerRelation("grafana")],
    )

    ctx.run(grafana_container.pebble_ready_event, state)

    fs = grafana_container.get_filesystem(ctx)
    config = fs.joinpath(*CONFIG_PATH.split("/")).read_text()

    assert "[tracing.opentelemetry]" not in config
    assert config == """[database]\ntype = sqlite3\npath = /var/lib/grafana/grafana.db\n\n"""


def test_tracing_config_with_receiver(ctx, grafana_container):
    tracing_relation = scenario.Relation(
        "tracing",
        local_app_data={"receivers": json.dumps(["jaeger_thrift_http"])},
        remote_app_data={
            "host": '"remotefqdn.local.foo"',
            "receivers": json.dumps(
                [{"protocol": "jaeger_thrift_http", "port": 42, "path": "/foo/bar"}]
            ),
        },
    )

    state = scenario.State(
        leader=True,
        containers=[grafana_container],
        relations=[tracing_relation, scenario.PeerRelation("grafana")],
    )

    ctx.run(grafana_container.pebble_ready_event, state)

    fs = grafana_container.get_filesystem(ctx)
    config = fs.joinpath(*CONFIG_PATH.split("/")).read_text()

    assert "[tracing.opentelemetry]" in config
    assert "address = http://remotefqdn.local.foo:42/foo/bar/api/traces" in config


def test_tracing_config_with_receiver_and_ingress(ctx, grafana_container):
    tracing_relation = scenario.Relation(
        "tracing",
        local_app_data={"receivers": json.dumps(["jaeger_thrift_http"])},
        remote_app_data={
            "host": '"remotefqdn.local.foo"',
            "external_url": '"https://example.com"',
            "receivers": json.dumps(
                [{"protocol": "jaeger_thrift_http", "port": 42, "path": "/foo/bar"}]
            ),
        },
    )

    state = scenario.State(
        leader=True,
        containers=[grafana_container],
        relations=[tracing_relation, scenario.PeerRelation("grafana")],
    )

    ctx.run(grafana_container.pebble_ready_event, state)

    fs = grafana_container.get_filesystem(ctx)
    config = fs.joinpath(*CONFIG_PATH.split("/")).read_text()

    assert "address = https://example.com/foo/bar/api/traces" in config
