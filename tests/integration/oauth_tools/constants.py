# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import os
from pathlib import Path
import collections

DEX_MANIFESTS = Path(__file__).parent / "dex.yaml"
KUBECONFIG = os.environ.get("TESTING_KUBECONFIG", "~/.kube/config")

DEX_CLIENT_ID = "client_id"
DEX_CLIENT_SECRET = "client_secret"

EXTERNAL_USER_EMAIL = "admin@example.com"
EXTERNAL_USER_PASSWORD = "password"

APPS = collections.namedtuple(
    "Apps",
    [
        "TRAEFIK_ADMIN",
        "TRAEFIK_PUBLIC",
        "HYDRA",
        "KRATOS",
        "KRATOS_EXTERNAL_IDP_INTEGRATOR",
        "IDENTITY_PLATFORM_LOGIN_UI_OPERATOR",
    ],
)(
    TRAEFIK_ADMIN="traefik-admin",
    TRAEFIK_PUBLIC="traefik-public",
    HYDRA="hydra",
    KRATOS="kratos",
    KRATOS_EXTERNAL_IDP_INTEGRATOR="kratos-external-idp-integrator",
    IDENTITY_PLATFORM_LOGIN_UI_OPERATOR="identity-platform-login-ui-operator",
)

OAUTH_RELATION = collections.namedtuple(
    "OAUTH_RELATION", ["OAUTH_APPLICATION", "OAUTH_INTERFACE", "OAUTH_PROXY"]
)(
    OAUTH_APPLICATION="hydra",
    OAUTH_INTERFACE="oauth",
    OAUTH_PROXY="traefik-public",
)

IDENTITY_BUNDLE = collections.namedtuple("IDENTITY_BUNDLE", ["NAME", "CHANNEL"])(
    NAME="identity-platform",
    CHANNEL="0.1/edge",
)
