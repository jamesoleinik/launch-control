"""Read-only recording readiness checks for Episode 11."""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
EPISODE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(EPISODE_ROOT))

import auth  # noqa: E402
from agent.config import Config  # noqa: E402
from agent.identity import AgentTokenProvider  # noqa: E402

EPISODE = "ep-11-agent-quality-gate"
ROLE_NAME = "lc Quality Gate Agent"
BPF_NAME = "Launch Approval"
PLUGIN_ASSEMBLY = "QualityGateAutomation"
PLUGIN_TYPES = {
    "QualityGateAutomation.CreateQualityGateAssignmentPlugin",
    "QualityGateAutomation.ApplyQualityGateResultPlugin",
}
PLUGIN_STEPS = {
    "Launch Approval: Create Quality Gate Assignment",
    "Quality Gate Result: Apply and Advance",
}
BPF_STRUCTURE = [
    ("Draft", ["lc_name", "lc_targetdate"]),
    (
        "Quality Gate",
        [
            "lc_qualitygatestatus",
            "lc_qualitygatescore",
            "lc_qualitygatefeedback",
            "lc_qualitygateevidence",
            "lc_qualitygatecheckedon",
        ],
    ),
    ("Launch Approval", ["lc_approvaldecision", "ownerid"]),
    ("Ready To Launch", ["lc_launchstatus"]),
]


def jwt_tenant(token: str) -> str | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("tid")
    except (IndexError, ValueError, json.JSONDecodeError):
        return None


def bpf_structure(clientdata: str) -> list[tuple[str, list[str]]]:
    root = json.loads(clientdata)
    result = []
    for entity in root["steps"]["list"]:
        if not str(entity.get("__class", "")).startswith("EntityStep:"):
            continue
        for stage in entity["steps"]["list"]:
            fields = [
                step["steps"]["list"][0]["dataFieldName"]
                for step in stage["steps"]["list"]
            ]
            result.append((stage["description"], fields))
    return result


class Checks:
    def __init__(self) -> None:
        self.failures = 0

    def check(self, name: str, passed: bool, detail: str = "") -> None:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}{': ' + detail if detail else ''}")
        if not passed:
            self.failures += 1


