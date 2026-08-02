"""
Diagnose why Data Activator flow actions fail in Ep 10.

This script uses pac + BAP APIs to verify whether Data Activator can be enabled
via connector-governance controls in the current tenant.

Usage:
    python episodes/ep-10-dataverse-fabriciq/diagnose_dataactivator_policy.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request


def run(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _az_cmd() -> str:
    direct = shutil.which("az")
    if direct:
        return direct
    candidate = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
    if os.path.exists(candidate):
        return candidate
    raise RuntimeError("Azure CLI executable not found (az)")


def get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(url: str, token: str, body: dict) -> dict:
    raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=raw,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(raw) from exc


def main() -> int:
    try:
        az = _az_cmd()
        tenant_id = run([az, "account", "show", "--query", "tenantId", "-o", "tsv"])
        pwr_token = run(
            [
                az,
                "account",
                "get-access-token",
                "--resource",
                "https://service.powerapps.com/",
                "--query",
                "accessToken",
                "-o",
                "tsv",
            ]
        )
    except Exception as exc:
        print(f"ERROR: auth precheck failed: {exc}")
        return 1

    print(f"Tenant: {tenant_id}")

    # 1) List DLP policies
    policies_url = (
        "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform/"
        "scopes/admin/apiPolicies?api-version=2024-05-01"
    )
    policies = get_json(policies_url, pwr_token).get("value", [])
    print(f"DLP policies found: {len(policies)}")
    for p in policies:
        display = p.get("properties", {}).get("displayName", "")
        print(f"  {p.get('name')} | {display}")

    # 2) Confirm Data Activator appears in policy api groups
    has_dataactivator = False
    for p in policies:
        groups = p.get("properties", {}).get("definition", {}).get("apiGroups", {})
        for g in groups.values():
            for api in g.get("apis", []):
                if api.get("id") in (
                    "/providers/Microsoft.PowerApps/apis/shared_dataactivator",
                    "/providers/Microsoft.PowerApps/apis/shared_dataactivatorpreview",
                ):
                    has_dataactivator = True
                    break
    print(f"Data Activator present in DLP api groups: {has_dataactivator}")

    # 3) Try tenant connector-governance enablement create probe
    # Expected in this tenant today: not supported (DlpConnectorEnablementConfigurationsNotAllowedForTenant)
    probe_url = (
        "https://api.bap.microsoft.com/providers/PowerPlatform.Governance/v1/"
        f"tenants/{tenant_id}/connectorEnablementConfigurations?api-version=2024-05-01"
    )
    probe_body = {"ConnectorSettings": [{"id": "/providers/Microsoft.PowerApps/apis/shared_dataactivator"}]}

    try:
        probe_result = post_json(probe_url, pwr_token, probe_body)
        print("Connector enablement POST accepted:")
        print(json.dumps(probe_result, indent=2))
    except Exception as exc:
        msg = str(exc)
        print("Connector enablement POST failed (expected in this tenant):")
        print(msg)
        if "DlpConnectorEnablementConfigurationsNotAllowedForTenant" in msg:
            print("\nConclusion:")
            print(
                "- This tenant does not allow connector-enablement policy overrides via PAC/API.\n"
                "- Use Fabric item action path, or ask tenant admin to change Advanced Connector Policy in PPAC."
            )
            return 0
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
