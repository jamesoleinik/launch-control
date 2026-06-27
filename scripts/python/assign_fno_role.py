"""Assign a Finance & Operations security role to a user.

Uses the F&O OData data entities (SystemUsers, SecurityRoles,
SecurityUserRoleAssociations). Auth is delegated to the Azure CLI: whoever is
signed in via `az login` must be a valid F&O admin in the target environment.

This script is idempotent and defaults to a read-only inspection (dry-run).
Pass --assign to actually import the user (if needed) and create the role
association.

Examples
--------
# Inspect: confirm admin access, show whether the user exists, list roles
python scripts/python/assign_fno_role.py --fno-url https://<your-fno-env>.operations.dynamics.com \
    --user someone@contoso.onmicrosoft.com

# Assign (writes): import the user if missing, then grant the role
python scripts/python/assign_fno_role.py --fno-url https://<your-fno-env>.operations.dynamics.com \
    --user someone@contoso.onmicrosoft.com --role "System administrator" \
    --legal-entity DAT --assign

No environment identifiers are hardcoded; pass --fno-url (or set FNO_URL in the
repo-root .env).
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def load_fno_url_from_env():
    """Best-effort: read FNO_URL from the repo-root .env without extra deps."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("FNO_URL"):
            _, _, val = line.partition("=")
            return val.strip().strip('"').strip("'") or None
    return None


def get_token(resource):
    """Get an Entra access token for the F&O resource via the Azure CLI."""
    result = subprocess.run(
        ["az", "account", "get-access-token", "--resource", resource,
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True, shell=(os.name == "nt"),
    )
    if result.returncode != 0:
        sys.exit(f"Failed to get token (is `az login` done as an F&O admin?):\n{result.stderr}")
    return result.stdout.strip()


def odata_request(base, token, path, method="GET", body=None):
    url = f"{base}/data/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        return e.code, detail


def odata_get_value(base, token, path):
    status, payload = odata_request(base, token, path)
    if status != 200:
        sys.exit(f"GET {path} -> {status}\n{payload}")
    return payload.get("value", []) if isinstance(payload, dict) else []


def main():
    ap = argparse.ArgumentParser(description="Assign an F&O security role to a user.")
    ap.add_argument("--fno-url", default=load_fno_url_from_env(),
                    help="F&O instance URL, e.g. https://<env>.operations.dynamics.com")
    ap.add_argument("--user", required=True, help="User UPN / email (Entra alias).")
    ap.add_argument("--role", help="SecurityRoleName to assign (required with --assign).")
    ap.add_argument("--legal-entity", default="DAT",
                    help="Default company/legal entity for a newly imported user (default: DAT).")
    ap.add_argument("--user-id", help="Short F&O UserID to use if the user must be created "
                    "(default: derived from the alias).")
    ap.add_argument("--provider", help="Entra identity provider URL for a newly imported user "
                    "(default: https://sts.windows.net/<tenant>/ from the signed-in tenant).")
    ap.add_argument("--assign", action="store_true",
                    help="Perform writes (import user if missing, create role association). "
                    "Omit for a read-only inspection.")
    args = ap.parse_args()

    if not args.fno_url:
        sys.exit("Provide --fno-url or set FNO_URL in the repo-root .env.")
    base = args.fno_url.rstrip("/")
    resource = base
    token = get_token(resource)
    user = args.user

    # 1) Confirm admin access + locate the user.
    print(f"== F&O instance: {base}")
    filt = urllib.parse.quote(f"Email eq '{user}'")
    matches = odata_get_value(
        base, token,
        f"SystemUsers?$select=UserID,UserName,Email,Alias,Enabled&$filter={filt}")
    if matches:
        u = matches[0]
        print(f"== User found: UserID={u.get('UserID')} Enabled={u.get('Enabled')} "
              f"Email={u.get('Email')}")
        user_id = u.get("UserID")
    else:
        print(f"== User '{user}' is NOT yet a SystemUser in this environment.")
        user_id = None

    # 2) Resolve the role (if provided).
    role = None
    if args.role:
        rfilt = urllib.parse.quote(f"SecurityRoleName eq '{args.role}'")
        roles = odata_get_value(
            base, token,
            f"SecurityRoles?$select=SecurityRoleName,SecurityRoleIdentifier&$filter={rfilt}")
        if not roles:
            print(f"!! Role '{args.role}' not found. Listing first 25 roles for reference:")
            for r in odata_get_value(
                    base, token,
                    "SecurityRoles?$select=SecurityRoleName&$top=25&$orderby=SecurityRoleName"):
                print(f"   - {r.get('SecurityRoleName')}")
            sys.exit(1)
        role = roles[0]
        print(f"== Role: {role.get('SecurityRoleName')} "
              f"(identifier={role.get('SecurityRoleIdentifier')})")

    if not args.assign:
        print("\n(dry-run) No changes made. Re-run with --role \"<name>\" --assign to apply.")
        return

    if not role:
        sys.exit("--assign requires --role.")

    # 3) Import the user if missing.
    if user_id is None:
        new_id = args.user_id or user.split("@")[0][:20]
        provider = args.provider
        if not provider:
            tenant = subprocess.run(
                ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
                capture_output=True, text=True, shell=(os.name == "nt")).stdout.strip()
            provider = f"https://sts.windows.net/{tenant}/"
        print(f"== Importing user as SystemUser UserID={new_id} (provider={provider}) ...")
        body = {
            "UserID": new_id,
            "UserName": user.split("@")[0],
            "Alias": user,
            "Email": user,
            "Company": args.legal_entity,
            "Enabled": True,
            "UserInfo_language": "en-us",
            "Helplanguage": "en-us",
            "Provider": provider,
        }
        status, payload = odata_request(base, token, "SystemUsers", "POST", body)
        if status not in (200, 201):
            sys.exit(f"User import failed ({status}):\n{payload}\n"
                     "Importing users via OData can be version-specific; if this fails, "
                     "import the user in the F&O UI (System administration > Users) and re-run.")
        user_id = new_id
        print("== User imported.")

    # 4) Idempotent role association.
    afilt = urllib.parse.quote(
        f"UserId eq '{user_id}' and SecurityRoleIdentifier eq '{role.get('SecurityRoleIdentifier')}'")
    existing = odata_get_value(
        base, token, f"SecurityUserRoleAssociations?$filter={afilt}")
    if existing:
        print("== Role already assigned. Nothing to do (idempotent).")
        return
    body = {
        "UserId": user_id,
        "SecurityRoleIdentifier": role.get("SecurityRoleIdentifier"),
    }
    status, payload = odata_request(
        base, token, "SecurityUserRoleAssociations", "POST", body)
    if status not in (200, 201):
        sys.exit(f"Role assignment failed ({status}):\n{payload}")
    print(f"== Assigned '{role.get('SecurityRoleName')}' to {user}. Done.")


if __name__ == "__main__":
    main()
