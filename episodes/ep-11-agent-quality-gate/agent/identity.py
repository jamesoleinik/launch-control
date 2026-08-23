from __future__ import annotations

from collections.abc import Callable
from time import monotonic
from typing import Any

import os
import requests
from azure.identity import AzureCliCredential

from .config import Config

TOKEN_EXCHANGE_SCOPE = "api://AzureADTokenExchange/.default"
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


class AgentTokenProvider:
    """Acquire Dataverse tokens for the registered agent runtime.

    Local development can use Azure CLI. A controlled recording test can use
    the documented three-step Agent User OAuth flow with a short-lived
    blueprint secret. Production should use the approved Auth SDK sidecar or
    another approved broker with a certificate or federated credential.
    """

    def __init__(self, config: Config) -> None:
        self.broker_url = os.environ.get("A365_TOKEN_BROKER_URL", "").strip()
        self.blueprint_client_id = os.environ.get(
            "A365_BLUEPRINT_CLIENT_ID", ""
        ).strip()
        self.blueprint_client_secret = os.environ.get(
            "A365_BLUEPRINT_CLIENT_SECRET", ""
        ).strip()
        self.agent_id = os.environ.get("A365_AGENT_ID", "").strip()
        self.agent_user_id = os.environ.get("A365_AGENT_USER_ID", "").strip()
        self.tenant_id = config.tenant_id
        self.scope = config.dataverse_url + "/.default"
        self.session = requests.Session()
        self._exchange_tokens: tuple[str, str, float] | None = None
        self._resource_tokens: dict[str, tuple[str, float]] = {}
        self.direct_enabled = all(
            (
                self.blueprint_client_id,
                self.blueprint_client_secret,
                self.agent_id,
                self.agent_user_id,
            )
        )
        if self.broker_url and self.agent_id:
            self.credential = None
            self.mode = "Microsoft Entra Agent ID token broker"
        elif self.direct_enabled:
            self.credential = None
            self.mode = "Microsoft Entra Agent User OAuth test flow"
        else:
            self.credential = AzureCliCredential(
                tenant_id=config.tenant_id, process_timeout=60
            )
            self.mode = "Azure CLI development credential (not agent identity)"

    def __call__(self) -> str:
        return self.get_token(self.scope)

    def get_token(self, scope: str) -> str:
        if self.broker_url:
            response = requests.post(
                self.broker_url,
                json={
                    "tenant_id": os.environ["TENANT_ID"],
                    "agent_identity_id": self.agent_id,
                    "agent_user_id": self.agent_user_id,
                    "scope": scope,
                },
                timeout=30,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Agent ID token broker failed ({response.status_code}): "
                    f"{response.text[:400]}"
                )
            token = response.json().get("access_token")
            if not token:
                raise RuntimeError("Agent ID token broker returned no access_token")
            return token
        if self.direct_enabled:
            return self._get_agent_user_token(scope)
        return self.credential.get_token(scope).token

    def _get_agent_user_token(self, scope: str) -> str:
        cached = self._resource_tokens.get(scope)
        if cached and cached[1] > monotonic():
            return cached[0]

        blueprint_token, agent_token = self._get_exchange_tokens()
        result = self._post_token(
            {
                "client_id": self.agent_id,
                "scope": scope,
                "grant_type": "user_fic",
                "client_assertion_type": CLIENT_ASSERTION_TYPE,
                "client_assertion": blueprint_token,
                "user_id": self.agent_user_id,
                "user_federated_identity_credential": agent_token,
            },
            "agent user resource token",
        )
        token = self._access_token(result, "agent user resource token")
        self._resource_tokens[scope] = (
            token,
            monotonic() + self._cache_lifetime(result),
        )
        return token

    def _get_exchange_tokens(self) -> tuple[str, str]:
        if self._exchange_tokens and self._exchange_tokens[2] > monotonic():
            return self._exchange_tokens[:2]

        blueprint_result = self._post_token(
            {
                "client_id": self.blueprint_client_id,
                "scope": TOKEN_EXCHANGE_SCOPE,
                "grant_type": "client_credentials",
                "client_secret": self.blueprint_client_secret,
                "fmi_path": self.agent_id,
            },
            "blueprint exchange token",
        )
        blueprint_token = self._access_token(
            blueprint_result, "blueprint exchange token"
        )
        agent_result = self._post_token(
            {
                "client_id": self.agent_id,
                "scope": TOKEN_EXCHANGE_SCOPE,
                "grant_type": "client_credentials",
                "client_assertion_type": CLIENT_ASSERTION_TYPE,
                "client_assertion": blueprint_token,
            },
            "agent identity exchange token",
        )
        agent_token = self._access_token(
            agent_result, "agent identity exchange token"
        )
        expires_at = monotonic() + min(
            self._cache_lifetime(blueprint_result),
            self._cache_lifetime(agent_result),
        )
        self._exchange_tokens = (blueprint_token, agent_token, expires_at)
        return blueprint_token, agent_token

    def _post_token(
        self, form: dict[str, str], description: str
    ) -> dict[str, Any]:
        endpoint = (
            f"https://login.microsoftonline.com/{self.tenant_id}"
            "/oauth2/v2.0/token"
        )
        response = self.session.post(endpoint, data=form, timeout=30)
        try:
            payload = response.json()
        except requests.JSONDecodeError as exc:
            raise RuntimeError(
                f"Microsoft Entra {description} returned invalid JSON "
                f"({response.status_code})"
            ) from exc
        if response.status_code != 200:
            error = payload.get("error", "token_request_failed")
            raise RuntimeError(
                f"Microsoft Entra {description} failed "
                f"({response.status_code}, {error})"
            )
        return payload

    @staticmethod
    def _access_token(payload: dict[str, Any], description: str) -> str:
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError(
                f"Microsoft Entra {description} returned no access_token"
            )
        return token

    @staticmethod
    def _cache_lifetime(payload: dict[str, Any]) -> float:
        try:
            expires_in = max(0, int(payload.get("expires_in", 0)))
        except (TypeError, ValueError):
            expires_in = 0
        return max(0, expires_in - 300)


TokenProvider = Callable[[], str]
