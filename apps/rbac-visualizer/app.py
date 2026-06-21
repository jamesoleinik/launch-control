"""RBAC + data-masking visualizer for Launch Control.

A tiny Flask app that makes Episode 8 visible: pick a persona, and the page runs
*the same* launch query as that user and shows two things side by side:

  1. Row-level security  - how many lc_* rows each persona can read.
  2. Data masking        - the PII columns on lc_teammember: lc_email with a live
                            on/off masking rule, and lc_fullname with a live
                            column-level-security grant toggle (the Part 3
                            side-by-side demo: flip the state here, Cowork honors
                            it on the same env).

Impersonation is real: in live mode every call carries the `MSCRMCallerID`
header set to the selected user's systemuserid, exactly like the smoke-test.
The platform decides what comes back; this app just renders it.

Run it:
    # Offline demo (seeded snapshot, no Dataverse needed - good for the recording)
    python apps/rbac-visualizer/app.py --mock

    # Live against your environment (uses scripts/auth.py + .env DATAVERSE_URL)
    python apps/rbac-visualizer/app.py

Then open http://127.0.0.1:5000.

Secured columns are flagged below. When a caller is outside the field security
profile, Dataverse omits the secured column from the Web API payload, so the app
treats "present" as cleartext and "absent/null" as masked (********).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SNAPSHOT = HERE / "samples" / "snapshot.json"

# The lc_teammember PII columns (lc_email, lc_fullname) are protected by the
# Episode 8 field security profile. Absent/null on a readable row means the caller
# is outside the profile -> render as masked.
MASK = "\u2588" * 8  # ████████

# --- PII / email masking (Part 3 side-by-side demo) -------------------------
# The lc_teammember.lc_email column is the PII the masking rule protects. The app
# can flip the masking rule on/off live (the same lever as toggle_email_mask.py),
# and Cowork - reading the same environment - honors whichever state is set.
EMAIL_ENTITY = "lc_teammember"
EMAIL_SET = "lc_teammembers"
EMAIL_ATTR = "lc_email"
EMAIL_RULE_NAME = "lc_EmailMask"
EMAIL_BIND_UNIQUENAME = "lc_teammember_lc_email_mask"
EMAIL_RULE_REGEX = r"(?<=.).(?=[^@]*@)"
EMAIL_RULE_CHAR = "#"

# Second PII column on the same table: the team member's real name. lc_name is
# the primary-name field (Dataverse refuses to field-secure it), so the real
# name lives in lc_fullname (securable) and lc_name now holds a non-PII ID.
# Unlike the email (which is masked/obscured), the full name uses pure
# column-level security: when the profile grant is revoked the column is hidden
# entirely (the value comes back null for everyone outside the profile).
NAME_ATTR = "lc_fullname"
PROFILE_NAME = "lc Sensitive Readers"

# We surface three roles spanning the three depth levels (User / Business Unit /
# Organization). The redundant lc Admin role (Org depth like Viewer, plus write)
# is omitted; full control already lives with the System Administrator role.
ROLE_NAMES = {"lc Owner", "lc Member", "lc Viewer"}

# The lc teams created in Part 2; each maps a persona to its owner-team.
TEAM_BY_PERSONA = {
    "member": "lc Members",
    "owner": "lc Owners",
    "viewer": "lc Viewers",
}

app = Flask(__name__)
app.config["MOCK"] = False

# Per-process caches for the persona list and policy lens (both persona-independent).
# Populated on first live request; reused on subsequent persona switches.
_PERSONAS_CACHE: list[dict] | None = None
_POLICIES_CACHE: dict | None = None


# ---------------------------------------------------------------------------
# Mock backend - reads a seeded snapshot so the app runs with zero setup.
# ---------------------------------------------------------------------------
def _load_snapshot() -> dict:
    with open(SNAPSHOT, encoding="utf-8") as fh:
        return json.load(fh)


def mock_personas() -> list[dict]:
    return _load_snapshot()["personas"]


def mock_lenses(persona_id: str) -> dict:
    snap = _load_snapshot()
    return {
        "counts": snap["counts"].get(persona_id, {}),
        "tasks": snap["tasks"].get(persona_id, []),
    }


def mock_policies() -> dict:
    return _load_snapshot().get("policies", {"roles": [], "profiles": []})


# ---------------------------------------------------------------------------
# Live backend - real impersonated Web API calls.
# ---------------------------------------------------------------------------
# Cache the bearer token so we don't re-shell out to `az` on every Web API call
# (each acquisition can cost several seconds; a page load makes dozens of calls).
_TOKEN_CACHE: dict[str, float | str] = {"value": "", "exp": 0.0}


def _cached_token() -> str:
    import time
    if _TOKEN_CACHE["value"] and time.time() < float(_TOKEN_CACHE["exp"]):
        return str(_TOKEN_CACHE["value"])
    sys.path.insert(0, str(ROOT / "scripts"))
    from auth import get_token  # noqa: E402
    tok = get_token()
    _TOKEN_CACHE["value"] = tok
    _TOKEN_CACHE["exp"] = time.time() + 50 * 60  # tokens last ~60 min; refresh early
    return tok


def _live():
    """Lazy-import the live dependencies so --mock has no hard requirements."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import requests  # noqa: E402

    url = os.environ["DATAVERSE_URL"].rstrip("/")
    api = url + "/api/data/v9.2"
    headers = {
        "Authorization": f"Bearer {_cached_token()}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    return requests, api, headers


def _imp(headers: dict, userid: str | None) -> dict:
    return {**headers, "MSCRMCallerID": userid} if userid else headers


def live_personas() -> list[dict]:
    """Discover one impersonatable user per lc team, plus 'me'."""
    requests, api, headers = _live()
    me = requests.get(f"{api}/WhoAmI", headers=headers).json()
    personas = [{"id": "me", "label": "You (no impersonation)", "userid": me["UserId"]}]
    for pid, team_name in TEAM_BY_PERSONA.items():
        team = requests.get(
            f"{api}/teams?$select=teamid,name&$filter=name eq '{team_name}'",
            headers=headers,
        ).json().get("value", [])
        if not team:
            continue
        members = requests.get(
            f"{api}/teams({team[0]['teamid']})/teammembership_association"
            f"?$select=systemuserid,fullname&$top=1",
            headers=headers,
        ).json().get("value", [])
        if not members:
            continue
        m = members[0]
        personas.append({
            "id": pid,
            "label": f"{m.get('fullname') or m['systemuserid']} ({team_name})",
            "userid": m["systemuserid"],
        })
    return personas


def _count(requests, api, headers, entity_set: str) -> int | str:
    r = requests.get(
        f"{api}/{entity_set}?$count=true&$top=1",
        headers={**headers, "Prefer": "odata.maxpagesize=1"},
    )
    if r.status_code != 200:
        return "-"  # caller can't read this surface at all
    return r.json().get("@odata.count", "?")


def live_lenses(personas: list[dict], persona_id: str) -> dict:
    requests, api, headers = _live()
    userid = next((p["userid"] for p in personas if p["id"] == persona_id), None)
    h = _imp(headers, None if persona_id == "me" else userid)

    counts = {
        "lc_launch": _count(requests, api, h, "lc_launchs"),
        "lc_milestone": _count(requests, api, h, "lc_milestones"),
        "lc_task": _count(requests, api, h, "lc_tasks"),
    }

    tasks = []
    r = requests.get(
        f"{api}/lc_tasks?$select=lc_title,lc_taskstatus"
        f"&$expand=lc_launchid($select=lc_name)&$top=200",
        headers={**h, "Prefer": 'odata.maxpagesize=200,'
                 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'},
    )
    if r.status_code == 200:
        fv = "@OData.Community.Display.V1.FormattedValue"
        for row in r.json().get("value", []):
            launch = row.get("lc_launchid") or {}
            tasks.append({
                # lc_task's primary name is lc_title; status is a choice, so use
                # its formatted label rather than the raw option value.
                "lc_name": row.get("lc_title"),
                "lc_taskstatus": row.get("lc_taskstatus" + fv) or row.get("lc_taskstatus"),
                "lc_launch": launch.get("lc_name"),
            })
    return {"counts": counts, "tasks": tasks}


# ---------------------------------------------------------------------------
# Email PII lens + live masking toggle (Part 3 side-by-side demo)
# ---------------------------------------------------------------------------
def mock_emails() -> list[dict]:
    return _load_snapshot().get("emails", [])


def live_emails(personas: list[dict], persona_id: str) -> list[dict]:
    """Read the team-member emails as the selected persona.

    When masking is ON the value comes back redacted (a#########@example.test);
    OFF returns cleartext. A persona outside the field security profile gets the
    column omitted entirely (rendered as the mask block).
    """
    requests, api, headers = _live()
    userid = next((p["userid"] for p in personas if p["id"] == persona_id), None)
    h = _imp(headers, None if persona_id == "me" else userid)
    rows = []
    r = requests.get(
        f"{api}/{EMAIL_SET}?$select=lc_name,{NAME_ATTR},{EMAIL_ATTR}&$top=50", headers=h)
    if r.status_code == 200:
        for m in r.json().get("value", []):
            rows.append({"id": m.get("lc_name"),
                         "fullname": m.get(NAME_ATTR),
                         "email": m.get(EMAIL_ATTR)})
    return rows


def _mask_binding(requests, api, headers, attr) -> str | None:
    """Return the attributemaskingrule binding id for a column, or None if unmasked."""
    rows = _vals(
        requests, api, headers,
        f"/attributemaskingrules?$select=attributemaskingruleid"
        f"&$filter=entityname eq '{EMAIL_ENTITY}' and attributelogicalname eq '{attr}'",
    )
    return rows[0]["attributemaskingruleid"] if rows else None


def _ensure_rule(requests, api, headers, name, displayname, desc, regex, char, testdata) -> str:
    rows = _vals(requests, api, headers,
                 f"/maskingrules?$select=maskingruleid&$filter=name eq '{name}'")
    if rows:
        return rows[0]["maskingruleid"]
    body = {
        "name": name,
        "displayname": displayname,
        "description": desc,
        "regularexpression": regex,
        "maskedcharacter": char,
        "testdata": testdata,
    }
    r = requests.post(api + "/maskingrules",
                      headers={**headers, "Content-Type": "application/json",
                               "Prefer": "return=representation"}, json=body)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"create rule -> {r.status_code}: {r.text[:300]}")
    if r.text:
        return r.json()["maskingruleid"]
    return _vals(requests, api, headers,
                 f"/maskingrules?$select=maskingruleid&$filter=name eq '{name}'")[0]["maskingruleid"]


def _mask_set(attr, bind_uniquename, ensure_rule, mock_key, on: bool) -> None:
    """Attach (on) or detach (off) a column's masking rule. Idempotent."""
    if app.config["MOCK"]:
        app.config[mock_key] = on
        return
    requests, api, headers = _live()
    hw = {**headers, "Content-Type": "application/json"}
    bid = _mask_binding(requests, api, headers, attr)
    if on:
        if bid:
            return
        rid = ensure_rule(requests, api, headers)
        body = {
            "uniquename": bind_uniquename,
            "entityname": EMAIL_ENTITY,
            "attributelogicalname": attr,
            "MaskingRuleId@odata.bind": f"/maskingrules({rid})",
        }
        r = requests.post(api + "/attributemaskingrules", headers=hw, json=body)
        if r.status_code not in (200, 201, 204):
            raise RuntimeError(f"bind -> {r.status_code}: {r.text[:300]}")
    else:
        if not bid:
            return
        r = requests.delete(api + f"/attributemaskingrules({bid})", headers=hw)
        if r.status_code not in (200, 204):
            raise RuntimeError(f"unbind -> {r.status_code}: {r.text[:300]}")


def _ensure_email_rule(requests, api, headers) -> str:
    return _ensure_rule(
        requests, api, headers, EMAIL_RULE_NAME, "LaunchControl email mask",
        "Masks the email local part; reveals the first character and the domain.",
        EMAIL_RULE_REGEX, EMAIL_RULE_CHAR, "avery.chen@example.test")


def email_mask_state() -> bool:
    """True when the lc_email masking rule is attached (redacted)."""
    if app.config["MOCK"]:
        return bool(app.config.get("MOCK_EMAIL_MASK", True))
    requests, api, headers = _live()
    return _mask_binding(requests, api, headers, EMAIL_ATTR) is not None


def email_mask_set(on: bool) -> None:
    _mask_set(EMAIL_ATTR, EMAIL_BIND_UNIQUENAME, _ensure_email_rule, "MOCK_EMAIL_MASK", on)


def _name_fieldperm(requests, api, headers) -> dict | None:
    """The lc_fullname field permission on the Sensitive Readers profile, or None."""
    pids = _vals(requests, api, headers,
                 f"/fieldsecurityprofiles?$select=fieldsecurityprofileid"
                 f"&$filter=name eq '{PROFILE_NAME}'")
    if not pids:
        return None
    pid = pids[0]["fieldsecurityprofileid"]
    rows = _vals(
        requests, api, headers,
        f"/fieldpermissions?$select=fieldpermissionid,canread"
        f"&$filter=_fieldsecurityprofileid_value eq {pid}"
        f" and entityname eq '{EMAIL_ENTITY}' and attributelogicalname eq '{NAME_ATTR}'")
    out = dict(rows[0]) if rows else None
    if out is not None:
        out["_profileid"] = pid
    return out


def name_hidden_state() -> bool:
    """True when lc_fullname read is revoked on the profile (column hidden)."""
    if app.config["MOCK"]:
        return bool(app.config.get("MOCK_NAME_HIDDEN", False))
    requests, api, headers = _live()
    fp = _name_fieldperm(requests, api, headers)
    return fp is None or fp.get("canread") != 4


def name_security_set(hide: bool) -> None:
    """Revoke (hide) or grant (show) lc_fullname column read on the profile.

    This is pure column-level security: with the grant revoked the value comes
    back null for every profile member (and any connected agent), so the field
    is hidden entirely rather than obscured. Idempotent.
    """
    if app.config["MOCK"]:
        app.config["MOCK_NAME_HIDDEN"] = hide
        return
    requests, api, headers = _live()
    hw = {**headers, "Content-Type": "application/json"}
    target = 0 if hide else 4
    fp = _name_fieldperm(requests, api, headers)
    if fp is None:
        pids = _vals(requests, api, headers,
                     f"/fieldsecurityprofiles?$select=fieldsecurityprofileid"
                     f"&$filter=name eq '{PROFILE_NAME}'")
        if not pids:
            raise RuntimeError(f"field security profile '{PROFILE_NAME}' not found")
        body = {"entityname": EMAIL_ENTITY, "attributelogicalname": NAME_ATTR,
                "canread": target,
                "fieldsecurityprofileid@odata.bind":
                f"/fieldsecurityprofiles({pids[0]['fieldsecurityprofileid']})"}
        r = requests.post(api + "/fieldpermissions", headers=hw, json=body)
        if r.status_code not in (200, 201, 204):
            raise RuntimeError(f"grant -> {r.status_code}: {r.text[:300]}")
        return
    if fp.get("canread") == target:
        return
    r = requests.patch(api + f"/fieldpermissions({fp['fieldpermissionid']})",
                       headers=hw, json={"canread": target})
    if r.status_code not in (200, 204):
        raise RuntimeError(f"set canread -> {r.status_code}: {r.text[:300]}")
_DEPTH = {"Basic": "User", "Local": "Business Unit",
          "Deep": "Parent: Child BU", "Global": "Organization"}
# Privilege actions, in the order we like to read them (prv<Action>lc_<table>).
_ACTION_ORDER = ["Create", "Read", "Write", "Delete",
                 "Append", "AppendTo", "Assign", "Share"]
# Field-permission option set values -> labels.
_RWUC = {0: "Not allowed", 4: "Allowed"}
_UNMASK = {0: "Not allowed", 1: "One record", 3: "All records"}


def _vals(requests, api, headers, path: str) -> list[dict]:
    """GET a collection, returning its `value` array or [] on any non-200."""
    r = requests.get(api + path, headers=headers)
    return r.json().get("value", []) if r.status_code == 200 else []


def live_policies() -> dict:
    """Read the actual security policies and who is assigned to each.

    Row-level: every `lc *` security role, its read depth on the lc_* tables,
    the owner-team bound to it, and that team's members.
    Column-level: every field security profile that secures an lc_* column, the
    per-column permissions (decoded to labels) plus the masking rule on the
    column, and the users/teams assigned to the profile.
    """
    requests, api, headers = _live()

    # --- Column masking rules: (entity, attribute) -> rule display name -------
    rules = {r["maskingruleid"]: r.get("name")
             for r in _vals(requests, api, headers, "/maskingrules?$select=maskingruleid,name")}
    col_rule = {
        (a["entityname"], a["attributelogicalname"]): rules.get(a.get("_maskingruleid_value"))
        for a in _vals(
            requests, api, headers,
            "/attributemaskingrules?$select=entityname,attributelogicalname,_maskingruleid_value",
        )
    }

    # --- Row-level: lc roles, their depth, bound team and members -------------
    teams = _vals(
        requests, api, headers,
        "/teams?$select=teamid,name&$filter=startswith(name,'lc ')",
    )
    role_to_team: dict[str, dict] = {}
    for t in teams:
        tid = t["teamid"]
        members = [m.get("fullname") or m.get("systemuserid")
                   for m in _vals(requests, api, headers,
                                  f"/teams({tid})/teammembership_association?$select=systemuserid,fullname")]
        for r in _vals(requests, api, headers,
                       f"/teams({tid})/teamroles_association?$select=roleid,name"):
            role_to_team[r["roleid"]] = {"team": t["name"], "members": members}

    roles = []
    for r in _vals(requests, api, headers,
                   "/roles?$select=roleid,name&$filter=startswith(name,'lc ')"):
        if r["name"] not in ROLE_NAMES:
            continue  # show the three depth-distinct roles; omit lc Admin
        depth, tables, actions = "-", set(), set()
        rp = requests.get(f"{api}/RetrieveRolePrivilegesRole(RoleId={r['roleid']})",
                          headers=headers)
        if rp.status_code == 200:
            for p in rp.json().get("RolePrivileges", []):
                name = p.get("PrivilegeName", "")
                idx = name.find("lc_")
                if not name.startswith("prv") or idx == -1:
                    continue  # only summarize privileges over the lc_* tables
                actions.add(name[3:idx])  # e.g. prvCreatelc_task -> "Create"
                if name.startswith("prvReadlc_"):
                    tables.add(name[len("prvRead"):])
                    if name == "prvReadlc_task" or depth == "-":
                        depth = _DEPTH.get(p.get("Depth"), p.get("Depth"))
        bound = role_to_team.get(r["roleid"], {})
        roles.append({
            "name": r["name"],
            "read_depth": depth,
            "privileges": ", ".join([a for a in _ACTION_ORDER if a in actions]) or "-",
            "table_count": len(tables),
            "team": bound.get("team", "(no team)"),
            "members": bound.get("members", []),
        })
    roles.sort(key=lambda x: x["name"])

    # --- Column-level: field security profiles, permissions, members ----------
    profiles = []
    for p in _vals(requests, api, headers,
                   "/fieldsecurityprofiles?$select=fieldsecurityprofileid,name,description"):
        pid = p["fieldsecurityprofileid"]
        perms = [fp for fp in _vals(
            requests, api, headers,
            f"/fieldpermissions?$filter=_fieldsecurityprofileid_value eq {pid}"
            "&$select=entityname,attributelogicalname,canread,cancreate,canupdate,canreadunmasked",
        ) if fp.get("entityname", "").startswith("lc_")]
        if not perms:
            continue  # skip system/empty profiles that touch no lc_* column
        columns = [{
            "column": f"{fp['entityname']}.{fp['attributelogicalname']}",
            "rule": col_rule.get((fp["entityname"], fp["attributelogicalname"])) or "(none)",
            "read": _RWUC.get(fp.get("canread"), fp.get("canread")),
            "readunmasked": _UNMASK.get(fp.get("canreadunmasked"), fp.get("canreadunmasked")),
            "create": _RWUC.get(fp.get("cancreate"), fp.get("cancreate")),
            "update": _RWUC.get(fp.get("canupdate"), fp.get("canupdate")),
        } for fp in perms]
        # Only list human members: application users (Cowork, DataSync*, and other
        # service principals) all carry the System Administrator profile, which
        # otherwise floods this column with dozens of non-human identities.
        members = [m.get("fullname") or m.get("systemuserid")
                   for m in _vals(requests, api, headers,
                                  f"/fieldsecurityprofiles({pid})/systemuserprofiles_association"
                                  "?$select=systemuserid,fullname,applicationid")
                   if not m.get("applicationid")]
        members += [f"{tm.get('name')} (team)"
                    for tm in _vals(requests, api, headers,
                                    f"/fieldsecurityprofiles({pid})/teamprofiles_association?$select=name")]
        profiles.append({
            "name": p["name"],
            "description": p.get("description") or "",
            "columns": columns,
            "members": members,
        })
    profiles.sort(key=lambda x: x["name"])

    return {"roles": roles, "profiles": profiles}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _perm_summary(col: dict) -> str:
    """Collapse a column's field permissions into one phrase, like role privileges."""
    parts = []
    if col.get("read") not in (None, "Not allowed"):
        parts.append("Read")
    ru = col.get("readunmasked")
    if ru not in (None, "Not allowed"):
        parts.append(f"Read unmasked: {ru}")
    if col.get("create") not in (None, "Not allowed"):
        parts.append("Create")
    if col.get("update") not in (None, "Not allowed"):
        parts.append("Update")
    return ", ".join(parts) or "-"


PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Launch Control - RBAC & Masking Visualizer</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; font: 15px/1.5 -apple-system, Segoe UI, Roboto, sans-serif;
         background: #0d1117; color: #e6edf3; }
  header { padding: 20px 28px; border-bottom: 1px solid #21262d; }
  h1 { margin: 0 0 4px; font-size: 19px; }
  .sub { color: #8b949e; font-size: 13px; }
  main { padding: 24px 28px; max-width: 980px; }
  form { margin-bottom: 22px; }
  label { font-size: 13px; color: #8b949e; margin-right: 10px; }
  select { background: #161b22; color: #e6edf3; border: 1px solid #30363d;
           border-radius: 6px; padding: 8px 12px; font-size: 14px; }
  .lens { background: #161b22; border: 1px solid #21262d; border-radius: 10px;
          padding: 18px 20px; margin-bottom: 20px; }
  .lens h2 { margin: 0 0 12px; font-size: 14px; text-transform: uppercase;
             letter-spacing: .06em; color: #58a6ff; }
  .counts { display: flex; flex-wrap: wrap; gap: 10px; }
  .chip { background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
          padding: 8px 14px; }
  .chip b { font-size: 20px; display: block; }
  .chip span { font-size: 12px; color: #8b949e; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }
  .policy-table { table-layout: fixed; }
  .policy-table th, .policy-table td { word-break: break-word; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #21262d;
           vertical-align: top; overflow-wrap: anywhere; word-break: break-word; }
  /* Truncate noisy single-token values (e.g. the long masked risksummary) to one
     line with an ellipsis; the full value stays available via the cell tooltip. */
  td.col-trunc { white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                 max-width: 0; }
  th { color: #8b949e; font-weight: 600; }
  .secured th { color: #d29922; }
  .masked { font-family: ui-monospace, monospace; color: #f85149;
            letter-spacing: 1px; }
  .masked-soft { color: #8b949e; font-style: italic; }
  .clear { color: #e6edf3; }
  .pill { font-size: 11px; padding: 2px 8px; border-radius: 999px;
          border: 1px solid #30363d; color: #8b949e; }
  .note { color: #8b949e; font-size: 12px; margin-top: 6px; }
  .mode { float: right; font-size: 12px; color: #8b949e; }
  .mask-state { font-size: 12px; padding: 2px 8px; border-radius: 999px;
                vertical-align: middle; }
  .mask-state.on { color: #f0883e; border: 1px solid #bb6c2b; }
  .mask-state.off { color: #3fb950; border: 1px solid #2c6b32; }
  .toggle-form { display: flex; align-items: center; gap: 12px;
                 flex-wrap: wrap; margin: 4px 0 10px; }
  .mask-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
              padding: 8px 0; border-top: 1px solid #21262d; }
  .mask-row .toggle-form { margin: 0; }
  .toggle-btn { cursor: pointer; font-size: 13px; font-weight: 600;
                padding: 7px 14px; border-radius: 8px; border: 1px solid #30363d;
                color: #e6edf3; background: #21262d; }
  .toggle-btn.on { border-color: #2c6b32; }   /* currently masked -> offer reveal */
  .toggle-btn.off { border-color: #bb6c2b; }  /* currently clear -> offer redact */
  .toggle-btn:hover { background: #30363d; }
  /* Loading overlay shown over the lens panels while a new persona is queried. */
  .lc-lenses { position: relative; }
  .lc-overlay { display: none; position: absolute; inset: 0; z-index: 5;
                border-radius: 10px; background: rgba(13, 17, 23, .72);
                backdrop-filter: blur(1.5px);
                align-items: center; justify-content: center; flex-direction: column;
                gap: 14px; }
  .lc-lenses.loading .lc-overlay { display: flex; }
  .lc-spinner { width: 34px; height: 34px; border-radius: 50%;
                border: 3px solid #30363d; border-top-color: #58a6ff;
                animation: lc-spin .8s linear infinite; }
  .lc-overlay span { font-size: 13px; color: #8b949e; }
  @keyframes lc-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .lc-spinner { animation-duration: 2.4s; } }
</style>
</head>
<body>
<header>
  <span class="mode">{{ "DEMO (seeded snapshot)" if mock else "LIVE - " + dv_host }}</span>
  <h1>Launch Control - RBAC &amp; Data-Masking Visualizer</h1>
  <div class="sub">Same query, every persona. Row counts show row-level security;
    the <b>secured columns</b> show data masking.</div>
</header>
<main>
  <div class="lens">
    <h2>The policies behind the curtain - who's assigned to what</h2>
    <div class="note" style="margin-top:0;margin-bottom:14px;">This panel is the
      configuration itself, independent of the impersonation below: the row-level roles
      and column-level profiles enforced by the platform, and the users or teams
      assigned to each.</div>

    <h3 style="font-size:13px;color:#8b949e;margin:6px 0 8px;">Row-level security
      &middot; roles &rarr; privileges &rarr; team &amp; members</h3>
    {% if policies.roles %}
    <table class="policy-table">
      <colgroup>
        <col style="width:17%"><col style="width:19%"><col style="width:18%">
        <col style="width:16%"><col style="width:14%"><col style="width:16%">
      </colgroup>
      <thead><tr>
        <th>Role</th><th>Privileges (lc_* tables)</th><th>Read depth (lc_task)</th>
        <th>lc_* tables</th><th>Owner team</th><th>Members assigned</th>
      </tr></thead>
      <tbody>
      {% for r in policies.roles %}
        <tr>
          <td><b>{{ r.name }}</b></td>
          <td>{{ r.privileges }}</td>
          <td><span class="pill">{{ r.read_depth }}</span></td>
          <td>{{ r.table_count }}</td>
          <td>{{ r.team }}</td>
          <td>{% if r.members %}{{ r.members|join(", ") }}{% else %}<span class="masked-soft">none</span>{% endif %}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="note">No <code>lc *</code> roles found.</div>
    {% endif %}

    <h3 style="font-size:13px;color:#8b949e;margin:18px 0 8px;">Column-level security
      &middot; profile &rarr; masking &rarr; permissions &rarr; secured column &amp; members</h3>
    {% if policies.profiles %}
    <table class="policy-table">
      <colgroup>
        <col style="width:17%"><col style="width:19%"><col style="width:18%">
        <col style="width:16%"><col style="width:14%"><col style="width:16%">
      </colgroup>
      <thead><tr class="secured">
        <th>Profile</th><th>Masking rule</th><th>Permissions (this column)</th>
        <th>Secured column &#128274;</th><th colspan="2">Assigned to (profile members)</th>
      </tr></thead>
      <tbody>
      {% for pr in policies.profiles %}
        {% for c in pr.columns %}
        <tr>
          <td>{{ pr.name }}</td>
          <td>{{ c.rule }}</td>
          <td>{{ c.permissions }}</td>
          <td><code>{{ c.column }}</code></td>
          <td colspan="2">{% if pr.members %}{{ pr.members|join(", ") }}{% else %}<span class="masked-soft">sysadmin only</span>{% endif %}</td>
        </tr>
        {% endfor %}
      {% endfor %}
      </tbody>
    </table>
    <div class="note">&#128274; = field-secured. Column access is <b>not</b> granted
      through roles: it comes from membership in the field security <b>profile</b>,
      assigned directly to users and teams. "Assigned to" lists those profile members;
      <span class="masked-soft">sysadmin only</span> means none are assigned, so only
      System Administrators can read the column today.</div>
    {% else %}
    <div class="note">No field security profiles secure an lc_* column.</div>
    {% endif %}
  </div>

  <form method="get">
    <label for="persona">Impersonate</label>
    <select id="persona" name="persona" onchange="lcSubmit(this)">
      {% for p in personas %}
        <option value="{{ p.id }}" {{ "selected" if p.id == selected else "" }}>{{ p.label }}</option>
      {% endfor %}
    </select>
    <noscript><button type="submit">Go</button></noscript>
  </form>

  <div id="lc-lenses" class="lc-lenses">
  <div class="lc-overlay"><div class="lc-spinner"></div><span>Querying Dataverse&hellip;</span></div>
  <div class="lens">
    <h2>Axis 1 - Row-level security: rows this persona can read</h2>
    <div class="counts">
      {% for k, v in counts.items() %}
        <div class="chip"><b>{{ v }}</b><span>{{ k }}</span></div>
      {% endfor %}
    </div>
    {% if tasks %}
    <table>
      <thead><tr><th>lc_title</th><th>status</th><th>lc_launch</th></tr></thead>
      <tbody>
      {% for t in tasks %}
        <tr>
          <td>{{ t.lc_name }}</td>
          <td>{{ t.lc_taskstatus }}</td>
          <td>{{ t.lc_launch }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% endif %}
    <div class="note">A persona with User-level depth on lc_task sees only the
      rows it owns; Business-Unit depth sees them all. A blank means no read at all.</div>
  </div>

  <div class="lens">
    <h2>Axis 2 - Data masking
      <span class="pill">lc_teammember</span></h2>
    <div class="sub" style="margin:-4px 0 12px">Two PII columns, two independent
      masking rules. Each toggle flips a Dataverse masking rule live; Cowork,
      reading the same env, honors whichever state is set.</div>

    <div class="mask-row">
      <span class="mask-state {{ 'on' if email_masked else 'off' }}">
        <code>lc_email</code> masking {{ "ON - redacted" if email_masked else "OFF - cleartext" }}</span>
      <form method="post" action="/toggle-mask" class="toggle-form" onsubmit="lcToggle(this)">
        <input type="hidden" name="persona" value="{{ selected }}">
        <input type="hidden" name="to" value="{{ 'off' if email_masked else 'on' }}">
        <button type="submit" class="toggle-btn {{ 'on' if email_masked else 'off' }}">
          {{ "Turn email masking OFF (reveal)" if email_masked else "Turn email masking ON (redact)" }}
        </button>
        <span class="note" style="margin:0">Flips the <code>lc_EmailMask</code> rule.</span>
      </form>
    </div>

    <div class="mask-row">
      <span class="mask-state {{ 'on' if name_hidden else 'off' }}">
        <code>lc_fullname</code> {{ "HIDDEN - column secured" if name_hidden else "VISIBLE - granted" }}</span>
      <form method="post" action="/toggle-name-security" class="toggle-form" onsubmit="lcToggle(this)">
        <input type="hidden" name="persona" value="{{ selected }}">
        <input type="hidden" name="to" value="{{ 'off' if name_hidden else 'on' }}">
        <button type="submit" class="toggle-btn {{ 'on' if name_hidden else 'off' }}">
          {{ "Grant full-name column (show)" if name_hidden else "Revoke full-name column (hide)" }}
        </button>
        <span class="note" style="margin:0">Column-level security: flips the
          <code>lc_fullname</code> read grant on the profile.</span>
      </form>
    </div>

    {% if emails %}
    <table>
      <thead><tr class="secured"><th>lc_name (ID)</th><th>lc_fullname &#128274;</th><th>lc_email &#128274;</th></tr></thead>
      <tbody>
      {% for e in emails %}
        <tr>
          <td>{{ e.id }}</td>
          <td>{% if e.fullname %}<span class="clear">{{ e.fullname }}</span>{% else %}<span class="masked">{{ mask }}</span>{% endif %}</td>
          <td>{% if e.email %}<span class="clear">{{ e.email }}</span>{% else %}<span class="masked">{{ mask }}</span>{% endif %}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    <div class="note">Two different techniques on one table. <b>Email</b> uses a
      <i>masking rule</i> - the value is obscured (<code>a#########@example.test</code>)
      but the column is still returned. <b>Full name</b> uses pure <i>column-level
      security</i> - revoking the grant hides the field entirely (the value comes
      back blank, shown here as <span class="masked">{{ mask }}</span>). The primary
      <code>lc_name</code> column is now a non-PII ID. A non-admin persona (or Cowork,
      reading as a profile member) honors both flips live; the signed-in admin always
      sees cleartext.</div>
    {% else %}
    <div class="note">This persona can't read any lc_teammember rows.</div>
    {% endif %}
  </div>
  </div>
</main>
<script>
  // Preserve scroll position across the persona reload so the page doesn't jump
  // back to the top each time you switch the impersonation account.
  function lcSubmit(sel) {
    try { sessionStorage.setItem('lc_scroll', window.scrollY); } catch (e) {}
    // Show the loading overlay over the lenses. (Don't disable the select -
    // a disabled control isn't submitted, which would drop the persona param.)
    var box = document.getElementById('lc-lenses');
    if (box) { box.classList.add('loading'); }
    sel.form.submit();
  }
  // Same loading affordance when flipping the masking rule (a live Web API write).
  function lcToggle(form) {
    try { sessionStorage.setItem('lc_scroll', window.scrollY); } catch (e) {}
    var box = document.getElementById('lc-lenses');
    if (box) { box.classList.add('loading'); }
    var btn = form.querySelector('button');
    if (btn) { btn.disabled = true; btn.textContent = 'Applying\u2026'; }
    return true;
  }
  (function () {
    var y = null;
    try { y = sessionStorage.getItem('lc_scroll'); } catch (e) {}
    if (y !== null) {
      window.scrollTo(0, parseInt(y, 10));
      try { sessionStorage.removeItem('lc_scroll'); } catch (e) {}
    }
  })();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    mock = app.config["MOCK"]
    if mock:
        personas = mock_personas()
        policies = mock_policies()
    else:
        # Personas and policies don't change when you switch the impersonated user,
        # so compute them once and reuse - only the lens query below is per-persona.
        global _PERSONAS_CACHE, _POLICIES_CACHE
        if _PERSONAS_CACHE is None:
            _PERSONAS_CACHE = live_personas()
        if _POLICIES_CACHE is None:
            _POLICIES_CACHE = live_policies()
        personas = _PERSONAS_CACHE
        policies = _POLICIES_CACHE

    selected = request.args.get("persona") or (personas[0]["id"] if personas else "me")
    lenses = mock_lenses(selected) if mock else live_lenses(personas, selected)
    emails = mock_emails() if mock else live_emails(personas, selected)
    for pr in policies.get("profiles", []):
        for col in pr.get("columns", []):
            col["permissions"] = _perm_summary(col)

    return render_template_string(
        PAGE,
        personas=personas,
        selected=selected,
        counts=lenses["counts"],
        tasks=lenses["tasks"],
        emails=emails,
        email_masked=email_mask_state(),
        name_hidden=name_hidden_state(),
        policies=policies,
        mock=mock,
        mask=MASK,
        dv_host=("" if mock else os.environ.get("DATAVERSE_URL", "")),
    )


@app.route("/toggle-mask", methods=["POST"])
def toggle_mask():
    """Attach/detach the lc_email masking rule live, then return to the page."""
    to_on = request.form.get("to", "on") == "on"
    persona = request.form.get("persona", "")
    try:
        email_mask_set(to_on)
        # The masking-rule binding lands immediately, but the security cache can
        # take a few seconds to settle. Without this pause the redirect re-reads
        # within that window and would render cleartext under an "ON" pill.
        time.sleep(5)
    except Exception as exc:  # surface the failure but keep the app up
        print(f"toggle-mask failed: {exc}")
    return redirect(url_for("index", persona=persona) if persona else url_for("index"))


@app.route("/toggle-name-security", methods=["POST"])
def toggle_name_security():
    """Revoke/grant the lc_fullname column read on the profile, then return."""
    to_hide = request.form.get("to", "on") == "on"
    persona = request.form.get("persona", "")
    try:
        name_security_set(to_hide)
        time.sleep(5)  # let the security cache settle before the redirect re-reads
    except Exception as exc:  # surface the failure but keep the app up
        print(f"toggle-name-security failed: {exc}")
    return redirect(url_for("index", persona=persona) if persona else url_for("index"))


def main() -> None:
    parser = argparse.ArgumentParser(description="RBAC + masking visualizer")
    parser.add_argument("--mock", action="store_true",
                        help="Use the seeded snapshot instead of live Dataverse.")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    # Load .env so DATAVERSE_URL is available for live mode without exporting it
    # by hand. Best-effort: --mock never needs it.
    if not args.mock:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        except Exception:
            pass

    # Default to mock when there's no env configured, so first-run never errors.
    app.config["MOCK"] = args.mock or not os.environ.get("DATAVERSE_URL")
    if app.config["MOCK"] and not args.mock:
        print("No DATAVERSE_URL found; starting in DEMO mode. Pass --mock to silence.")
    if not app.config["MOCK"]:
        print(f"LIVE mode against {os.environ.get('DATAVERSE_URL')}")

    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
