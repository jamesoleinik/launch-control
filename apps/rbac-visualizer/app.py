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

    return render_template_string(
        PAGE,
        personas=personas,
        selected=selected,
        counts=lenses["counts"],
        tasks=lenses["tasks"],
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
