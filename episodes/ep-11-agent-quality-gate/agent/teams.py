from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

import requests

from .config import Config
from .dataverse import Assignment

GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_API = "https://graph.microsoft.com/v1.0"


class ResourceTokenProvider(Protocol):
    def get_token(self, scope: str) -> str: ...


@dataclass(frozen=True)
class TeamsNotification:
    chat_id: str
    message_id: str
    launch_url: str
    sender_user_id: str


class TeamsNotifier:
    """Post completion updates as the delegated Agentic User."""

    def __init__(
        self,
        config: Config,
        token_provider: ResourceTokenProvider,
        agent_user_id: str,
    ) -> None:
        if not config.teams_recipient:
            raise ValueError("A365_TEAMS_RECIPIENT is required")
        if not config.launch_control_app_id:
            raise ValueError("LAUNCH_CONTROL_APP_ID is required")
        if not agent_user_id:
            raise ValueError("A365_AGENT_USER_ID is required")
        self.config = config
        self.token_provider = token_provider
        self.agent_user_id = agent_user_id.strip("{}")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": (
                f"Bearer {self.token_provider.get_token(GRAPH_SCOPE)}"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        expected: tuple[int, ...] = (200, 201),
    ) -> requests.Response:
        response = requests.request(
            method,
            GRAPH_API + path,
            headers=self._headers(),
            json=body,
            timeout=90,
        )
        if response.status_code not in expected:
            raise RuntimeError(
                f"Microsoft Graph {method} {path} failed "
                f"({response.status_code}): {response.text[:800]}"
            )
        return response

    def launch_url(self, launch_id: str) -> str:
        query = urlencode(
            {
                "appid": self.config.launch_control_app_id,
                "pagetype": "entityrecord",
                "etn": "lc_launch",
                "id": "{" + launch_id.strip("{}") + "}",
            }
        )
        return f"{self.config.dataverse_url}/main.aspx?{query}"

    def ensure_chat(self) -> str:
        members = [
            {
                "@odata.type": (
                    "#microsoft.graph.aadUserConversationMember"
                ),
                "roles": ["owner"],
                "user@odata.bind": (
                    f"{GRAPH_API}/users('{self.agent_user_id}')"
                ),
            },
            {
                "@odata.type": (
                    "#microsoft.graph.aadUserConversationMember"
                ),
                "roles": ["owner"],
                "user@odata.bind": (
                    f"{GRAPH_API}/users('{self.config.teams_recipient}')"
                ),
            },
        ]
        response = self._request(
            "POST",
            "/chats",
            {"chatType": "oneOnOne", "members": members},
        )
        chat_id = response.json().get("id")
        if not chat_id:
            raise RuntimeError("Microsoft Graph returned no Teams chat ID")
        return chat_id

    def send_completion(
        self,
        assignment: Assignment,
        *,
        outcome: str,
        score: int,
    ) -> TeamsNotification:
        stage = "Launch Approval" if outcome == "PASSED" else "Quality Gate"
        launch_url = self.launch_url(assignment.launch_id)
        content = (
            "<p><strong>Quality analysis complete</strong></p>"
            f"<p><strong>Launch:</strong> "
            f"{html.escape(assignment.launch_name)}<br>"
            f"<strong>Verdict:</strong> {html.escape(outcome)}<br>"
            f"<strong>Score:</strong> {score}/100<br>"
            f"<strong>BPF state:</strong> {stage}</p>"
            f'<p><a href="{html.escape(launch_url, quote=True)}">'
            "Open the Launch and current BPF state</a></p>"
        )
        chat_id = self.ensure_chat()
        response = self._request(
            "POST",
            f"/chats/{chat_id}/messages",
            {
                "body": {
                    "contentType": "html",
                    "content": content,
                }
            },
        )
        message_id = response.json().get("id")
        if not message_id:
            raise RuntimeError("Microsoft Graph returned no Teams message ID")
        sender_user_id = (
            response.json().get("from", {}).get("user", {}).get("id", "")
        )
        if sender_user_id.lower() != self.agent_user_id.lower():
            raise RuntimeError(
                "Teams completion was not attributed to the Agentic User"
            )
        return TeamsNotification(
            chat_id=chat_id,
            message_id=message_id,
            launch_url=launch_url,
            sender_user_id=sender_user_id,
        )
