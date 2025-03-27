#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright 2021 Canonical Ltd.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""A class to manage a secret for securely storing data between peers."""

import logging
import secrets
import string
from typing import Optional, Callable, Dict

import ops

logger = logging.getLogger()


def generate_password() -> str:
    """Generates a random 12 character password."""
    # Really limited by what can be passed into shell commands, since this all goes
    # through subprocess. So much for complex password
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(12))


class SecretStorage(ops.Object):
    """Class to manage the creation of a peer-shared secret to store simple key-value pairs."""

    def __init__(self, charm: ops.CharmBase,
                 label: str,
                 default: Callable[[], Dict[str, str]],
                 description: Optional[str] = None,
                 ):
        super().__init__(charm, label)
        self._label = label
        self._charm = charm
        self._default = default
        self._description = description

    @property
    def contents(self) -> Optional[Dict[str, str]]:
        # check if secret exists already
        secret = None
        secret_label = self._label

        try:
            secret = self._charm.model.get_secret(label=secret_label)
        except ops.SecretNotFoundError:
            logger.info(f"{secret_label} secret does not exist yet")
        except ops.ModelError:
            logger.exception(f"error retrieving {secret_label} secret")
        except:
            raise

        # if we're leader and have already generated the secret in a previous run,
        # or we're a follower and the leader has given us a secret already: fetch the content
        if secret:
            logger.debug(f"{secret_label} secret found: returning content")
            # we don't expect it to change, but just in case, refresh.
            return secret.get_content(refresh=True)

        # if we're a leader: generate the password and drop it in a secret
        if self._charm.unit.is_leader():
            logger.info(f"leader: creating and priming {secret_label} secret")
            content = self._default()
            self._charm.app.add_secret(
                content =content,
                label=secret_label,
                description=self._description
            )
            return content

        # if we're a follower and the leader hasn't generated a secret yet,
        # then we return None; we must wait.
        return None
