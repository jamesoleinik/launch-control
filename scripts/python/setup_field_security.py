"""Episode 8 — Part 3: column-level (field) security + a masking rule.

Idempotent. Targets the active `.env` environment. Requires System Administrator
and a Managed Environment (masking rules need one).

Builds the live column-security model the episode demonstrates:

  Secured column            Table          Masking rule        Profile members read
  ------------------------  -------------  ------------------  --------------------------
  lc_task.lc_blockerreason  lc_task        (none)             cleartext; outsiders: omitted
  lc_launch.lc_risksummary  lc_launch      lc_RiskSummaryMask masked (severity prefix only);
                                                              cleartext with ?UnMaskedData=true
  lc_teammember.lc_email    lc_teammember  (none)             cleartext PII; outsiders: omitted

Steps
-----
1. Secure both columns (`IsSecured = true` on attribute metadata, then publish).
2. Create masking rule `lc_RiskSummaryMask` (regex masks everything after the
   first colon, so the leading severity word survives) and bind it to
   `lc_launch.lc_risksummary` via `attributemaskingrule`.
3. Create field security profile `lc Sensitive Readers`.
4. Grant the profile `canread` on both columns; add `canreadunmasked` on the
   masked column so members can pull cleartext with `?UnMaskedData=true`.
   (canreadunmasked is omitted on the non-masked column — Dataverse 404s it.)
5. Add the Owner persona to the profile; the Member persona is left out so the
   impersonation test shows the column withheld/masked for outsiders.
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
H = {"Authorization": f"Bearer {TOK}", "Accept": "application/json",
     "OData-MaxVersion": "4.0", "OData-Version": "4.0"}
HW = {**H, "Content-Type": "application/json", "Prefer": "return=representation"}

PROFILE_NAME = "lc Sensitive Readers"
MASK_NAME = "lc_RiskSummaryMask"
# Mask every character that follows the first ":" — reveals the leading severity word.
MASK_REGEX = r"(?<=:.*)."
MASK_CHAR = "#"
# Columns to secure: (entity, attribute, has_masking_rule)
SECURED = [
    ("lc_task", "lc_blockerreason", False),
    ("lc_launch", "lc_risksummary", True),
    ("lc_teammember", "lc_email", False),
]
PROFILE_MEMBER = "vivsun@agent365003.onmicrosoft.com"  # Owner persona is cleared


def g(p):
    r = requests.get(API + p, headers=H)
    r.raise_for_status()
    return r.json()


def post(path, body, hdr=None):
    r = requests.post(API + path, headers=hdr or HW, json=body)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text[:500]}")
    return r.json() if r.text else {}


def secure_column(entity, attr):
    meta = g(f"/EntityDefinitions(LogicalName='{entity}')/Attributes(LogicalName='{attr}')"
             f"?$select=LogicalName,MetadataId,IsSecured,AttributeType")
    if meta.get("IsSecured"):
        print(f"  {entity}.{attr}: already secured")
        return
    atype = meta["AttributeType"]
    odata_type = {"Memo": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
                  "String": "Microsoft.Dynamics.CRM.StringAttributeMetadata"}.get(
                      atype, "Microsoft.Dynamics.CRM.AttributeMetadata")
    body = {"@odata.type": "#" + odata_type, "LogicalName": attr, "IsSecured": True}
    r = requests.put(
        f"{API}/EntityDefinitions(LogicalName='{entity}')/Attributes(LogicalName='{attr}')",
        headers={**HW, "MSCRM.MergeLabels": "true", "Consistency": "Strong"}, json=body)
    if r.status_code not in (200, 204):
        raise RuntimeError(f"secure {entity}.{attr} -> {r.status_code}: {r.text[:400]}")
    print(f"  {entity}.{attr}: secured (IsSecured=true)")


def ensure_masking_rule():
    existing = g(f"/maskingrules?$select=maskingruleid,name,regularexpression&$filter=name eq '{MASK_NAME}'")["value"]
    if existing:
        rid = existing[0]["maskingruleid"]
        if existing[0].get("regularexpression") != MASK_REGEX:
            r = requests.patch(API + f"/maskingrules({rid})",
                               headers={**HW, "If-Match": "*"},
                               json={"regularexpression": MASK_REGEX, "maskedcharacter": MASK_CHAR})
            if r.status_code not in (200, 204):
                raise RuntimeError(f"PATCH maskingrule -> {r.status_code}: {r.text[:300]}")
            print(f"  masking rule '{MASK_NAME}': regex updated -> {MASK_REGEX}")
        else:
            print(f"  masking rule '{MASK_NAME}': exists")
        return rid
    body = {
        "name": MASK_NAME,
        "displayname": "LaunchControl risk-summary mask",
        "description": "Masks everything after the first colon; reveals the leading severity word.",
        "regularexpression": MASK_REGEX,
        "maskedcharacter": MASK_CHAR,
    }
    rid = post("/maskingrules", body)["maskingruleid"]
    print(f"  masking rule '{MASK_NAME}': created ({rid})")
    return rid


def bind_masking_rule(entity, attr, rule_id):
    existing = g(f"/attributemaskingrules?$select=attributemaskingruleid"
                 f"&$filter=entityname eq '{entity}' and attributelogicalname eq '{attr}'")["value"]
    if existing:
        print(f"  attributemaskingrule {entity}.{attr}: exists")
        return
    body = {
        "uniquename": f"lc_{entity}_{attr}_mask".replace("lc_lc_", "lc_"),
        "entityname": entity,
        "attributelogicalname": attr,
        "MaskingRuleId@odata.bind": f"/maskingrules({rule_id})",
    }
    post("/attributemaskingrules", body)
    print(f"  attributemaskingrule {entity}.{attr}: bound -> {MASK_NAME}")


def ensure_profile():
    existing = g(f"/fieldsecurityprofiles?$select=fieldsecurityprofileid,name"
                 f"&$filter=name eq '{PROFILE_NAME}'")["value"]
    if existing:
        print(f"  profile '{PROFILE_NAME}': exists")
        return existing[0]["fieldsecurityprofileid"]
    pid = post("/fieldsecurityprofiles",
               {"name": PROFILE_NAME,
                "description": "Members read the secured lc_* sensitive columns."})["fieldsecurityprofileid"]
    print(f"  profile '{PROFILE_NAME}': created ({pid})")
    return pid


def grant_permission(pid, entity, attr, has_mask):
    existing = g(f"/fieldpermissions?$select=fieldpermissionid"
                 f"&$filter=_fieldsecurityprofileid_value eq {pid} "
                 f"and entityname eq '{entity}' and attributelogicalname eq '{attr}'")["value"]
    if existing:
        print(f"  fieldpermission {entity}.{attr}: exists")
        return
    body = {
        "entityname": entity,
        "attributelogicalname": attr,
        "canread": 4,  # Allowed
        "fieldsecurityprofileid@odata.bind": f"/fieldsecurityprofiles({pid})",
    }
    if has_mask:
        body["canreadunmasked"] = 3  # 0=No,1=OneRecord,3=AllRecords — members pull cleartext via ?UnMaskedData=true
    post("/fieldpermissions", body)
    print(f"  fieldpermission {entity}.{attr}: canread=Allowed"
          f"{' + canreadunmasked=Allowed' if has_mask else ''}")


def add_profile_member(pid, domain):
    u = g(f"/systemusers?$select=systemuserid,fullname&$filter=domainname eq '{domain}'")["value"]
    if not u:
        print(f"  profile member {domain}: NOT FOUND")
        return
    uid = u[0]["systemuserid"]
    r = requests.post(
        f"{API}/fieldsecurityprofiles({pid})/systemuserprofiles_association/$ref",
        headers=HW, json={"@odata.id": f"{API}/systemusers({uid})"})
    ok = r.status_code in (200, 204) or "duplicate" in r.text.lower()
    print(f"  profile member {u[0]['fullname']}: {'added' if ok else r.status_code}")


def main() -> int:
    print(f"Env: {URL}")
    print("\n[1] Secure columns")
    for entity, attr, _ in SECURED:
        secure_column(entity, attr)
    print("\n  Publishing customizations...")
    post("/PublishAllXml", {})
    time.sleep(3)

    print("\n[2] Masking rule + binding")
    rule_id = ensure_masking_rule()
    bind_masking_rule("lc_launch", "lc_risksummary", rule_id)

    print("\n[3] Field security profile")
    pid = ensure_profile()

    print("\n[4] Grant column permissions to the profile")
    for entity, attr, has_mask in SECURED:
        grant_permission(pid, entity, attr, has_mask)

    print("\n[5] Add profile members (Owner persona cleared; Member left out)")
    add_profile_member(pid, PROFILE_MEMBER)

    print("\nDone. Column security + masking are live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
