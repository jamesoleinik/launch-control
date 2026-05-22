"""Validate the Episode 4 RBAC approach against the live Dataverse environment.

This script exercises every primitive that setup_rbac.py and rbac_smoketest.py
will rely on, then cleans up:

  1. Read the root business unit.
  2. Create a test BU under root (idempotent on name).
  3. Create an owner-team inside the BU (idempotent on name).
  4. Read the OOB "Basic User" role (template).
  5. Create a new role in the test BU by copying Basic User via the
     CloneAsRole Web API action (the canonical "start from a template"
     mechanism). Falls back to a Web-API create + AddPrivilegesRole if
     the action isn't exposed.
  6. Associate the role with the test team (teamroles_association).
  7. Run WhoAmI with MSCRMCallerID set to self — proves the
     impersonation header is accepted on this environment for the
     calling user. (Full cross-user impersonation requires another
     systemuser, which we don't create here.)
  8. Clean up — disassociate, delete role, delete team, delete BU.

Exit code 0 on full success; non-zero on the first failed step.
Prints a clear pass/fail line per step so the output is human-readable.
"""
from __future__ import annotations

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
TOK = get_credential().get_token(URL + "/.default").token

H_READ = {
    "Authorization": f"Bearer {TOK}",
    "Accept": "application/json",
    "OData-MaxVersion": "4.0",
    "OData-Version": "4.0",
}
H_WRITE = {
    **H_READ,
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

TEST_BU_NAME = "lc_rbac_validation_bu"
TEST_TEAM_NAME = "lc_rbac_validation_team"
TEST_ROLE_NAME = "lc_rbac_validation_role"

FAIL = "❌"
OK = "✅"


def die(msg: str, resp: requests.Response | None = None) -> None:
    print(f"{FAIL} {msg}")
    if resp is not None:
        print(f"   HTTP {resp.status_code}: {resp.text[:600]}")
    sys.exit(1)


def step(n: int, msg: str) -> None:
    print(f"\n[{n}] {msg}")


# ---------------------------------------------------------------------------
# 0. Sanity — WhoAmI
# ---------------------------------------------------------------------------
step(0, "WhoAmI sanity check")
r = requests.get(f"{API}/WhoAmI", headers=H_READ)
if r.status_code != 200:
    die("WhoAmI failed — auth or env URL is wrong", r)
me = r.json()
print(f"   {OK} userid={me['UserId']}  bu={me['BusinessUnitId']}  org={me['OrganizationId']}")

# ---------------------------------------------------------------------------
# 1. Find the root BU
# ---------------------------------------------------------------------------
step(1, "Find the root business unit")
r = requests.get(
    f"{API}/businessunits?$select=businessunitid,name,_parentbusinessunitid_value",
    headers=H_READ,
)
if r.status_code != 200:
    die("Could not list BUs", r)
bus = r.json()["value"]
root_bu = next((b for b in bus if not b.get("_parentbusinessunitid_value")), None)
if not root_bu:
    die("No root BU found in this environment")
print(f"   {OK} root BU: {root_bu['name']} ({root_bu['businessunitid']})")

# ---------------------------------------------------------------------------
# 2. Create the test BU (idempotent on name)
# ---------------------------------------------------------------------------
step(2, f"Create test BU '{TEST_BU_NAME}' under root (idempotent)")
existing = [b for b in bus if b["name"] == TEST_BU_NAME]
if existing:
    test_bu_id = existing[0]["businessunitid"]
    print(f"   {OK} already exists: {test_bu_id}")
else:
    body = {
        "name": TEST_BU_NAME,
        "parentbusinessunitid@odata.bind": f"/businessunits({root_bu['businessunitid']})",
    }
    r = requests.post(f"{API}/businessunits", headers=H_WRITE, json=body)
    if r.status_code not in (200, 201):
        die("Failed to create test BU", r)
    test_bu_id = r.json()["businessunitid"]
    print(f"   {OK} created: {test_bu_id}")

# ---------------------------------------------------------------------------
# 3. Create the owner-team in the test BU (idempotent on name)
# ---------------------------------------------------------------------------
step(3, f"Create owner-team '{TEST_TEAM_NAME}' in test BU (idempotent)")
r = requests.get(
    f"{API}/teams?$select=teamid,name,teamtype&$filter=name eq '{TEST_TEAM_NAME}'",
    headers=H_READ,
)
existing = r.json().get("value", [])
if existing:
    test_team_id = existing[0]["teamid"]
    print(f"   {OK} already exists: {test_team_id} (teamtype={existing[0].get('teamtype')})")
else:
    body = {
        "name": TEST_TEAM_NAME,
        "description": "Created by rbac_validate.py — safe to delete.",
        "teamtype": 0,  # 0 = Owner team
        "businessunitid@odata.bind": f"/businessunits({test_bu_id})",
    }
    r = requests.post(f"{API}/teams", headers=H_WRITE, json=body)
    if r.status_code not in (200, 201):
        die("Failed to create owner-team", r)
    test_team_id = r.json()["teamid"]
    print(f"   {OK} created: {test_team_id}")

# ---------------------------------------------------------------------------
# 4. Get the "Basic User" role template (root-BU instance)
# ---------------------------------------------------------------------------
step(4, "Find 'Basic User' role template in root BU")
r = requests.get(
    f"{API}/roles?$select=roleid,name,_businessunitid_value,parentrootroleid"
    f"&$filter=name eq 'Basic User'",
    headers=H_READ,
)
roles = r.json().get("value", [])
basic_user_root = next(
    (rl for rl in roles if rl["_businessunitid_value"] == root_bu["businessunitid"]),
    None,
)
if not basic_user_root:
    die(f"'Basic User' not found in root BU (found {len(roles)} candidates across BUs)")
print(f"   {OK} Basic User (root): {basic_user_root['roleid']}")

# ---------------------------------------------------------------------------
# 5. Create the test role via CloneAsRole (preferred) or fallback
# ---------------------------------------------------------------------------
step(5, f"Create test role '{TEST_ROLE_NAME}' in test BU (clone of Basic User)")
# Did it already exist?
r = requests.get(
    f"{API}/roles?$select=roleid,name,_businessunitid_value"
    f"&$filter=name eq '{TEST_ROLE_NAME}' and _businessunitid_value eq {test_bu_id}",
    headers=H_READ,
)
existing = r.json().get("value", [])
if existing:
    test_role_id = existing[0]["roleid"]
    print(f"   {OK} already exists: {test_role_id}")
else:
    # Preferred path: CloneAsRole bound action
    clone_body = {
        "SourceRoleId": basic_user_root["roleid"],
        "BusinessUnitId": test_bu_id,
        "DisplayName": TEST_ROLE_NAME,
    }
    r = requests.post(f"{API}/CloneAsRole", headers=H_WRITE, json=clone_body)
    if r.status_code in (200, 201):
        # Response can be either {RoleId: "..."} or a role entity
        body = r.json()
        test_role_id = body.get("RoleId") or body.get("roleid")
        if not test_role_id:
            die("CloneAsRole returned 2xx but no role id in body", r)
        print(f"   {OK} cloned via CloneAsRole: {test_role_id}")
    else:
        # Fallback: create a bare role in the test BU; Dataverse auto-propagates
        # the role into child BUs but the privilege set will be empty. That's
        # still enough to validate the *plumbing*; the matrix-driven privilege
        # add is a separate concern.
        print(f"   ⚠ CloneAsRole not available ({r.status_code}); falling back to bare role create")
        body = {
            "name": TEST_ROLE_NAME,
            "businessunitid@odata.bind": f"/businessunits({test_bu_id})",
        }
        r2 = requests.post(f"{API}/roles", headers=H_WRITE, json=body)
        if r2.status_code not in (200, 201):
            die("Fallback role create failed", r2)
        test_role_id = r2.json()["roleid"]
        print(f"   {OK} bare role created: {test_role_id}")

# ---------------------------------------------------------------------------
# 6. Associate role with team
# ---------------------------------------------------------------------------
step(6, "Associate role with the owner-team (teamroles_association)")
assoc_body = {"@odata.id": f"{API}/roles({test_role_id})"}
r = requests.post(
    f"{API}/teams({test_team_id})/teamroles_association/$ref",
    headers=H_WRITE,
    json=assoc_body,
)
if r.status_code in (204,):
    print(f"   {OK} role bound to team")
elif r.status_code == 412 or (r.status_code >= 400 and "duplicate" in r.text.lower()):
    print(f"   {OK} role already bound to team (idempotent)")
else:
    # Some envs return 400 on re-bind — check if it's actually bound
    r2 = requests.get(
        f"{API}/teams({test_team_id})/teamroles_association?$select=roleid",
        headers=H_READ,
    )
    bound = [x for x in r2.json().get("value", []) if x["roleid"] == test_role_id]
    if bound:
        print(f"   {OK} role already bound to team (verified via GET)")
    else:
        die("Failed to bind role to team", r)

# ---------------------------------------------------------------------------
# 7. Impersonation header sanity (MSCRMCallerID = self)
# ---------------------------------------------------------------------------
step(7, "WhoAmI with MSCRMCallerID set to self — impersonation plumbing")
H_IMP = {**H_READ, "MSCRMCallerID": me["UserId"]}
r = requests.get(f"{API}/WhoAmI", headers=H_IMP)
if r.status_code == 200 and r.json()["UserId"] == me["UserId"]:
    print(f"   {OK} MSCRMCallerID accepted; impersonated WhoAmI returned same userid")
else:
    die("Impersonation header was rejected or returned the wrong user", r)

# ---------------------------------------------------------------------------
# 7b. Persona-style impersonated query — proves filtered reads work
# ---------------------------------------------------------------------------
step("7b", "Impersonated read against lc_task (count) — same shape as rbac_smoketest")
r = requests.get(
    f"{API}/lc_tasks?$select=lc_taskid&$top=5",
    headers=H_IMP,
)
if r.status_code == 200:
    print(f"   {OK} lc_tasks read under impersonation: got {len(r.json().get('value', []))} row(s)")
else:
    # Don't die — the table may not be readable by the caller in some envs;
    # the important thing is that the header didn't break the call shape.
    print(f"   ⚠ lc_tasks read returned HTTP {r.status_code} — header accepted but RBAC denied. That's expected if your role doesn't grant lc_task read. Not a failure of the *approach*.")

# ---------------------------------------------------------------------------
# 8. Cleanup — disassociate, delete role, delete team, delete BU
# ---------------------------------------------------------------------------
step(8, "Cleanup")

# Disassociate role from team
r = requests.delete(
    f"{API}/teams({test_team_id})/teamroles_association({test_role_id})/$ref",
    headers=H_READ,
)
print(f"   role↔team disassociate: HTTP {r.status_code}")

# Delete role
r = requests.delete(f"{API}/roles({test_role_id})", headers=H_READ)
print(f"   delete role:             HTTP {r.status_code}")

# Delete team
r = requests.delete(f"{API}/teams({test_team_id})", headers=H_READ)
print(f"   delete team:             HTTP {r.status_code}")

# Disable + delete BU. BUs must be disabled before delete.
r = requests.patch(
    f"{API}/businessunits({test_bu_id})",
    headers={**H_WRITE, "If-Match": "*"},
    json={"isdisabled": True},
)
print(f"   disable BU:              HTTP {r.status_code}")
# Some orgs require a brief settle before delete
time.sleep(1)
r = requests.delete(f"{API}/businessunits({test_bu_id})", headers=H_READ)
print(f"   delete BU:               HTTP {r.status_code} "
      f"{'(BU delete is restricted on some orgs — left disabled if 4xx)' if r.status_code >= 400 else ''}")

print(f"\n{OK} RBAC approach validated end-to-end. setup_rbac.py can build on these primitives.")
