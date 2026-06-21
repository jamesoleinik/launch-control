"""Episode 8: reset the security model to a clean slate for a ground-up rebuild.

This is the inverse of the build. Run it before recording so Cursor rebuilds the
whole model from nothing on camera, and re-run it between takes. It only touches
the artifacts this episode creates (everything named `lc *` / `lc_*`), never the
launch data itself, so it is safe to repeat.

What it removes (in dependency order):

  1. (Part 4) Restores the Cowork application user to System Administrator, undoing
     the per-agent scope-down, so Part 1 starts from the same baseline every time.
  2. (Part 3) Unbinds + deletes the `lc_EmailMask` masking rule.
  3. (Part 3) Deletes the `lc Sensitive Readers` field-security profile and its
     field permissions.
  4. (Part 3) Un-secures the `lc_teammember` PII columns (`lc_email`, `lc_fullname`)
     and publishes.
  5. (Part 2) Deletes the four `lc *` roles and their `lc *s` owner-teams.

It does NOT delete launch rows, the `lc_fullname` column, or reset `lc_name`; those
are data/schema set up once and reused. Pair with `seed_ep08_demo.py` only if you
also want to re-seed the demo personas + sample content.

Safety: prints a dry-run plan by default. Pass `--confirm` to actually delete.

Usage
-----
  python scripts/python/teardown_security.py             # dry-run (plan only)
  python scripts/python/teardown_security.py --confirm   # execute the reset
  python scripts/python/teardown_security.py --confirm --keep-rbac   # leave roles/teams
  python scripts/python/teardown_security.py --confirm --skip-agent-restore

Auth: uses `scripts/auth.py` (AzureCliCredential by default). Requires System
Administrator and a Managed Environment (masking rules need one).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from auth import get_credential  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))
URL = os.environ["DATAVERSE_URL"].rstrip("/")
API = URL + "/api/data/v9.2"
CLIENT_ID = os.environ.get("MCP_CLIENT_ID")

PROFILE_NAME = "lc Sensitive Readers"
MASK_NAME = "lc_EmailMask"
SECURED = [("lc_teammember", "lc_email"), ("lc_teammember", "lc_fullname")]
ROLES = ["lc Member", "lc Owner", "lc Viewer", "lc Admin"]
TEAMS = [r + "s" for r in ROLES]  # "lc Member" -> "lc Members"
ADMIN_ROLE = "System Administrator"

DRY = True  # flipped by --confirm


def _headers():
    tok = get_credential().get_token(URL + "/.default").token
    return {"Authorization": f"Bearer {tok}", "Accept": "application/json",
            "OData-MaxVersion": "4.0", "OData-Version": "4.0",
            "Content-Type": "application/json"}


H = _headers()


def g(path):
    r = requests.get(API + path, headers=H)
    r.raise_for_status()
    return r.json()


def delete(path, label):
    if DRY:
        print(f"  DRY-RUN would delete: {label}")
        return
    r = requests.delete(API + path, headers=H)
    ok = r.status_code in (200, 204)
    print(f"  {'deleted' if ok else f'FAILED({r.status_code})'}: {label}"
          + ("" if ok else f" -> {r.text[:160]}"))


# ---------------------------------------------------------------------------
# 1. Restore the Cowork application user to System Administrator
# ---------------------------------------------------------------------------
def restore_agent():
    if not CLIENT_ID:
        print("  MCP_CLIENT_ID not in .env; skipping agent restore.")
        return
    users = g(f"/systemusers?$select=systemuserid,fullname"
              f"&$filter=applicationid eq {CLIENT_ID}").get("value", [])
    if not users:
        print("  Cowork application user not found; skipping.")
        return
    uid = users[0]["systemuserid"]
    role = g(f"/roles?$select=roleid,name&$filter=name eq '{ADMIN_ROLE}'").get("value", [])
    if not role:
        print(f"  role '{ADMIN_ROLE}' not found; skipping.")
        return
    rid = role[0]["roleid"]
    assigned = g(f"/systemusers({uid})/systemuserroles_association?$select=roleid"
                 f"&$filter=roleid eq {rid}").get("value", [])
    if assigned:
        print(f"  agent {users[0]['fullname']}: already has {ADMIN_ROLE}")
        return
    if DRY:
        print(f"  DRY-RUN would add {ADMIN_ROLE} to agent {users[0]['fullname']}")
        return
    r = requests.post(
        f"{API}/systemusers({uid})/systemuserroles_association/$ref",
        headers=H, json={"@odata.id": f"{API}/roles({rid})"})
    print(f"  agent {users[0]['fullname']}: "
          + (f"granted {ADMIN_ROLE}" if r.status_code in (200, 204) else f"FAILED {r.status_code}"))


# ---------------------------------------------------------------------------
# 2 + 3. Masking rule, profile, field permissions
# ---------------------------------------------------------------------------
def remove_masking_and_profile():
    # Unbind every attributemaskingrule for our secured columns.
    for entity, attr in SECURED:
        binds = g("/attributemaskingrules?$select=attributemaskingruleid"
                  f"&$filter=entityname eq '{entity}' and attributelogicalname eq '{attr}'").get("value", [])
        for b in binds:
            delete(f"/attributemaskingrules({b['attributemaskingruleid']})",
                   f"attributemaskingrule {entity}.{attr}")

    # Delete the masking rule itself.
    rules = g(f"/maskingrules?$select=maskingruleid,name&$filter=name eq '{MASK_NAME}'").get("value", [])
    for r in rules:
        delete(f"/maskingrules({r['maskingruleid']})", f"maskingrule {MASK_NAME}")

    # Delete the field-security profile (field permissions cascade with it, but
    # remove them explicitly first so the plan is legible).
    profs = g(f"/fieldsecurityprofiles?$select=fieldsecurityprofileid,name"
              f"&$filter=name eq '{PROFILE_NAME}'").get("value", [])
    for p in profs:
        pid = p["fieldsecurityprofileid"]
        perms = g(f"/fieldpermissions?$select=fieldpermissionid,entityname,attributelogicalname"
                  f"&$filter=_fieldsecurityprofileid_value eq {pid}").get("value", [])
        for fp in perms:
            delete(f"/fieldpermissions({fp['fieldpermissionid']})",
                   f"fieldpermission {fp['entityname']}.{fp['attributelogicalname']}")
        delete(f"/fieldsecurityprofiles({pid})", f"fieldsecurityprofile {PROFILE_NAME}")


# ---------------------------------------------------------------------------
# 4. Un-secure the PII columns
# ---------------------------------------------------------------------------
def unsecure_columns():
    changed = False
    for entity, attr in SECURED:
        meta = g(f"/EntityDefinitions(LogicalName='{entity}')/Attributes(LogicalName='{attr}')"
                 f"?$select=LogicalName,IsSecured,AttributeType")
        if not meta.get("IsSecured"):
            print(f"  {entity}.{attr}: already not secured")
            continue
        if DRY:
            print(f"  DRY-RUN would set IsSecured=false on {entity}.{attr}")
            continue
        atype = meta["AttributeType"]
        odata_type = {"Memo": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
                      "String": "Microsoft.Dynamics.CRM.StringAttributeMetadata"}.get(
                          atype, "Microsoft.Dynamics.CRM.AttributeMetadata")
        body = {"@odata.type": "#" + odata_type, "LogicalName": attr, "IsSecured": False}
        r = requests.put(
            f"{API}/EntityDefinitions(LogicalName='{entity}')/Attributes(LogicalName='{attr}')",
            headers={**H, "MSCRM.MergeLabels": "true", "Consistency": "Strong"}, json=body)
        ok = r.status_code in (200, 204)
        print(f"  {entity}.{attr}: " + ("un-secured" if ok else f"FAILED {r.status_code} {r.text[:160]}"))
        changed = changed or ok
    if changed and not DRY:
        requests.post(API + "/PublishAllXml", headers=H, json={})
        print("  published customizations")


# ---------------------------------------------------------------------------
# 5. Roles + teams
# ---------------------------------------------------------------------------
def remove_roles_and_teams():
    for tname in TEAMS:
        teams = g(f"/teams?$select=teamid,name&$filter=name eq '{tname}'").get("value", [])
        for t in teams:
            delete(f"/teams({t['teamid']})", f"team {tname}")
    for rname in ROLES:
        roles = g(f"/roles?$select=roleid,name&$filter=name eq '{rname}'").get("value", [])
        for r in roles:
            delete(f"/roles({r['roleid']})", f"role {rname}")


def main() -> int:
    global DRY
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="Actually delete (default is dry-run).")
    ap.add_argument("--keep-rbac", action="store_true", help="Leave the lc roles/teams in place.")
    ap.add_argument("--skip-agent-restore", action="store_true",
                    help="Do not re-grant System Administrator to the Cowork app user.")
    args = ap.parse_args()
    DRY = not args.confirm

    print(f"Env: {URL}")
    print(f"Mode: {'EXECUTE' if args.confirm else 'DRY-RUN (pass --confirm to apply)'}\n")

    if not args.skip_agent_restore:
        print("[1] Restore Cowork app user to System Administrator")
        restore_agent()
    print("\n[2/3] Remove masking rule + field-security profile")
    remove_masking_and_profile()
    print("\n[4] Un-secure the lc_teammember PII columns")
    unsecure_columns()
    if not args.keep_rbac:
        print("\n[5] Remove the lc roles + owner-teams")
        remove_roles_and_teams()

    print("\nDone." + ("" if args.confirm else "  (nothing changed; this was a dry-run)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
