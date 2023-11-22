#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
from os.path import join
from time import sleep
from typing import List

from pytest_operator.plugin import OpsTest
from lightkube import Client, KubeConfig, codecs
from lightkube.core.exceptions import ApiError, ObjectDeleted
from lightkube.resources.apps_v1 import Deployment
from lightkube.resources.core_v1 import Pod, Service, Namespace
import requests
from requests.exceptions import RequestException

from oauth_tools.constants import (
    DEX_MANIFESTS,
    DEX_CLIENT_ID,
    DEX_CLIENT_SECRET,
    KUBECONFIG,
)

logger = logging.getLogger(__name__)


class ExternalIdpManager:
    """This class manages the lifecycle for the external Identity Provider used by the Oauth integration test."""

    def __init__(self, ops_test: OpsTest):
        # Deploys the identity provider
        self._ops_test = ops_test
        self._client = Client(config=KubeConfig.from_file(KUBECONFIG), field_manager="dex-test")
        self._redirect_uri = ""
        if not self._dex_namespace_exists():
            self._apply_dex_resources()

    @property
    def idp_service_url(self) -> str:
        # Retrieve the address of identity provider
        service = self._client.get(Service, "dex", namespace="dex")
        return f"http://{service.status.loadBalancer.ingress[0].ip}:5556/"

    def update_redirect_uri(self, redirect_uri: str) -> None:
        # Updates the redirect uri configuration for the identity provider.
        if not redirect_uri:
            logger.info("Empty parameter for redirect_uri")
            return
        self._redirect_uri = redirect_uri
        self._apply_dex_resources()

    def close(self) -> None:
        # Removes the identity provider deployment
        if self._ops_test.keep_model:
            return
        logger.info("Deleting dex resources")
        for obj in self._get_dex_manifest():
            try:
                self._client.delete(type(obj), obj.metadata.name, namespace=obj.metadata.namespace)
            except ApiError:
                pass

    def _dex_namespace_exists(self) -> bool:
        try:
            self._client.get(Namespace, "dex")
            return True
        except ApiError:
            return False

    def _get_dex_manifest(self) -> List[codecs.AnyResource]:
        temp_issuer_url = None
        try:
            temp_issuer_url = self.idp_service_url
        except ApiError:
            logger.info("No service found for identity provider")

        temp_redirect_url = self._redirect_uri
        if not temp_redirect_url:
            temp_redirect_url = None

        with open(DEX_MANIFESTS, "r") as file:
            return codecs.load_all_yaml(
                file,
                context={
                    "client_id": DEX_CLIENT_ID,
                    "client_secret": DEX_CLIENT_SECRET,
                    "redirect_uri": temp_redirect_url,
                    "issuer_url": temp_issuer_url,
                },
            )

    def _restart_dex(self) -> None:
        for pod in self._client.list(Pod, namespace="dex", labels={"app": "dex"}):
            self._client.delete(Pod, pod.metadata.name, namespace="dex")

    def _wait_until_dex_is_ready_helper(self) -> None:
        for pod in self._client.list(Pod, namespace="dex", labels={"app": "dex"}):
            # Some pods may be deleted, if we are restarting
            try:
                self._client.wait(
                    Pod, pod.metadata.name, for_conditions=["Ready", "Deleted"], namespace="dex"
                )
            except ObjectDeleted:
                pass
        self._client.wait(Deployment, "dex", namespace="dex", for_conditions=["Available"])

        try:
            temp_issuer_url = self.idp_service_url
            resp = requests.get(join(temp_issuer_url, ".well-known/openid-configuration"))
            if resp.status_code != 200:
                raise RuntimeError("Failed to deploy dex")
        except ApiError:
            raise RuntimeError("Failed to deploy dex")

    def _wait_until_dex_is_ready(self) -> None:
        try:
            self._wait_until_dex_is_ready_helper()
        except (RuntimeError, RequestException):
            sleep(3)
            self._wait_until_dex_is_ready_helper()

    def _apply_dex_resources(self) -> None:
        objs = self._get_dex_manifest()

        for obj in objs:
            self._client.apply(obj, force=True)

        logger.info("Restarting dex")
        self._restart_dex()

        logger.info("Waiting for dex to be ready")
        self._wait_until_dex_is_ready()
