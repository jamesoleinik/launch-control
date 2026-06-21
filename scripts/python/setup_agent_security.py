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
  2. Read the same rows / secured columns AS THE AGENT and contrast with a
     privileged human read. Because the agent is no longer a sysadmin and is
     outside the profile, the secured columns come back omitted even though the
     human (cleared, or a System Administrator who bypasses column security)
     reads them fine.
  3. (--demo-grant) Temporarily add the agent to the profile, re-read to show
     cleartext returns, then revoke — restoring the least-privilege end state.

Reading "as the agent": if a client-credentials secret is configured
(`MCP_CLIENT_SECRET` or a `.deploy/ep-08/*.json` artifact) the agent read uses a
real S2S app-only token. Otherwise it falls back to admin impersonation of the
agent's `systemuserid` (the `MSCRMCallerID` header). Dataverse evaluates field
security against the impersonated principal, so the agent's effective column
access is identical either way; the S2S path just proves it under the agent's
own credentials.

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

# Read privileges the Dataverse MCP needs to enumerate the environment on
# connect. System Administrator carried these implicitly; once the agent is
# scoped down they must live on a role it keeps, or Cowork fails to call.
# These are metadata reads only, so they do not weaken the PII column security.
MCP_ENABLEMENT_PRIVS = ["prvReadSolution", "prvReadPublisher"]
MCP_PRIV_HOST_ROLE = "lc Owner"


def admin_headers():
    tok = get_credential().get_token(URL + "/.default").token
    return {"Authorization": f"Bearer {tok}", "Accept": "application/json",
            "OData-MaxVersion": "4.0", "OData-Version": "4.0",
            "Content-Type": "application/json", "Prefer": "return=representation"}


def load_secret():
    # Prefer an env var, then the most recent deploy artifact.
    env_secret = os.environ.get("MCP_CLIENT_SECRET")
    if env_secret:
        return env_secret.strip()
    dd = os.path.join(ROOT, ".deploy", "ep-08")
    if os.path.isdir(dd):
        for f in sorted(os.listdir(dd), reverse=True):
            if f.endswith(".json"):
                return json.load(open(os.path.join(dd, f)))["entra"]["clientSecret"]
    raise SystemExit("Could not find the app client secret (MCP_CLIENT_SECRET / .deploy/ep-08).")


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


def ensure_role_privileges(h, role_id, priv_names):
    """Idempotently add read privileges (Global depth) to a role so the agent,
    once scoped off System Administrator, can still enumerate solutions and
    publishers for the Dataverse MCP. Metadata reads only; no PII exposure."""
    priv_ids = []
    for name in priv_names:
        v = requests.get(
            API + f"/privileges?$select=privilegeid&$filter=name eq '{name}'",
            headers=h).json().get("value", [])
        if v:
            priv_ids.append(v[0]["privilegeid"])
    if not priv_ids:
        return
    body = {"Privileges": [{"PrivilegeId": p, "Depth": "Global"} for p in priv_ids]}
    r = requests.post(
        API + f"/roles({role_id})/Microsoft.Dynamics.CRM.AddPrivilegesRole",
        headers=h, json=body)
    if r.status_code in (200, 204):
        print(f"  ensured MCP read privileges on role: {', '.join(priv_names)}")
    else:
        print(f"  WARN: could not add MCP privileges ({r.status_code}): {r.text[:120]}")


def read_teammember(headers, label):
    """Print the lc_teammember row count and the secured columns on one row.

    A secured column outside the reader's field-security profile is omitted from
    the payload (rendered <omitted>), even when the row itself is readable.
    lc_email also carries the lc_EmailMask rule, so a plain read shows the mask.
    """
    coll = requests.get(
        API + "/lc_teammembers?$select=lc_teammemberid", headers=headers).json()
    if "value" not in coll:
        print(f"  [{label}] cannot read lc_teammember ({str(coll)[:160]})")
        return
    n = len(coll["value"])
    one = requests.get(
        API + "/lc_teammembers?$select=lc_name,lc_fullname,lc_email"
              "&$top=1&$orderby=lc_name", headers=headers).json().get("value", [])
    if not one:
        print(f"  [{label}] rows={n} (no row to sample)")
        return
    r = one[0]
    print(f"  [{label}] rows={n}  "
          f"lc_name={r.get('lc_name', '<omitted>')!r}  "
          f"lc_fullname={r.get('lc_fullname', '<omitted>')!r}  "
          f"lc_email={r.get('lc_email', '<omitted>')!r}")


def agent_context(admin_h, agent_uid):
    """Return (headers, mode) that read AS the agent.

    Prefers a real client-credentials (S2S) token when a secret is configured;
    otherwise falls back to admin impersonation of the agent's systemuserid via
    MSCRMCallerID. Dataverse evaluates field security against the impersonated
    principal, so the agent's effective column access is identical either way.
    """
    try:
        tok = agent_token()
    except SystemExit:
        tok = None
    except Exception as exc:  # network / token errors -> impersonation fallback
        print(f"    (S2S token unavailable: {str(exc)[:120]}; using impersonation)")
        tok = None
    if tok:
        return H(tok), "S2S app-only token"
    base = {k: v for k, v in admin_h.items() if k not in ("Content-Type", "Prefer")}
    return {**base, "MSCRMCallerID": agent_uid}, "admin impersonation (no S2S secret)"


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

        host = role_id.get(MCP_PRIV_HOST_ROLE)
        if host:
            ensure_role_privileges(h, host, MCP_ENABLEMENT_PRIVS)

    # Profile id
    prof = requests.get(
        API + f"/fieldsecurityprofiles?$select=fieldsecurityprofileid&$filter=name eq '{PROFILE_NAME}'",
        headers=h).json()["value"]
    pid = prof[0]["fieldsecurityprofileid"] if prof else None

    print("\n[2] Read the same lc_teammember: human vs. agent")
    print(f"    The agent is outside the '{PROFILE_NAME}' profile and no longer sysadmin.")
    read_teammember(h, "human / me (System Administrator, bypasses column security)")
    ah, mode = agent_context(h, uid)
    print(f"    agent read via: {mode}")
    read_teammember(ah, "agent / least-privilege (outside profile)")

    if args.demo_grant and pid:
        import time
        print("\n[3] Intersection demo: temporarily add the agent to the profile")
        assoc(h, f"/fieldsecurityprofiles({pid})/systemuserprofiles_association/$ref",
              f"/systemusers({uid})")
        time.sleep(5)  # let the security cache settle
        ah, _ = agent_context(h, uid)
        read_teammember(ah, "agent / IN profile")
        disassoc(h, f"/fieldsecurityprofiles({pid})/systemuserprofiles_association/{uid}/$ref")
        time.sleep(5)
        print("  (agent removed from profile again — least-privilege restored)")
        ah, _ = agent_context(h, uid)
        read_teammember(ah, "agent / least-privilege")

    print("\nDone. The agent carries its own field security, enforced as the")
    print("intersection with the human's profile on every read.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
