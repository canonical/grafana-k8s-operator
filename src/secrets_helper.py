#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""A Juju secrets getter for sensitive data."""

import logging
from typing import Optional
from urllib.parse import urlparse
import ops


logger = logging.getLogger(__name__)


class SecretError(Exception):
    """Raised when a secret cannot be resolved."""


class SecretGetter:
    """A getter for Juju secrets referenced by secret:// URLs."""

    def __init__(self, model: ops.Model):
        self._model = model

    def get_value(self, secret_url: str) -> Optional[str]:
        """Retrieve the secret value from a secret URL.

        Args:
            secret_url: a URL of the form secret://<secret-id>/<key>

        Returns:
            The secret value, or None if secret_url is empty.

        Raises:
            SecretError: if the URL is malformed, the secret is not found,
                the charm lacks permission, or any other error occurs.
        """
        if not secret_url:
            return None

        parsed_secret = urlparse(secret_url)
        if not all([parsed_secret.scheme == "secret", parsed_secret.netloc, parsed_secret.path]):
            raise SecretError("Invalid secret URL in custom_config.")

        secret_id = parsed_secret.netloc
        if len(paths := parsed_secret.path.lstrip("/").split("/")) != 1:
            raise SecretError("Invalid secret URL in custom_config.")

        secret_key = paths[0]
        try:
            secret = self._model.get_secret(id=secret_id)
        except ops.model.SecretNotFoundError as e:
            logger.error("Secret not found for URL %s: %s", secret_url, e)
            raise SecretError("Secret not found in custom_config.") from e
        except ops.model.ModelError as e:
            logger.error(
                "missing charm permissions for the secret in custom_config. "
                "run 'juju grant-secret' to resolve: %s",
                e,
            )
            raise SecretError(
                "missing charm permissions for secret in custom_config."
            ) from e
        except Exception as e:
            logger.error("unexpected error fetching secret: %s", e)
            raise SecretError("Unexpected error fetching secret.") from e

        content = secret.get_content(refresh=True)
        if not (value := content.get(secret_key)):
            raise SecretError("Secret not found in custom_config.")

        return value
