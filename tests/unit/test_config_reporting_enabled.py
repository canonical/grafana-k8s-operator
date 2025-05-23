from dataclasses import replace
from configparser import ConfigParser


def test_reporting_enabled(ctx, base_state):
    # GIVEN the "reporting_enabled" config option is set to True
    state = replace(base_state, config={"reporting_enabled": True})

    # WHEN config-changed fires
    out = ctx.run(ctx.on.config_changed(), state)

    # THEN the config file is written WITHOUT the [analytics] section being rendered
    simulated_pebble_filesystem = out.get_container("grafana").get_filesystem(ctx)
    grafana_config_path = simulated_pebble_filesystem / "etc/grafana/grafana-config.ini"

    config = ConfigParser()
    config.read(grafana_config_path)
    assert "analytics" not in config


def test_reporting_disabled(ctx, base_state):
    # GIVEN the "reporting_enabled" config option is set to False
    state = replace(base_state, config={"reporting_enabled": False})

    # WHEN config-changed fires
    out = ctx.run(ctx.on.config_changed(), state)

    # THEN the config file is written WITH the [analytics] section being rendered
    simulated_pebble_filesystem = out.get_container("grafana").get_filesystem(ctx)
    grafana_config_path = simulated_pebble_filesystem / "etc/grafana/grafana-config.ini"

    config = ConfigParser()
    config.read(grafana_config_path)
    assert "analytics" in config
    assert dict(config["analytics"]) == {
        "reporting_enabled": "false",
        "check_for_updates": "false",
        "check_for_plugin_updates": "false",
    }

    # AND the "grafana" service is restarted
    # TODO Does it make sense to check this if the charm under test's lifetime is only for the config-changed?
    # TODO How to assert this?
