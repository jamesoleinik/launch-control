"""RBAC + data-masking visualizer for Launch Control.

A tiny Flask app that makes Episode 8 visible: pick a persona, and the page runs
*the same* launch query as that user and shows two things side by side:

  1. Row-level security  - how many lc_* rows each persona can read.
  2. Data masking        - whether the sensitive columns (lc_blockerreason,
                            lc_risksummary) come back as cleartext or ████████,
                            plus the PII column lc_teammember.lc_email with a live
                            on/off masking toggle (the Part 3 side-by-side demo:
                            flip the rule here, Cowork honors it on the same env).

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
import html
import json
import os
import sys
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SNAPSHOT = HERE / "samples" / "snapshot.json"

# Columns protected by the Episode 8 field security profile. Absent/null on a
# readable row means the caller is outside the profile -> render as masked.
SECURED_COLUMNS = ("lc_blockerreason", "lc_risksummary")
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
        "lc_githubissue": _count(requests, api, h, "lc_githubissues"),
    }

    tasks = []
    r = requests.get(
        f"{api}/lc_tasks?$select=lc_title,lc_taskstatus,lc_blockerreason"
        f"&$expand=lc_launchid($select=lc_name,lc_risksummary)&$top=200",
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
                # Absent/null secured field => caller outside the profile => masked.
                "lc_blockerreason": row.get("lc_blockerreason"),
                "lc_risksummary": launch.get("lc_risksummary"),
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
    r = requests.get(f"{api}/{EMAIL_SET}?$select=lc_name,{EMAIL_ATTR}&$top=50", headers=h)
    if r.status_code == 200:
        for m in r.json().get("value", []):
            rows.append({"name": m.get("lc_name"), "email": m.get(EMAIL_ATTR)})
    return rows


def _email_mask_binding(requests, api, headers) -> str | None:
    rows = _vals(
        requests, api, headers,
        f"/attributemaskingrules?$select=attributemaskingruleid"
        f"&$filter=entityname eq '{EMAIL_ENTITY}' and attributelogicalname eq '{EMAIL_ATTR}'",
    )
    return rows[0]["attributemaskingruleid"] if rows else None


def email_mask_state() -> bool:
    """True when the lc_email masking rule is attached (redacted)."""
    if app.config["MOCK"]:
        return bool(app.config.get("MOCK_EMAIL_MASK", True))
    requests, api, headers = _live()
    return _email_mask_binding(requests, api, headers) is not None


def _ensure_email_rule(requests, api, headers) -> str:
    rows = _vals(requests, api, headers,
                 f"/maskingrules?$select=maskingruleid&$filter=name eq '{EMAIL_RULE_NAME}'")
    if rows:
        return rows[0]["maskingruleid"]
    body = {
        "name": EMAIL_RULE_NAME,
        "displayname": "LaunchControl email mask",
        "description": "Masks the email local part; reveals the first character and the domain.",
        "regularexpression": EMAIL_RULE_REGEX,
        "maskedcharacter": EMAIL_RULE_CHAR,
        "testdata": "avery.chen@example.test",
    }
    r = requests.post(api + "/maskingrules",
                      headers={**headers, "Content-Type": "application/json",
                               "Prefer": "return=representation"}, json=body)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"create rule -> {r.status_code}: {r.text[:300]}")
    if r.text:
        return r.json()["maskingruleid"]
    return _vals(requests, api, headers,
                 f"/maskingrules?$select=maskingruleid&$filter=name eq '{EMAIL_RULE_NAME}'")[0]["maskingruleid"]


def email_mask_set(on: bool) -> None:
    """Attach (on) or detach (off) the lc_email masking rule. Idempotent."""
    if app.config["MOCK"]:
        app.config["MOCK_EMAIL_MASK"] = on
        return
    requests, api, headers = _live()
    hw = {**headers, "Content-Type": "application/json"}
    bid = _email_mask_binding(requests, api, headers)
    if on:
        if bid:
            return
        rid = _ensure_email_rule(requests, api, headers)
        body = {
            "uniquename": EMAIL_BIND_UNIQUENAME,
            "entityname": EMAIL_ENTITY,
            "attributelogicalname": EMAIL_ATTR,
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
def render_cell(task: dict, col: str) -> str:
    val = task.get(col)
    if val in (None, ""):
        return f'<span class="masked">{MASK}</span>'
    safe = html.escape(str(val))
    # title carries the full value so a truncated cell still reveals it on hover.
    return f'<span class="clear" title="{safe}">{safe}</span>'


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
  .toggle-btn { cursor: pointer; font-size: 13px; font-weight: 600;
                padding: 7px 14px; border-radius: 8px; border: 1px solid #30363d;
                color: #e6edf3; background: #21262d; }
  .toggle-btn.on { border-color: #2c6b32; }   /* currently masked -> offer reveal */
  .toggle-btn.off { border-color: #bb6c2b; }  /* currently clear -> offer redact */
  .toggle-btn:hover { background: #30363d; }
  /* "Hide name column" toggle: instant client-side column hide. */
  .names-toggle { font-size: 12px; color: #8b949e; display: inline-flex;
                  align-items: center; gap: 6px; cursor: pointer; user-select: none; }
  body.hide-names .col-name { display: none; }
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
    <div class="note">A persona with User-level depth on lc_task sees only the
      rows it owns; Business-Unit depth sees them all. A blank means no read at all.</div>
  </div>

  <div class="lens">
    <h2>Axis 2 - Data masking: secured columns
      <span class="pill">lc_blockerreason</span>
      <span class="pill">lc_risksummary</span></h2>
    {% if tasks %}
    <table>
      <thead><tr class="secured">
        <th>lc_name</th><th>status</th>
        <th>lc_blockerreason &#128274;</th><th>lc_risksummary &#128274;</th>
      </tr></thead>
      <tbody>
      {% for t in tasks %}
        <tr>
          <td>{{ t.lc_name }}</td>
          <td>{{ t.lc_taskstatus }}</td>
          <td>{{ render_cell(t, "lc_blockerreason")|safe }}</td>
          <td class="col-trunc">{{ render_cell(t, "lc_risksummary")|safe }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    <div class="note">&#128274; = field-secured. A red
      <span class="masked">{{ mask }}</span> means the caller is outside the
      <code>lc Sensitive Readers</code> profile, so Dataverse withheld the value -
      even though the row itself is readable.</div>
    {% else %}
    <div class="note">This persona can't read any lc_task rows, so there's
      nothing to mask.</div>
    {% endif %}
  </div>

  <div class="lens">
    <h2>Axis 2 (PII) - Data masking: <span class="pill">lc_teammember.lc_email</span>
      <span class="mask-state {{ 'on' if email_masked else 'off' }}">
        masking {{ "ON - redacted" if email_masked else "OFF - cleartext" }}</span></h2>
    <form method="post" action="/toggle-mask" class="toggle-form" onsubmit="lcToggle(this)">
      <input type="hidden" name="persona" value="{{ selected }}">
      <input type="hidden" name="to" value="{{ 'off' if email_masked else 'on' }}">
      <button type="submit" class="toggle-btn {{ 'on' if email_masked else 'off' }}">
        {{ "Turn masking OFF (reveal cleartext)" if email_masked else "Turn masking ON (redact PII)" }}
      </button>
      <span class="note" style="margin:0">Flips the <code>lc_EmailMask</code> rule live.
        Cowork, reading the same env, honors whichever state is set.</span>
    </form>
    <label class="names-toggle" style="margin:0 0 10px;">
      <input type="checkbox" id="hide-names" onchange="lcToggleNames(this)"> Hide name column
    </label>
    {% if emails %}
    <table>
      <thead><tr class="secured"><th class="col-name">lc_name</th><th>lc_email &#128274;</th></tr></thead>
      <tbody>
      {% for e in emails %}
        <tr>
          <td class="col-name">{{ e.name }}</td>
          <td>{% if e.email %}<span class="clear">{{ e.email }}</span>{% else %}<span class="masked">{{ mask }}</span>{% endif %}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    <div class="note">With masking <b>ON</b> every non-admin read (and any connected
      agent) gets the redacted form <code>a#########@example.test</code>; <b>OFF</b>
      returns the real address. The platform enforces it on the read, so the same
      flip is honored in Cowork.</div>
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
  // "Hide name column" toggle: pure client-side, persisted so it survives the
  // persona reload. Toggles a body class the CSS uses to hide .col-name cells.
  function lcApplyNames(hide) {
    document.body.classList.toggle('hide-names', !!hide);
    var cb = document.getElementById('hide-names');
    if (cb) { cb.checked = !!hide; }
  }
  function lcToggleNames(cb) {
    try { sessionStorage.setItem('lc_hide_names', cb.checked ? '1' : '0'); } catch (e) {}
    lcApplyNames(cb.checked);
  }
  (function () {
    var v = null;
    try { v = sessionStorage.getItem('lc_hide_names'); } catch (e) {}
    if (v === '1') { lcApplyNames(true); }
  })();
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
        policies=policies,
        render_cell=render_cell,
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
    except Exception as exc:  # surface the failure but keep the app up
        print(f"toggle-mask failed: {exc}")
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
