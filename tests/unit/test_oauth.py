# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch
from tests.unit.test_charm import BaseTestCharm

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


class TestOauth(BaseTestCharm):
    def test_config_is_updated_with_oauth_relation_data(self):
        self.harness.set_leader(True)
        self.harness.container_pebble_ready("grafana")

        # add oauth relation with provider endpoints details
        rel_id = self.harness.add_relation("oauth", "hydra")
        self.harness.add_relation_unit(rel_id, "hydra/0")
        secret_id = self.harness.add_model_secret("hydra", {"secret": OAUTH_CLIENT_SECRET})
        self.harness.grant_secret(secret_id, "grafana-k8s")
        self.harness.update_relation_data(
            rel_id,
            "hydra",
            {
                "client_id": OAUTH_CLIENT_ID,
                "client_secret_id": secret_id,
                **OAUTH_PROVIDER_INFO,
            },
        )

        services = (
            self.harness.charm.containers["workload"].get_plan().services["grafana"].to_dict()
        )
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
        all(self.assertEqual(env[k], v) for k, v in expected_env.items())

    def test_config_with_empty_oauth_relation_data(self):
        self.harness.set_leader(True)
        self.harness.container_pebble_ready("grafana")

        rel_id = self.harness.add_relation("oauth", "hydra")
        self.harness.add_relation_unit(rel_id, "hydra/0")

        services = (
            self.harness.charm.containers["workload"].get_plan().services["grafana"].to_dict()
        )
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
        all(self.assertNotIn(k, env) for k in oauth_env)

    # The oauth library tries to access the relation databag
    # when the relation is departing. This causes harness to throw an
    # error, a behavior not implemented in juju. This will be fixed
    # once https://github.com/canonical/operator/issues/940 is merged
    def test_config_is_updated_with_oauth_relation_data_removed(self):
        patcher = patch("charms.hydra.v0.oauth.OAuthRequirer.is_client_created")
        self.mock_resolve_dir = patcher.start()
        self.mock_resolve_dir.return_value = False
        self.addCleanup(patcher.stop)
        self.harness.set_leader(True)
        self.harness.container_pebble_ready("grafana")

        # add oauth relation with provider endpoints details
        rel_id = self.harness.add_relation("oauth", "hydra")
        self.harness.add_relation_unit(rel_id, "hydra/0")
        secret_id = self.harness.add_model_secret("hydra", {"secret": OAUTH_CLIENT_SECRET})
        self.harness.grant_secret(secret_id, "grafana-k8s")
        self.harness.update_relation_data(
            rel_id,
            "hydra",
            {
                "client_id": OAUTH_CLIENT_ID,
                "client_secret_id": secret_id,
                **OAUTH_PROVIDER_INFO,
            },
        )
        self.mock_resolve_dir.return_value = True
        rel_id = self.harness.remove_relation(rel_id)

        services = (
            self.harness.charm.containers["workload"].get_plan().services["grafana"].to_dict()
        )
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
        all(self.assertNotIn(k, env) for k in oauth_env)
