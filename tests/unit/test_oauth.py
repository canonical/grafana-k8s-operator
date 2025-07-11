# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

from dataclasses import replace
from ops.testing import Relation, Secret

OAUTH_CLIENT_ID = "grafana_client_id"
OAUTH_CLIENT_SECRET = "s3cR#T"
OAUTH_PROVIDER_INFO = {
    "authorization_endpoint": "https://example.oidc.com/oauth2/auth",
    "introspection_endpoint": "https://example.oidc.com/admin/oauth2/introspect",
    "issuer_url": "https://example.oidc.com",
    "jwks_endpoint": "https://example.oidc.com/.well-known/jwks.json",
    "scope": "openid profile email phone",
    "token_endpoint": "https://example.oidc.com/oauth2/token",
    "userinfo_endpoint": "https://example.oidc.com/userinfo",
}


def test_config_is_updated_with_oauth_relation_data(ctx, base_state, peer_relation):
    # GIVEN an oauth relation AND an oauth secret
    oauth_secret = Secret({"secret": OAUTH_CLIENT_SECRET})
    oauth_rel = Relation(
        "oauth",
        remote_app_name="hydra",
        remote_app_data={
            "client_id": OAUTH_CLIENT_ID,
            "client_secret_id": oauth_secret.id,
            **OAUTH_PROVIDER_INFO,
        },
    )
    state = replace(base_state, relations={peer_relation, oauth_rel}, secrets={oauth_secret})

    # WHEN a relation_changed event fires
    with ctx(ctx.on.relation_changed(oauth_rel), state) as mgr:
        mgr.run()
        charm = mgr.charm
        # THEN we get oauth env vars set in the workload pebble layer
        services = charm.unit.get_container("grafana").get_plan().services["grafana"].to_dict()
        env = services["environment"]  # type: ignore
        expected_env = {
            "GF_AUTH_GENERIC_OAUTH_ENABLED": "True",
            "GF_AUTH_GENERIC_OAUTH_NAME": "external identity provider",
            "GF_AUTH_GENERIC_OAUTH_CLIENT_ID": OAUTH_CLIENT_ID,
            "GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET": OAUTH_CLIENT_SECRET,
            "GF_AUTH_GENERIC_OAUTH_SCOPES": "openid email offline_access",
            "GF_AUTH_GENERIC_OAUTH_AUTH_URL": OAUTH_PROVIDER_INFO["authorization_endpoint"],
            "GF_AUTH_GENERIC_OAUTH_TOKEN_URL": OAUTH_PROVIDER_INFO["token_endpoint"],
            "GF_AUTH_GENERIC_OAUTH_API_URL": OAUTH_PROVIDER_INFO["userinfo_endpoint"],
            "GF_AUTH_GENERIC_OAUTH_USE_REFRESH_TOKEN": "True",
            "GF_FEATURE_TOGGLES_ENABLE": "accessTokenExpirationCheck",
        }
        for k, v in expected_env.items():
            assert env[k] == v


def test_config_with_empty_oauth_relation_data(ctx, base_state, peer_relation):
    # GIVEN an oauth relation with NO app data
    oauth_rel = Relation("oauth", remote_app_name="hydra")
    state = replace(base_state, relations={peer_relation, oauth_rel})
    # WHEN a relation_changed event fires
    with ctx(ctx.on.relation_changed(oauth_rel), state) as mgr:
        mgr.run()
        charm = mgr.charm
        services = charm.unit.get_container("grafana").get_plan().services["grafana"].to_dict()
        # THEN we get no oauth env vars
        env = services["environment"]  # type: ignore
        oauth_env = {
            "GF_AUTH_GENERIC_OAUTH_ENABLED",
            "GF_AUTH_GENERIC_OAUTH_NAME",
            "GF_AUTH_GENERIC_OAUTH_CLIENT_ID",
            "GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET",
            "GF_AUTH_GENERIC_OAUTH_SCOPES",
            "GF_AUTH_GENERIC_OAUTH_AUTH_URL",
            "GF_AUTH_GENERIC_OAUTH_TOKEN_URL",
            "GF_AUTH_GENERIC_OAUTH_API_URL",
            "GF_AUTH_GENERIC_OAUTH_USE_REFRESH_TOKEN",
            "GF_FEATURE_TOGGLES_ENABLE",
        }
        for k in oauth_env:
            assert k not in env


def test_config_is_updated_with_oauth_relation_data_removed(ctx, base_state, peer_relation):
    # GIVEN an oauth relation AND an oauth secret
    oauth_secret = Secret({"secret": OAUTH_CLIENT_SECRET})
    oauth_rel = Relation(
        "oauth",
        remote_app_name="hydra",
        remote_app_data={
            "client_id": OAUTH_CLIENT_ID,
            "client_secret_id": oauth_secret.id,
            **OAUTH_PROVIDER_INFO,
        },
    )
    state = replace(base_state, relations={peer_relation, oauth_rel}, secrets={oauth_secret})

    # WHEN a relation_broken event fires
    with ctx(ctx.on.relation_broken(oauth_rel), state) as mgr:
        mgr.run()
        charm = mgr.charm
        services = charm.unit.get_container("grafana").get_plan().services["grafana"].to_dict()

        env = services["environment"]  # type: ignore
        oauth_env = {
            "GF_AUTH_GENERIC_OAUTH_ENABLED",
            "GF_AUTH_GENERIC_OAUTH_NAME",
            "GF_AUTH_GENERIC_OAUTH_CLIENT_ID",
            "GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET",
            "GF_AUTH_GENERIC_OAUTH_SCOPES",
            "GF_AUTH_GENERIC_OAUTH_AUTH_URL",
            "GF_AUTH_GENERIC_OAUTH_TOKEN_URL",
            "GF_AUTH_GENERIC_OAUTH_API_URL",
            "GF_AUTH_GENERIC_OAUTH_USE_REFRESH_TOKEN",
            "GF_FEATURE_TOGGLES_ENABLE",
        }
        # THEN oauth env vars are not set
        for k in oauth_env:
            assert k not in env
