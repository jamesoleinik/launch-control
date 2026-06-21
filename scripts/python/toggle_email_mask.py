"""Episode 8 — Cowork email-masking demo toggle.

Showcases data masking on `lc_teammember.lc_email` through Cowork. The signed-in
human stays a member of `lc Sensitive Readers` (so the column always returns); the
toggle attaches or detaches the masking rule on the column:

  mask ON  : Cowork shows a redacted email, e.g. a#########@example.test
  mask OFF : Cowork shows the real address

Binding/unbinding a masking rule takes effect without a publish, so the toggle is
fast enough for a live demo. (A plain Cowork/MCP read never sends
?UnMaskedData=true, so a masked column reads masked regardless of the unmasked
permission. That is why we toggle the rule itself, not a permission, to flip
between masked and cleartext.)

Idempotent. Targets the active `.env` environment. Requires System Administrator
and a Managed Environment (masking rules need one). Leaves risk-summary masking
untouched.

Usage
-----
  python scripts/python/toggle_email_mask.py --on
  python scripts/python/toggle_email_mask.py --off
  python scripts/python/toggle_email_mask.py --status
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

ENTITY = "lc_teammember"
ATTR = "lc_email"
RULE_NAME = "lc_EmailMask"
# Reveal the first character of the local part, mask the rest, keep @domain.
RULE_REGEX = r"(?<=.).(?=[^@]*@)"
RULE_CHAR = "#"
BIND_UNIQUENAME = "lc_teammember_lc_email_mask"


def g(path: str) -> dict:
    r = requests.get(API + path, headers=H)
    r.raise_for_status()
    return r.json()


def ensure_rule() -> str:
    rows = g(f"/maskingrules?$select=maskingruleid&$filter=name eq '{RULE_NAME}'")["value"]
    if rows:
        return rows[0]["maskingruleid"]
    body = {
        "name": RULE_NAME,
        "displayname": "LaunchControl email mask",
        "description": "Masks the email local part; reveals the first character and the domain.",
        "regularexpression": RULE_REGEX,
        "maskedcharacter": RULE_CHAR,
        "testdata": "avery.chen@example.test",
    }
    r = requests.post(API + "/maskingrules",
                      headers={**HW, "Prefer": "return=representation"}, json=body)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"create rule -> {r.status_code}: {r.text[:400]}")
    if r.text:
        rid = r.json()["maskingruleid"]
    else:
        rid = g(f"/maskingrules?$select=maskingruleid&$filter=name eq '{RULE_NAME}'")["value"][0]["maskingruleid"]
    print(f"  masking rule '{RULE_NAME}': created ({rid})")
    return rid


def find_binding() -> str | None:
    rows = g(f"/attributemaskingrules?$select=attributemaskingruleid"
             f"&$filter=entityname eq '{ENTITY}' and attributelogicalname eq '{ATTR}'")["value"]
    return rows[0]["attributemaskingruleid"] if rows else None


def mask_on() -> None:
    if find_binding():
        print(f"No-op: masking already ON for {ENTITY}.{ATTR}.")
        return
    rid = ensure_rule()
    body = {
        "uniquename": BIND_UNIQUENAME,
        "entityname": ENTITY,
        "attributelogicalname": ATTR,
        "MaskingRuleId@odata.bind": f"/maskingrules({rid})",
    }
    r = requests.post(API + "/attributemaskingrules", headers=HW, json=body)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"bind -> {r.status_code}: {r.text[:400]}")
    print(f"Masking ON: {ENTITY}.{ATTR} is now redacted "
          f"(e.g. a#########@example.test) on the agent's read.")
    print("Allow a few seconds for the security cache before re-asking Cowork.")


def mask_off() -> None:
    bid = find_binding()
    if not bid:
        print(f"No-op: masking already OFF for {ENTITY}.{ATTR}.")
        return
    r = requests.delete(API + f"/attributemaskingrules({bid})", headers=HW)
    if r.status_code not in (200, 204):
        raise RuntimeError(f"unbind -> {r.status_code}: {r.text[:400]}")
    print(f"Masking OFF: {ENTITY}.{ATTR} now returns cleartext to profile members.")
    print("Allow a few seconds for the security cache before re-asking Cowork.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    g_ = ap.add_mutually_exclusive_group()
    g_.add_argument("--on", action="store_true", help="attach the mask (redacted)")
    g_.add_argument("--off", action="store_true", help="detach the mask (cleartext)")
    g_.add_argument("--status", action="store_true", help="report mask state")
    args = ap.parse_args()

    if args.on:
        mask_on()
    elif args.off:
        mask_off()
    else:
        state = "ON (redacted)" if find_binding() else "OFF (cleartext)"
        print(f"{ENTITY}.{ATTR} masking is {state}.")


if __name__ == "__main__":
    main()
