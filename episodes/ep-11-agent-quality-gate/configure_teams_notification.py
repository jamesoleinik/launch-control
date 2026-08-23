"""Configure delegated Graph permissions for Agentic User Teams updates."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from azure.identity import AzureCliCredential

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import auth  # noqa: E402

EPISODE = "ep-11-agent-quality-gate"
GRAPH_API = "https://graph.microsoft.com/v1.0"
GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"
REQUIRED_SCOPES = ("Chat.Create", "ChatMessage.Send")
CONFIG_PATH = ROOT / "a365.generated.config.json"


class Graph:
    def __init__(self, tenant_id: str) -> None:
        token = AzureCliCredential(
            tenant_id=tenant_id, process_timeout=60
        ).get_token("https://graph.microsoft.com/.default").token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (200, 201, 204),
    ) -> requests.Response:
        response = requests.request(
            method,
            GRAPH_API + path,
            headers=self.headers,
            json=body,
            timeout=90,
        )
        if response.status_code not in expected:
            raise RuntimeError(
                f"Microsoft Graph {method} {path} failed "
                f"({response.status_code}): {response.text[:800]}"
            )
        return response

    def one(self, path: str, description: str) -> dict[str, Any]:
        rows = self.request("GET", path).json().get("value", [])
        if len(rows) != 1:
            raise RuntimeError(
                f"Expected one {description}; found {len(rows)}"
            )
        return rows[0]


def read_agent_config() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        raise RuntimeError(
            "a365.generated.config.json is required and must remain gitignored"
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def required_access(
    current: list[dict[str, Any]],
    scope_ids: dict[str, str],
) -> list[dict[str, Any]]:
    access = [dict(item) for item in current]
    graph_entry = next(
        (
            item
            for item in access
            if item.get("resourceAppId", "").lower()
            == GRAPH_APP_ID.lower()
        ),
        None,
    )
    if graph_entry is None:
        graph_entry = {
            "resourceAppId": GRAPH_APP_ID,
            "resourceAccess": [],
        }
        access.append(graph_entry)
    existing = {
        item["id"].lower()
        for item in graph_entry.get("resourceAccess", [])
    }
    for scope_id in scope_ids.values():
        if scope_id.lower() not in existing:
            graph_entry.setdefault("resourceAccess", []).append(
                {"id": scope_id, "type": "Scope"}
            )
    return access


def permission_state(
    graph: Graph, blueprint_app_id: str
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, str],
    list[dict[str, Any]],
]:
    blueprint_app = graph.one(
        "/applications"
        f"?$filter=appId eq '{blueprint_app_id}'"
        "&$select=id,appId,requiredResourceAccess",
        "Agent 365 blueprint application",
    )
    blueprint_sp = graph.one(
        "/servicePrincipals"
        f"?$filter=appId eq '{blueprint_app_id}'"
        "&$select=id,appId",
        "Agent 365 blueprint service principal",
    )
    graph_sp = graph.one(
        "/servicePrincipals"
        f"?$filter=appId eq '{GRAPH_APP_ID}'"
        "&$select=id,appId,oauth2PermissionScopes",
        "Microsoft Graph service principal",
    )
    available = {
        scope["value"]: scope["id"]
        for scope in graph_sp.get("oauth2PermissionScopes", [])
        if scope.get("isEnabled")
    }
    missing_definitions = [
        scope for scope in REQUIRED_SCOPES if scope not in available
    ]
    if missing_definitions:
        raise RuntimeError(
            "Microsoft Graph scope definitions not found: "
            + ", ".join(missing_definitions)
        )
    grants = graph.request(
        "GET",
        "/oauth2PermissionGrants"
        f"?$filter=clientId eq '{blueprint_sp['id']}' "
        f"and resourceId eq '{graph_sp['id']}'"
        "&$select=id,clientId,resourceId,consentType,scope",
    ).json().get("value", [])
    return (
        blueprint_app,
        blueprint_sp,
        graph_sp,
        {scope: available[scope] for scope in REQUIRED_SCOPES},
        grants,
    )


def verify(
    blueprint_app: dict[str, Any],
    scope_ids: dict[str, str],
    grants: list[dict[str, Any]],
) -> bool:
    graph_access = next(
        (
            item
            for item in blueprint_app.get("requiredResourceAccess", [])
            if item.get("resourceAppId", "").lower()
            == GRAPH_APP_ID.lower()
        ),
        {},
    )
    configured_ids = {
        item.get("id", "").lower()
        for item in graph_access.get("resourceAccess", [])
    }
    configured = all(
        scope_id.lower() in configured_ids
        for scope_id in scope_ids.values()
    )
    consented_scopes = {
        scope
        for grant in grants
        if grant.get("consentType") == "AllPrincipals"
        for scope in grant.get("scope", "").split()
    }
    consented = all(scope in consented_scopes for scope in REQUIRED_SCOPES)
    print(f"[{'PASS' if configured else 'FAIL'}] Graph scopes configured")
    print(f"[{'PASS' if consented else 'FAIL'}] Graph scopes consented")
    return configured and consented


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    auth.load_env(EPISODE)
    tenant_id = os.environ["TENANT_ID"]
    config = read_agent_config()
    blueprint_app_id = config["agentBlueprintId"]
    graph = Graph(tenant_id)
    (
        blueprint_app,
        blueprint_sp,
        graph_sp,
        scope_ids,
        grants,
    ) = permission_state(graph, blueprint_app_id)

    if args.verify:
        return 0 if verify(blueprint_app, scope_ids, grants) else 1

    print("Plan: configure delegated Graph scopes for Agentic User Teams chat")
    for scope in REQUIRED_SCOPES:
        print(f"  - {scope}")
    if args.dry_run:
        print("[dry-run] no Microsoft Graph changes made")
        return 0

    updated_access = required_access(
        blueprint_app.get("requiredResourceAccess", []),
        scope_ids,
    )
    graph.request(
        "PATCH",
        f"/applications/{blueprint_app['id']}",
        {"requiredResourceAccess": updated_access},
    )

    all_principals = next(
        (
            grant
            for grant in grants
            if grant.get("consentType") == "AllPrincipals"
        ),
        None,
    )
    scopes = set(REQUIRED_SCOPES)
    if all_principals:
        scopes.update(all_principals.get("scope", "").split())
        graph.request(
            "PATCH",
            f"/oauth2PermissionGrants/{all_principals['id']}",
            {"scope": " ".join(sorted(scopes))},
        )
    else:
        graph.request(
            "POST",
            "/oauth2PermissionGrants",
            {
                "clientId": blueprint_sp["id"],
                "consentType": "AllPrincipals",
                "resourceId": graph_sp["id"],
                "scope": " ".join(sorted(scopes)),
            },
        )

    state = permission_state(graph, blueprint_app_id)
    return 0 if verify(state[0], state[3], state[4]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
