from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote

import requests

from .identity import AgentTokenProvider

SUBJECT_PREFIX = "Launch Control quality gate::"
TASK_ID = re.compile(
    r"^Launch Control quality gate::"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)


@dataclass(frozen=True)
class MailNotification:
    message_id: str
    task_id: str


class MailboxClient:
    def __init__(
        self, mailbox: str, token_provider: AgentTokenProvider
    ) -> None:
        self.mailbox = mailbox
        self.token_provider = token_provider
        self.api = "https://graph.microsoft.com/v1.0"

    def _request(
        self, method: str, path: str, body: dict | None = None
    ) -> requests.Response:
        token = self.token_provider.get_token(
            "https://graph.microsoft.com/.default"
        )
        response = requests.request(
            method,
            self.api + path,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60,
        )
        if response.status_code not in (200, 204):
            raise RuntimeError(
                f"Graph {method} {path} failed ({response.status_code}): "
                f"{response.text[:400]}"
            )
        return response

    def pending_notifications(self) -> list[MailNotification]:
        mailbox = quote(self.mailbox, safe="")
        prefix = SUBJECT_PREFIX.replace("'", "''")
        path = (
            f"/users/{mailbox}/mailFolders/inbox/messages"
            "?$select=id,subject&$top=25"
            f"&$filter=isRead eq false and startswith(subject,'{prefix}')"
        )
        rows = self._request("GET", path).json().get("value", [])
        notifications = []
        for row in rows:
            match = TASK_ID.fullmatch(row.get("subject", ""))
            if match:
                notifications.append(
                    MailNotification(
                        message_id=row["id"],
                        task_id=match.group(1).lower(),
                    )
                )
        return notifications

    def mark_read(self, message_id: str) -> None:
        mailbox = quote(self.mailbox, safe="")
        message = quote(message_id, safe="")
        self._request(
            "PATCH",
            f"/users/{mailbox}/messages/{message}",
            {"isRead": True},
        )
