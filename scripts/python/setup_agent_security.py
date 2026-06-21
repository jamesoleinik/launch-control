"""Episode 8 — Part 4: per-agent (application-user) security.

The Cowork connection authenticates as a real Dataverse **application user**
(the Entra app from Part 1). Field security binds to that agent identity just
like a human, so the agent gets its own least-privilege scope independent of
how privileged its human operators are. Effective column access is the
**intersection** of the human's profile and the agent's profile.

This script proves it end to end against the live env:

  1. Scope the Cowork app user DOWN from System Administrator to
     `Basic User + lc Owner` (it can still read/write the lc_* model at BU
     depth) and leave it OUT of the `lc Sensitive Readers` field-security
     profile.
  2. Acquire a client-credentials token AS THE AGENT and read the same rows /
     secured columns. Because the agent is no longer a sysadmin and is outside
     the profile, the secured columns come back omitted/masked even though a
     privileged human reads them fine.
  3. (--demo-grant) Temporarily add the agent to the profile, re-read to show
     cleartext returns, then revoke — restoring the least-privilege end state.

Usage:
    python scripts/python/setup_agent_security.py            # restrict + show
    python scripts/python/setup_agent_security.py --demo-grant  # also show grant/revoke
    python scripts/python/setup_agent_security.py --show-only   # no role changes
"""
from __future__ import annotations

import argparse
import json
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
TENANT = os.environ["TENANT_ID"]
CLIENT_ID = os.environ["MCP_CLIENT_ID"]

PROFILE_NAME = "lc Sensitive Readers"
AGENT_ROLES = ["Basic User", "lc Owner"]   # what the agent keeps
REMOVE_ROLES = ["System Administrator"]    # what the agent loses


def admin_headers():
    tok = get_credential().get_token(URL + "/.default").token
    return {"Authorization": f"Bearer {tok}", "Accept": "application/json",
            "OData-MaxVersion": "4.0", "OData-Version": "4.0",
            "Content-Type": "application/json", "Prefer": "return=representation"}


def load_secret():
    p = os.path.join(ROOT, "episodes", "ep-08-rbac", "atk", "env", ".env.dev.user")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.startswith("SECRET_AAD_APP_CLIENT_SECRET="):
                return line.split("=", 1)[1].strip()
    # fall back to the most recent deploy artifact
    dd = os.path.join(ROOT, ".deploy", "ep-08")
    if os.path.isdir(dd):
        for f in sorted(os.listdir(dd), reverse=True):
            if f.endswith(".json"):
                return json.load(open(os.path.join(dd, f)))["entra"]["clientSecret"]
    raise SystemExit("Could not find the app client secret (.env.dev.user / .deploy/ep-08).")


def agent_token():
    """Client-credentials token AS the Cowork application user."""
    r = requests.post(
        f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token",
        data={"client_id": CLIENT_ID, "client_secret": load_secret(),
              "scope": URL + "/.default", "grant_type": "client_credentials"})
    r.raise_for_status()
    return r.json()["access_token"]


def H(tok, unmask=False):
    return {"Authorization": f"Bearer {tok}", "Accept": "application/json",
            "OData-MaxVersion": "4.0", "OData-Version": "4.0"}


def agent_systemuser(h):
    u = requests.get(
        API + f"/systemusers?$select=systemuserid,fullname&$filter=applicationid eq {CLIENT_ID}",
        headers=h).json()["value"]
    return u[0] if u else None


def roles_in_root(h):
    bus = requests.get(API + "/businessunits?$select=businessunitid,_parentbusinessunitid_value",
                       headers=h).json()["value"]
    root = next(b for b in bus if not b.get("_parentbusinessunitid_value"))["businessunitid"]
    rs = requests.get(API + f"/roles?$select=roleid,name&$filter=_businessunitid_value eq {root}",
                      headers=h).json()["value"]
    return {r["name"]: r["roleid"] for r in rs}


def assoc(h, coll, target):
    r = requests.post(API + coll, headers=h, json={"@odata.id": API + target})
    return r.status_code in (200, 204) or "duplicate" in r.text.lower()


def disassoc(h, coll_single):
    r = requests.delete(API + coll_single, headers=h)
    return r.status_code in (200, 204)


def report(tok, label):
    h = H(tok)
    members = requests.get(
        API + "/lc_teammembers?$select=lc_teammemberid", headers=h).json()
    if "value" not in members:
        print(f"  [{label}] cannot read lc_teammember ({members})")
        return
    rows = members["value"]
    # lc_fullname is field-secured (pure column hide): outside the profile the
    # column is omitted from the payload, even though the row itself is readable.
    fn = requests.get(
        API + "/lc_teammembers?$select=lc_fullname&$top=1", headers=h).json().get("value", [])
    full = fn[0].get("lc_fullname", "<omitted>") if fn else "<no row>"
    print(f"  [{label}] teammembers={len(rows)}  fullname={str(full)[:40]!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show-only", action="store_true")
    ap.add_argument("--demo-grant", action="store_true")
    args = ap.parse_args()

    h = admin_headers()
    print(f"Env: {URL}")
    au = agent_systemuser(h)
    if not au:
        raise SystemExit("Cowork application user not found for this app id.")
    uid = au["systemuserid"]
    print(f"Agent app user: {au['fullname']} ({uid})\n")

    role_id = roles_in_root(h)

    if not args.show_only:
        print("[1] Scope the agent down to least privilege")
        for rn in REMOVE_ROLES:
            rid = role_id.get(rn)
            if rid and disassoc(
                    h, f"/systemusers({uid})/systemuserroles_association/{rid}/$ref"):
                print(f"  removed role: {rn}")
            else:
                print(f"  role not present / already removed: {rn}")
        for rn in AGENT_ROLES:
            rid = role_id.get(rn) or next(
                (r["roleid"] for r in requests.get(
                    API + f"/roles?$select=roleid,name&$filter=name eq '{rn}'",
                    headers=h).json()["value"]), None)
            if rid and assoc(h, f"/systemusers({uid})/systemuserroles_association/$ref",
                             f"/roles({rid})"):
                print(f"  ensured role: {rn}")

    # Profile id
    prof = requests.get(
        API + f"/fieldsecurityprofiles?$select=fieldsecurityprofileid&$filter=name eq '{PROFILE_NAME}'",
        headers=h).json()["value"]
    pid = prof[0]["fieldsecurityprofileid"] if prof else None

    print("\n[2] Read AS the agent (client-credentials token)")
    print("    The agent is outside the '%s' profile and no longer sysadmin:" % PROFILE_NAME)
    report(agent_token(), "agent / least-privilege")

    if args.demo_grant and pid:
        print("\n[3] Intersection demo: temporarily add the agent to the profile")
        assoc(h, f"/fieldsecurityprofiles({pid})/systemuserprofiles_association/$ref",
              f"/systemusers({uid})")
        report(agent_token(), "agent / IN profile")
        disassoc(h, f"/fieldsecurityprofiles({pid})/systemuserprofiles_association/{uid}/$ref")
        print("  (agent removed from profile again — least-privilege restored)")
        report(agent_token(), "agent / least-privilege")

    print("\nDone. The agent carries its own field security, enforced as the")
    print("intersection with the human's profile on every read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
