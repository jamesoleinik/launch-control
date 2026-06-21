"""Episode 8 — Part 4 demo toggle: add/remove a user from `lc Sensitive Readers`.

This is the live-demo lever. With the Cowork plugin authenticating delegated
(`OAuthPluginVault`), every read Cowork makes runs as the signed-in human, so
flipping that human's membership in the `lc Sensitive Readers` column-security
profile changes what the *same* Cowork prompt can see, at runtime.

  In  the profile : lc_blockerreason cleartext; lc_risksummary masked (High:#)
  Out the profile : lc_blockerreason omitted (null); the agent can't explain why

Idempotent. Targets the active `.env` environment. Requires System Administrator.

Usage
-----
  python scripts/python/toggle_sensitive_readers.py --user <upn> --in
  python scripts/python/toggle_sensitive_readers.py --user <upn> --out
  python scripts/python/toggle_sensitive_readers.py --user <upn> --status

Defaults to the demo identity (eppc2026demo2) if --user is omitted.
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
TOK = get_credential().get_token(URL + "/.default").token
H = {"Authorization": f"Bearer {TOK}", "Accept": "application/json",
     "OData-MaxVersion": "4.0", "OData-Version": "4.0"}
HW = {**H, "Content-Type": "application/json"}

PROFILE_NAME = "lc Sensitive Readers"
DEFAULT_USER = "eppc2026demo2@agent365003.onmicrosoft.com"


def resolve_profile() -> str:
    r = requests.get(
        f"{API}/fieldsecurityprofiles",
        params={"$select": "fieldsecurityprofileid",
                "$filter": f"name eq '{PROFILE_NAME}'"},
        headers=H)
    r.raise_for_status()
    rows = r.json().get("value", [])
    if not rows:
        sys.exit(f"Field security profile '{PROFILE_NAME}' not found.")
    return rows[0]["fieldsecurityprofileid"]


def resolve_user(upn: str) -> str:
    r = requests.get(
        f"{API}/systemusers",
        params={"$select": "systemuserid,domainname",
                "$filter": f"domainname eq '{upn}'"},
        headers=H)
    r.raise_for_status()
    rows = r.json().get("value", [])
    if not rows:
        sys.exit(f"User '{upn}' not found.")
    return rows[0]["systemuserid"]


def is_member(prof: str, user: str) -> bool:
    r = requests.get(
        f"{API}/fieldsecurityprofiles({prof})/systemuserprofiles_association",
        params={"$select": "systemuserid",
                "$filter": f"systemuserid eq {user}"},
        headers=H)
    r.raise_for_status()
    return bool(r.json().get("value", []))


def add_member(prof: str, user: str) -> None:
    body = {"@odata.id": f"{API}/systemusers({user})"}
    r = requests.post(
        f"{API}/fieldsecurityprofiles({prof})/systemuserprofiles_association/$ref",
        headers=HW, json=body)
    if r.status_code not in (200, 204):
        r.raise_for_status()


def remove_member(prof: str, user: str) -> None:
    r = requests.delete(
        f"{API}/fieldsecurityprofiles({prof})/systemuserprofiles_association"
        f"({user})/$ref",
        headers=HW)
    if r.status_code not in (200, 204):
        r.raise_for_status()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", default=DEFAULT_USER, help="UPN (domainname)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--in", dest="want_in", action="store_true",
                   help="add the user to the profile (cleartext)")
    g.add_argument("--out", dest="want_out", action="store_true",
                   help="remove the user from the profile (masked/omitted)")
    g.add_argument("--status", action="store_true",
                   help="just report current membership")
    args = ap.parse_args()

    prof = resolve_profile()
    user = resolve_user(args.user)
    member = is_member(prof, user)

    if args.status or not (args.want_in or args.want_out):
        state = "IN" if member else "OUT"
        print(f"{args.user} is {state} '{PROFILE_NAME}'.")
        return

    if args.want_in:
        if member:
            print(f"No-op: {args.user} already IN '{PROFILE_NAME}'.")
        else:
            add_member(prof, user)
            print(f"Added {args.user} to '{PROFILE_NAME}' "
                  f"(cleartext blocker reasons; risk summary masked).")
    else:  # want_out
        if not member:
            print(f"No-op: {args.user} already OUT of '{PROFILE_NAME}'.")
        else:
            remove_member(prof, user)
            print(f"Removed {args.user} from '{PROFILE_NAME}' "
                  f"(blocker reasons now omitted on the agent's read).")
    print("Allow a few seconds for the security cache before re-asking Cowork.")


if __name__ == "__main__":
    main()
