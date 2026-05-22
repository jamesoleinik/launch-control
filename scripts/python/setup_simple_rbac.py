"""Create four simple flat roles in the active Dataverse environment.

Per the user's spec:

  Member  — Create/Read/Update only their own records (User-level)
  Owner   — Create/Read/Update all records           (Business-Unit-level)
  Viewer  — Read-only across all records             (Business-Unit-level read)
  Admin   — Team-membership management               (read/write team,
            append systemuser, read role — BU-level)

Scope of "all records" = the unified LaunchControl model — `lc_launch`,
`lc_milestone`, `lc_task`, `lc_statusupdate`, `lc_teammember`. Add more
table logical names to LC_TABLES below to widen the scope.

Baseline assumption
-------------------
These roles are **surgical add-ons** layered on top of the OOB
`Basic User` role (which Microsoft documents as "the minimum privileges
and including privileges to the core business tables" — see
https://learn.microsoft.com/power-platform/admin/security-roles-privileges).

So a real user should be assigned:
    Basic User  +  exactly one of  { lc Member, lc Owner, lc Viewer }
    plus optionally  lc Admin  if they manage team membership.

Without Basic User, a user can't even call WhoAmI, so don't assign these
flat roles on their own.

What the script does
--------------------
1. Resolves the root business unit.
2. Looks up `prv<Op><EntityCamel>` privilege ids (Create/Read/Write[/Append/
   AppendTo]) for every table the roles need.
3. Creates 4 roles in the root BU (Dataverse propagates them to every
   child BU automatically) — idempotent on `lc <role>` name.
4. Calls `AddPrivilegesRole` to apply the depth matrix per role.
5. Creates 4 owner-teams in the root BU — `lc <role>s` — idempotent.
6. Binds each role to its same-named team.
7. If `--add-self` is passed, adds the current user to all four teams
   so you can immediately test (drop with `--remove-self` later).

Re-runs are no-ops once the roles + teams exist (privileges are applied
fresh each time; Dataverse de-dupes them).

Usage:
    python scripts/python/setup_simple_rbac.py            # create / sync
    python scripts/python/setup_simple_rbac.py --add-self # also join all teams
    python scripts/python/setup_simple_rbac.py --remove-self
    python scripts/python/setup_simple_rbac.py --dry-run  # plan only

Auth: uses `scripts/auth.py` (AzureCliCredential by default).
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from auth import get_credential  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))

URL = os.environ["DATAVERSE_URL"].rstrip("/")
API = URL + "/api/data/v9.2"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The custom tables the data-access roles cover. Edit here to widen scope.
LC_TABLES = [
    "lc_launch",
    "lc_milestone",
    "lc_task",
    "lc_statusupdate",
    "lc_teammember",
]

# Dataverse privilege depths.
USER = 1   # Basic — own records only
BU = 2     # Local — every record in the user's BU
ORG = 8    # Global — every record in the org

# Role definitions. Each value is a list of (operation, depth) tuples per
# table family; the script expands them into prv<Op><EntityCamel> privileges.
#
# For Admin, we use a hard-coded list of named privileges against system
# tables (team / systemuser) rather than expanding LC_TABLES.
ROLES = {
    "lc Member": {
        "kind": "lc_tables",
        "ops": [("Create", USER), ("Read", USER), ("Write", USER)],
    },
    "lc Owner": {
        "kind": "lc_tables",
        "ops": [("Create", BU), ("Read", BU), ("Write", BU)],
    },
    "lc Viewer": {
        "kind": "lc_tables",
        "ops": [("Read", BU)],
    },
    "lc Admin": {
        "kind": "named",
        "privileges": [
            # User-management — read users, read/write teams, and
            # Append on BOTH sides of the team↔systemuser M:N so the
            # admin can add and remove team members. Microsoft docs:
            # "For many-to-many relationships, a user must have Append
            #  privilege for both tables being associated or
            #  disassociated."
            #   — security-roles-privileges, "Table privileges"
            ("prvReadUser", BU),
            ("prvAppendUser", BU),
            ("prvReadTeam", BU),
            ("prvWriteTeam", BU),
            ("prvAppendTeam", BU),
            ("prvAppendToTeam", BU),
            ("prvReadRole", BU),  # so Admin can see which roles exist
        ],
    },
}

# Team name = "<role>s" (so "lc Member" → "lc Members").
def team_name_for(role_name: str) -> str:
    return role_name + "s"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dry-run", action="store_true", help="Print the plan, do not write.")
parser.add_argument("--add-self", action="store_true", help="Add the current user to all four teams.")
parser.add_argument("--remove-self", action="store_true", help="Remove the current user from all four teams.")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
print(f"Env: {URL}")
TOK = get_credential().get_token(URL + "/.default").token
H = {
    "Authorization": f"Bearer {TOK}",
    "Accept": "application/json",
    "OData-MaxVersion": "4.0",
    "OData-Version": "4.0",
}
HW = {**H, "Content-Type": "application/json", "Prefer": "return=representation"}


def get_json(path: str) -> dict:
    r = requests.get(API + path, headers=H)
    r.raise_for_status()
    return r.json()


def post_json(path: str, body: dict) -> dict:
    r = requests.post(API + path, headers=HW, json=body)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text[:600]}")
    return r.json() if r.text else {}


# ---------------------------------------------------------------------------
# Step 1 — root BU + me
# ---------------------------------------------------------------------------
me = get_json("/WhoAmI")
my_user_id = me["UserId"]
print(f"Caller userid: {my_user_id}")

bus = get_json("/businessunits?$select=businessunitid,name,_parentbusinessunitid_value")["value"]
root_bu = next(b for b in bus if not b.get("_parentbusinessunitid_value"))
print(f"Root BU: {root_bu['name']} ({root_bu['businessunitid']})")

# ---------------------------------------------------------------------------
# Step 2 — privilege lookup
# ---------------------------------------------------------------------------
# Build the set of privilege names we need.
needed_names: set[str] = set()
for role_name, cfg in ROLES.items():
    if cfg["kind"] == "lc_tables":
        for tbl in LC_TABLES:
            camel = tbl  # Dataverse privilege names use the logical name as-is, lowercase
            for op, _ in cfg["ops"]:
                needed_names.add(f"prv{op}{camel}")
    else:
        for name, _ in cfg["privileges"]:
            needed_names.add(name)

# Look them up.
filter_clause = " or ".join(f"name eq '{n}'" for n in sorted(needed_names))
batches: list[dict] = []
# OData $filter has length limits, so batch by 30 names at a time.
ALL = sorted(needed_names)
for i in range(0, len(ALL), 30):
    chunk = ALL[i : i + 30]
    fl = " or ".join(f"name eq '{n}'" for n in chunk)
    data = get_json(f"/privileges?$select=privilegeid,name&$filter={fl}")
    batches.extend(data["value"])

priv_by_name = {p["name"]: p["privilegeid"] for p in batches}
missing = needed_names - set(priv_by_name.keys())
if missing:
    print("\n❌ Missing privileges in this environment:")
    for n in sorted(missing):
        print(f"   {n}")
    print("\nLikely cause: one of the tables in LC_TABLES does not exist yet "
          "(this script assumes the Ep 1 unified model is published) or the "
          "name casing is wrong. Edit LC_TABLES and re-run.")
    sys.exit(1)
print(f"Resolved {len(priv_by_name)} privilege ids.")

# ---------------------------------------------------------------------------
# Step 3 — build the per-role privilege payload
# ---------------------------------------------------------------------------
def build_priv_payload(role_name: str, cfg: dict) -> list[dict]:
    out: list[dict] = []
    if cfg["kind"] == "lc_tables":
        for tbl in LC_TABLES:
            for op, depth in cfg["ops"]:
                pid = priv_by_name[f"prv{op}{tbl}"]
                out.append({"PrivilegeId": pid, "Depth": _depth_str(depth)})
    else:
        for name, depth in cfg["privileges"]:
            out.append({"PrivilegeId": priv_by_name[name], "Depth": _depth_str(depth)})
    return out


def _depth_str(depth_int: int) -> str:
    # AddPrivilegesRole wants the depth as an enum string, not the bit mask.
    return {USER: "Basic", BU: "Local", 4: "Deep", ORG: "Global"}[depth_int]


plan = {role: build_priv_payload(role, cfg) for role, cfg in ROLES.items()}

print("\n=== Plan ===")
for role, privs in plan.items():
    print(f"  {role:12s}  {len(privs):3d} privileges  team='{team_name_for(role)}'")

if args.dry_run:
    print("\n--dry-run: no changes written.")
    sys.exit(0)

# ---------------------------------------------------------------------------
# Step 4 — upsert roles in root BU
# ---------------------------------------------------------------------------
existing_roles = get_json(
    f"/roles?$select=roleid,name,_businessunitid_value"
    f"&$filter=_businessunitid_value eq {root_bu['businessunitid']}"
)["value"]
roles_by_name = {r["name"]: r["roleid"] for r in existing_roles}

role_id_by_name: dict[str, str] = {}
for role_name in ROLES:
    if role_name in roles_by_name:
        rid = roles_by_name[role_name]
        print(f"  role '{role_name}': exists ({rid})")
    else:
        body = {
            "name": role_name,
            "businessunitid@odata.bind": f"/businessunits({root_bu['businessunitid']})",
        }
        rid = post_json("/roles", body)["roleid"]
        print(f"  role '{role_name}': created ({rid})")
    role_id_by_name[role_name] = rid

# ---------------------------------------------------------------------------
# Step 5 — apply privileges via AddPrivilegesRole
# ---------------------------------------------------------------------------
for role_name, privs in plan.items():
    rid = role_id_by_name[role_name]
    body = {"Privileges": privs}
    r = requests.post(
        f"{API}/roles({rid})/Microsoft.Dynamics.CRM.AddPrivilegesRole",
        headers=HW,
        json=body,
    )
    if r.status_code not in (200, 204):
        print(f"  ❌ AddPrivilegesRole failed for '{role_name}': {r.status_code} {r.text[:400]}")
        sys.exit(1)
    print(f"  role '{role_name}': applied {len(privs)} privileges")

# ---------------------------------------------------------------------------
# Step 6 — upsert teams + bind role
# ---------------------------------------------------------------------------
existing_teams = get_json(
    f"/teams?$select=teamid,name,teamtype"
    f"&$filter=_businessunitid_value eq {root_bu['businessunitid']}"
)["value"]
teams_by_name = {t["name"]: t["teamid"] for t in existing_teams}

team_id_by_role: dict[str, str] = {}
for role_name in ROLES:
    tname = team_name_for(role_name)
    if tname in teams_by_name:
        tid = teams_by_name[tname]
        print(f"  team '{tname}': exists ({tid})")
    else:
        body = {
            "name": tname,
            "description": f"Auto-created by setup_simple_rbac.py — bound to '{role_name}' role.",
            "teamtype": 0,  # Owner team
            "businessunitid@odata.bind": f"/businessunits({root_bu['businessunitid']})",
        }
        tid = post_json("/teams", body)["teamid"]
        print(f"  team '{tname}': created ({tid})")
    team_id_by_role[role_name] = tid

    # Bind role to team (idempotent — 4xx on duplicate is fine).
    rid = role_id_by_name[role_name]
    ref = {"@odata.id": f"{API}/roles({rid})"}
    r = requests.post(
        f"{API}/teams({tid})/teamroles_association/$ref",
        headers=HW,
        json=ref,
    )
    if r.status_code == 204:
        print(f"  team '{tname}': role bound")
    else:
        # Verify it's already bound rather than treating as a hard failure.
        bound = get_json(
            f"/teams({tid})/teamroles_association?$select=roleid"
        )["value"]
        if any(x["roleid"] == rid for x in bound):
            print(f"  team '{tname}': role already bound")
        else:
            print(f"  ❌ team '{tname}': bind failed {r.status_code} {r.text[:300]}")
            sys.exit(1)

# ---------------------------------------------------------------------------
# Step 7 — optional --add-self / --remove-self
# ---------------------------------------------------------------------------
if args.add_self or args.remove_self:
    verb = "add" if args.add_self else "remove"
    print(f"\n{verb.title()}ing current user on every team…")
    for role_name, tid in team_id_by_role.items():
        ref = {"@odata.id": f"{API}/systemusers({my_user_id})"}
        if args.add_self:
            r = requests.post(
                f"{API}/teams({tid})/teammembership_association/$ref",
                headers=HW,
                json=ref,
            )
        else:
            r = requests.delete(
                f"{API}/teams({tid})/teammembership_association"
                f"({my_user_id})/$ref",
                headers=H,
            )
        ok = r.status_code in (200, 204)
        marker = "✅" if ok else "⚠"
        suffix = "" if ok else f" — {r.status_code} {r.text[:200]}"
        print(f"  {marker} {verb} self ↔ '{team_name_for(role_name)}'{suffix}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n=== Summary ===")
print(f"{'Role':14s} {'Role ID':38s} {'Team':18s} {'Team ID':38s}")
for role_name in ROLES:
    print(
        f"{role_name:14s} {role_id_by_name[role_name]:38s} "
        f"{team_name_for(role_name):18s} {team_id_by_role[role_name]:38s}"
    )
print("\nDone. Assign users to teams in PPAC → Security → Teams,")
print("or rerun with --add-self / --remove-self to manage your own membership.")
print("\nReminder: these flat roles are designed to layer on top of the OOB")
print("'Basic User' role. A user without Basic User can't even call WhoAmI.")
print("Recommended assignment: Basic User + ONE of { lc Member, lc Owner,")
print("lc Viewer } + optionally lc Admin for team-membership management.")
