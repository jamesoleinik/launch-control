"""RBAC + data-masking visualizer for Launch Control.

A tiny Flask app that makes Episode 8 visible: pick a persona, and the page runs
*the same* launch query as that user and shows two things side by side:

  1. Row-level security  - how many lc_* rows each persona can read.
  2. Data masking        - whether the sensitive columns (lc_blockerreason,
                            lc_risksummary) come back as cleartext or ********.

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
from pathlib import Path

from flask import Flask, render_template_string, request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SNAPSHOT = HERE / "samples" / "snapshot.json"

# Columns protected by the Episode 8 field security profile. Absent/null on a
# readable row means the caller is outside the profile -> render as masked.
SECURED_COLUMNS = ("lc_blockerreason", "lc_risksummary")
MASK = "\u2588" * 8  # ████████

# The lc teams created in Part 2; each maps a persona to its owner-team.
TEAM_BY_PERSONA = {
    "member": "lc Members",
    "owner": "lc Owners",
    "viewer": "lc Viewers",
    "admin": "lc Admins",
}

app = Flask(__name__)
app.config["MOCK"] = False


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
def _live():
    """Lazy-import the live dependencies so --mock has no hard requirements."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import requests  # noqa: E402
    from auth import get_token  # noqa: E402

    url = os.environ["DATAVERSE_URL"].rstrip("/")
    api = url + "/api/data/v9.2"
    headers = {
        "Authorization": f"Bearer {get_token()}",
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
        "lc_launch": _count(requests, api, h, "lc_launches"),
        "lc_milestone": _count(requests, api, h, "lc_milestones"),
        "lc_task": _count(requests, api, h, "lc_tasks"),
        "lc_githubissue": _count(requests, api, h, "lc_githubissues"),
    }

    tasks = []
    r = requests.get(
        f"{api}/lc_tasks?$select=lc_name,lc_taskstatus,lc_blockerreason"
        f"&$expand=lc_LaunchId($select=lc_name,lc_risksummary)&$top=20",
        headers=h,
    )
    if r.status_code == 200:
        for row in r.json().get("value", []):
            launch = row.get("lc_LaunchId") or {}
            tasks.append({
                "lc_name": row.get("lc_name"),
                "lc_taskstatus": row.get("lc_taskstatus"),
                # Absent/null secured field => caller outside the profile => masked.
                "lc_blockerreason": row.get("lc_blockerreason"),
                "lc_risksummary": launch.get("lc_risksummary"),
            })
    return {"counts": counts, "tasks": tasks}


# Depth labels returned by RetrieveRolePrivilegesRole -> friendly RBAC scope.
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
        members = [m.get("fullname") or m.get("systemuserid")
                   for m in _vals(requests, api, headers,
                                  f"/fieldsecurityprofiles({pid})/systemuserprofiles_association?$select=systemuserid,fullname")]
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
    return f'<span class="clear">{val}</span>'


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
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #21262d;
           vertical-align: top; }
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
  <form method="get">
    <label for="persona">Impersonate</label>
    <select id="persona" name="persona" onchange="this.form.submit()">
      {% for p in personas %}
        <option value="{{ p.id }}" {{ "selected" if p.id == selected else "" }}>{{ p.label }}</option>
      {% endfor %}
    </select>
    <noscript><button type="submit">Go</button></noscript>
  </form>

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
          <td>{{ render_cell(t, "lc_risksummary")|safe }}</td>
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
    <h2>The policies behind the curtain - who's assigned to what</h2>
    <div class="note" style="margin-top:0;margin-bottom:14px;">This panel is the
      configuration itself, independent of the persona above: the row-level roles
      and column-level profiles enforced by the platform, and the users or teams
      assigned to each.</div>

    <h3 style="font-size:13px;color:#8b949e;margin:6px 0 8px;">Row-level security
      &middot; roles &rarr; privileges &rarr; team &amp; members</h3>
    {% if policies.roles %}
    <table>
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
      &middot; secured column &rarr; profile &amp; masking &rarr; members</h3>
    {% if policies.profiles %}
    <table>
      <thead><tr class="secured">
        <th>Secured column &#128274;</th><th>Profile</th><th>Masking rule</th>
        <th>Read</th><th>Read unmasked</th><th>Create</th><th>Update</th>
        <th>Assigned to</th>
      </tr></thead>
      <tbody>
      {% for pr in policies.profiles %}
        {% for c in pr.columns %}
        <tr>
          <td><code>{{ c.column }}</code></td>
          <td>{{ pr.name }}</td>
          <td>{{ c.rule }}</td>
          <td>{{ c.read }}</td><td>{{ c.readunmasked }}</td>
          <td>{{ c.create }}</td><td>{{ c.update }}</td>
          <td>{% if pr.members %}{{ pr.members|join(", ") }}{% else %}<span class="masked-soft">sysadmin only</span>{% endif %}</td>
        </tr>
        {% endfor %}
      {% endfor %}
      </tbody>
    </table>
    <div class="note">&#128274; = field-secured. "Assigned to" lists the users and
      teams in the profile; <span class="masked-soft">sysadmin only</span> means no
      one is assigned, so only System Administrators can read the column today.</div>
    {% else %}
    <div class="note">No field security profiles secure an lc_* column.</div>
    {% endif %}
  </div>
</main>
</body>
</html>
"""


@app.route("/")
def index():
    mock = app.config["MOCK"]
    if mock:
        personas = mock_personas()
    else:
        personas = live_personas()

    selected = request.args.get("persona") or (personas[0]["id"] if personas else "me")
    lenses = mock_lenses(selected) if mock else live_lenses(personas, selected)
    policies = mock_policies() if mock else live_policies()

    return render_template_string(
        PAGE,
        personas=personas,
        selected=selected,
        counts=lenses["counts"],
        tasks=lenses["tasks"],
        policies=policies,
        render_cell=render_cell,
        mock=mock,
        mask=MASK,
        dv_host=("" if mock else os.environ.get("DATAVERSE_URL", "")),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="RBAC + masking visualizer")
    parser.add_argument("--mock", action="store_true",
                        help="Use the seeded snapshot instead of live Dataverse.")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    # Default to mock when there's no env configured, so first-run never errors.
    app.config["MOCK"] = args.mock or not os.environ.get("DATAVERSE_URL")
    if app.config["MOCK"] and not args.mock:
        print("No DATAVERSE_URL found; starting in DEMO mode. Pass --mock to silence.")

    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