def get_json(api: str, headers: dict[str, str], path: str) -> dict[str, Any]:
    response = requests.get(api + path, headers=headers, timeout=90)
    if response.status_code != 200:
        raise RuntimeError(
            f"GET {path} failed ({response.status_code}): {response.text[:500]}"
        )
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-dev-identity",
        action="store_true",
        help="Allow Azure CLI identity instead of the Agent ID token broker.",
    )
    args = parser.parse_args()

    auth.load_env(EPISODE)
    load_dotenv(EPISODE_ROOT / ".env", override=True)
    checks = Checks()

    required = [
        "DATAVERSE_URL",
        "TENANT_ID",
        "QUALITY_GATE_AGENT_SYSTEMUSER_ID",
    ]
    if not args.allow_dev_identity:
        required.extend(["A365_AGENT_ID", "A365_AGENT_USER_ID"])
        has_broker = bool(os.environ.get("A365_TOKEN_BROKER_URL"))
        if not has_broker:
            required.extend(
                [
                    "A365_BLUEPRINT_CLIENT_ID",
                    "A365_BLUEPRINT_CLIENT_SECRET",
                ]
            )
    missing = [name for name in required if not os.environ.get(name)]
    checks.check(
        "required configuration",
        not missing,
        "missing " + ", ".join(missing) if missing else "complete",
    )
    if missing:
        return 1

    for name in ("TENANT_ID", "QUALITY_GATE_AGENT_SYSTEMUSER_ID"):
        try:
            UUID(os.environ[name].strip("{}"))
            valid = True
        except ValueError:
            valid = False
        checks.check(f"{name} is a GUID", valid)
    mailbox = os.environ.get("A365_AGENT_MAILBOX", "")
    checks.check(
        "optional agent mailbox configuration",
        not mailbox or "@" in mailbox,
        mailbox or "disabled",
    )

    checks.check(
        "Microsoft 365 Agents SDK installed",
        importlib.util.find_spec("microsoft_agents") is not None,
    )
    checks.check(
        "Playwright installed",
        importlib.util.find_spec("playwright") is not None,
    )

    config = Config.load()
    provider = AgentTokenProvider(config)
    is_agent_identity = provider.mode in {
        "Microsoft Entra Agent ID token broker",
        "Microsoft Entra Agent User OAuth test flow",
    }
    checks.check(
        "agent identity token mode",
        is_agent_identity or args.allow_dev_identity,
        provider.mode,
    )

    try:
        token = provider()
    except Exception as exc:
        checks.check("agent token acquisition", False, str(exc))
        print(f"\nPreflight: {checks.failures} failure(s)")
        return 1
    checks.check("agent token acquisition", True, provider.mode)
    token_tenant = jwt_tenant(token)
    checks.check(
        "token tenant matches configured tenant",
        bool(token_tenant)
        and token_tenant.lower() == config.tenant_id.lower(),
        token_tenant or "tenant claim unavailable",
    )

    api = config.dataverse_url + "/api/data/v9.2"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    who = get_json(api, headers, "/WhoAmI")
    caller = who.get("UserId", "").lower()
    caller_matches_agent = caller == config.agent_systemuser_id.lower()
    checks.check(
        "Dataverse caller is configured agent user",
        caller_matches_agent or args.allow_dev_identity,
        caller if caller_matches_agent else f"{caller} (development identity)",
    )

    table = get_json(
        api,
        headers,
        "/EntityDefinitions?$select=LogicalName"
        "&$filter=LogicalName eq 'lc_qualitygateresult'",
    )["value"]
    checks.check("Quality Gate Result table exists", bool(table))

    agent_user = get_json(
        api,
        headers,
        f"/systemusers({config.agent_systemuser_id})"
        "?$select=systemmanagedusertype,isdisabled",
    )
    checks.check(
        "Dataverse principal is an enabled agent user",
        agent_user.get("systemmanagedusertype") == 3
        and agent_user.get("isdisabled") is False,
    )

    roles = get_json(
        api,
        headers,
        f"/systemusers({config.agent_systemuser_id})/"
        "systemuserroles_association?$select=name",
    )["value"]
    role_names = {row["name"] for row in roles}
    expected_roles = {"Basic User", ROLE_NAME}
    checks.check(
        "only approved least-privilege roles are assigned",
        role_names == expected_roles,
        ", ".join(sorted(role_names)),
    )

    control_token = auth.get_token(EPISODE)
    control_headers = {
        "Authorization": f"Bearer {control_token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    workflows = get_json(
        api,
        control_headers,
        "/workflows?$select=name,statecode,category,clientdata"
        f"&$filter=name eq '{BPF_NAME}' and category eq 4",
    )["value"]
    active = any(row.get("statecode") == 1 for row in workflows)
    checks.check("Launch Approval BPF active", active)
    exact_structure = any(
        row.get("statecode") == 1
        and bpf_structure(row.get("clientdata", "")) == BPF_STRUCTURE
        for row in workflows
    )
    checks.check("Launch Approval BPF structure", exact_structure)

    assemblies = get_json(
        api,
        control_headers,
        "/pluginassemblies?$select=name"
        f"&$filter=name eq '{PLUGIN_ASSEMBLY}'",
    )["value"]
    checks.check("Quality Gate plug-in assembly", len(assemblies) == 1)
    plugin_types = get_json(
        api,
        control_headers,
        "/plugintypes?$select=typename"
        "&$filter=startswith(typename,'QualityGateAutomation.')",
    )["value"]
    checks.check(
        "Quality Gate plug-in types",
        {row["typename"] for row in plugin_types} == PLUGIN_TYPES,
    )
    plugin_steps = get_json(
        api,
        control_headers,
        "/sdkmessageprocessingsteps?$select=name,statecode,mode,stage"
        "&$filter=startswith(name,'Launch Approval:') "
        "or startswith(name,'Quality Gate Result:')",
    )["value"]
    checks.check(
        "Quality Gate plug-in steps",
        {row["name"] for row in plugin_steps} == PLUGIN_STEPS
        and all(
            row.get("statecode") == 0
            and row.get("mode") == 0
            and row.get("stage") == 40
            for row in plugin_steps
        ),
    )

    try:
        browser_list = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--list"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        chromium_lines = [
            line.strip()
            for line in browser_list.stdout.splitlines()
            if "chromium-" in line.lower()
        ]
        checks.check(
            "Chromium installed",
            browser_list.returncode == 0 and bool(chromium_lines),
            chromium_lines[-1] if chromium_lines else "not found",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        checks.check("Chromium installed", False, str(exc))

    print(f"\nPreflight: {checks.failures} failure(s)")
    return 1 if checks.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
