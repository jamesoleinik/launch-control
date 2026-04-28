"""Launch Status Report — HTML Dashboard.

Queries Dataverse via the Python SDK's DataFrame API, then generates
a visual HTML dashboard that opens in the browser.

Usage: python scripts/python/status_report_html.py
"""

import os
import sys
import webbrowser
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient

import pandas as pd


MILESTONE_STATUS = {
    10600010: ("Not Started", "#6c757d", "&#9711;"),
    10600011: ("In Progress", "#0d6efd", "&#9881;"),
    10600012: ("Complete", "#198754", "&#10004;"),
    10600013: ("At Risk", "#ffc107", "&#9888;"),
    10600014: ("Blocked", "#dc3545", "&#10008;"),
}

TASK_STATUS = {
    10600020: ("Not Started", "#6c757d"),
    10600021: ("In Progress", "#0d6efd"),
    10600022: ("Done", "#198754"),
    10600023: ("Blocked", "#dc3545"),
}

LAUNCH_STATUS = {
    10600001: "Planning", 10600002: "In Progress",
    10600003: "Ready for Launch", 10600004: "Launched", 10600005: "On Hold",
}


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")

    with DataverseClient(env_url, get_credential()) as client:
        print("Querying data...")

        launches_df = client.dataframe.get("lc_launch",
            select=["lc_name", "lc_launchstatus", "lc_targetdate"])

        milestones_df = client.dataframe.get("lc_milestone",
            select=["lc_name", "lc_milestonestatus", "lc_duedate", "_lc_launchid_value"])

        tasks_df = client.dataframe.get("lc_task",
            select=["lc_title", "lc_taskstatus", "lc_isblocked", "lc_blockerreason",
                     "lc_duedate", "_lc_milestoneid_value", "_lc_assignedtoid_value"])

        members_df = client.dataframe.get("lc_teammember",
            select=["lc_name", "lc_role", "lc_teammemberid"])

        # Merge tasks with members
        tasks_merged = tasks_df.merge(
            members_df, left_on="_lc_assignedtoid_value",
            right_on="lc_teammemberid", how="left")
        if "lc_name" in tasks_merged.columns:
            tasks_merged = tasks_merged.rename(columns={"lc_name": "owner_name"})

        # Build HTML
        html_parts = [HTML_HEAD]

        for _, launch in launches_df.iterrows():
            launch_name = launch["lc_name"]
            launch_id = launch.get("lc_launchid")
            status = LAUNCH_STATUS.get(launch["lc_launchstatus"], "Unknown")
            target = str(launch.get("lc_targetdate", ""))[:10]

            ms = milestones_df[milestones_df["_lc_launchid_value"] == launch_id].sort_values("lc_duedate")
            total = len(tasks_df)
            done = len(tasks_df[tasks_df["lc_taskstatus"] == 10600022])
            blocked = tasks_merged[tasks_merged["lc_isblocked"] == True]
            pct = (done / total * 100) if total > 0 else 0

            # Header
            html_parts.append(f"""
            <div class="canvas">
            <div class="page-title">
                <h1>{launch_name}</h1>
                <span class="updated">Last updated: {datetime.now().strftime('%b %d, %Y %H:%M')}</span>
            </div>
            """)

            # KPI cards row
            at_risk = len(ms[ms["lc_milestonestatus"] == 10600013])
            complete_ms = len(ms[ms["lc_milestonestatus"] == 10600012])
            html_parts.append(f"""
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="kpi-label">Task Completion</div>
                    <div class="kpi-value kpi-{'green' if pct > 75 else 'yellow' if pct > 40 else 'red'}">{pct:.0f}%</div>
                    <div class="kpi-sub">{done} of {total} tasks done</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Milestones Complete</div>
                    <div class="kpi-value kpi-green">{complete_ms}/{len(ms)}</div>
                    <div class="kpi-sub">{complete_ms} of {len(ms)} milestones</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">At Risk</div>
                    <div class="kpi-value kpi-yellow">{at_risk}</div>
                    <div class="kpi-sub">milestone{'s' if at_risk != 1 else ''} at risk</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Blocked Tasks</div>
                    <div class="kpi-value kpi-red">{len(blocked)}</div>
                    <div class="kpi-sub">requiring escalation</div>
                </div>
            </div>
            """)

            # Two-column: Milestone timeline + Donut chart
            html_parts.append('<div class="card-row">')

            # Left: Milestone Timeline
            html_parts.append('<div class="card"><h2>Milestone Timeline</h2><div class="timeline">')
            ms_list = list(ms.iterrows())
            for idx, (_, m) in enumerate(ms_list):
                s = m["lc_milestonestatus"]
                label, bg, icon = MILESTONE_STATUS.get(s, ("Unknown", "#6c757d", "?"))
                due = str(m.get("lc_duedate", ""))[:10]
                is_last = idx == len(ms_list) - 1
                check_svg = '<svg viewBox="0 0 16 16" fill="white"><path d="M6.5 12L2 7.5l1.4-1.4L6.5 9.2l6.1-6.1L14 4.5z"/></svg>' if s == 10600012 else ''
                html_parts.append(f"""
                <div class="timeline-item">
                    <div class="timeline-track">
                        <div class="timeline-dot" style="background:{bg}">{check_svg}</div>
                        {'<div class="timeline-line"></div>' if not is_last else ''}
                    </div>
                    <div class="timeline-content">
                        <div class="timeline-name">{m['lc_name']}
                            <span class="timeline-badge" style="background:{bg}">{label}</span>
                        </div>
                        <div class="timeline-meta">Due: {due}</div>
                    </div>
                </div>
                """)
            html_parts.append('</div></div>')

            # Right: Donut chart + bar chart
            html_parts.append('<div class="card"><h2>Task Status Distribution</h2>')

            # CSS conic-gradient donut
            task_counts = {}
            for code, (lbl, clr) in TASK_STATUS.items():
                task_counts[lbl] = (len(tasks_df[tasks_df["lc_taskstatus"] == code]), clr)

            # Build conic gradient
            segments = []
            offset = 0
            for lbl, (cnt, clr) in task_counts.items():
                pct_seg = (cnt / total * 100) if total > 0 else 0
                segments.append(f"{clr} {offset:.1f}% {offset + pct_seg:.1f}%")
                offset += pct_seg
            conic = ", ".join(segments)

            html_parts.append(f"""
            <div class="donut-container">
                <div class="donut" style="background: conic-gradient({conic}); display:flex; align-items:center; justify-content:center;">
                    <div style="width:72px;height:72px;border-radius:50%;background:white;display:flex;align-items:center;justify-content:center;">
                        <div class="donut-center">
                            <div class="value">{total}</div>
                            <div class="label">tasks</div>
                        </div>
                    </div>
                </div>
                <div class="donut-legend">
            """)
            for lbl, (cnt, clr) in task_counts.items():
                html_parts.append(f"""
                    <div class="legend-item">
                        <div class="legend-dot" style="background:{clr}"></div>
                        {lbl}: <strong>{cnt}</strong>
                    </div>
                """)
            html_parts.append('</div></div>')

            # Horizontal bar chart
            html_parts.append('<div style="margin-top:24px">')
            for lbl, (cnt, clr) in task_counts.items():
                w = (cnt / total * 100) if total > 0 else 0
                html_parts.append(f"""
                <div class="hbar-row">
                    <div class="hbar-label">{lbl}</div>
                    <div class="hbar-bg">
                        <div class="hbar-fill" style="width:{w:.0f}%;background:{clr}">{cnt}</div>
                    </div>
                </div>
                """)
            html_parts.append('</div></div></div>')

            # Blocked tasks table (full width)
            if len(blocked) > 0:
                html_parts.append("""<div class="card-row card-full">
                <div class="card"><h2>&#9888; Blocked Items</h2>
                <table class="table-blocked">
                    <thead><tr><th>Task</th><th>Owner</th><th>Due Date</th><th>Status</th><th>Blocker Reason</th></tr></thead>
                    <tbody>""")
                for _, t in blocked.iterrows():
                    owner = t.get("owner_name", "Unassigned")
                    reason = t.get("lc_blockerreason", "No reason given")
                    due = str(t.get("lc_duedate", ""))[:10]
                    html_parts.append(f"""
                    <tr>
                        <td><strong>{t['lc_title']}</strong></td>
                        <td>{owner}</td>
                        <td>{due}</td>
                        <td><span class="tag-blocked">BLOCKED</span></td>
                        <td>{reason}</td>
                    </tr>""")
                html_parts.append('</tbody></table></div></div>')

            html_parts.append('</div>')  # close .canvas

        html_parts.append(HTML_FOOTER)
        html = "\n".join(html_parts)

        # Write and open
        out_path = os.path.join(tempfile.gettempdir(), "launch_control_report.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Report saved to: {out_path}")
        webbrowser.open(f"file:///{out_path}")
        print("Opened in browser.")


HTML_HEAD = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Launch Control - Status Report</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', -apple-system, sans-serif;
       background: #f0f2f5; color: #252423; padding: 0; }

/* Power BI top nav bar */
.topbar { background: #1a1a1a; color: white; padding: 12px 32px;
          display: flex; align-items: center; gap: 12px; font-size: 14px; }
.topbar-logo { font-weight: 700; font-size: 16px; }
.topbar-sep { color: #666; }
.topbar-title { color: #ccc; }

/* Canvas area */
.canvas { max-width: 1200px; margin: 24px auto; padding: 0 24px; }

/* Page title row */
.page-title { display: flex; justify-content: space-between; align-items: baseline;
              margin-bottom: 20px; }
.page-title h1 { font-size: 22px; font-weight: 600; color: #252423; }
.page-title .updated { font-size: 12px; color: #797775; }

/* KPI row */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.kpi-card { background: white; border-radius: 4px; padding: 20px 24px;
            box-shadow: 0 1.6px 3.6px rgba(0,0,0,0.13), 0 0.3px 0.9px rgba(0,0,0,0.1); }
.kpi-label { font-size: 12px; color: #797775; text-transform: uppercase; letter-spacing: 0.5px;
             margin-bottom: 8px; }
.kpi-value { font-size: 32px; font-weight: 600; line-height: 1; }
.kpi-sub { font-size: 12px; color: #797775; margin-top: 6px; }
.kpi-green { color: #107c10; }
.kpi-yellow { color: #ca5010; }
.kpi-red { color: #d13438; }
.kpi-blue { color: #0078d4; }

/* Cards */
.card-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.card-full { grid-template-columns: 1fr; }
.card { background: white; border-radius: 4px; padding: 20px 24px;
        box-shadow: 0 1.6px 3.6px rgba(0,0,0,0.13), 0 0.3px 0.9px rgba(0,0,0,0.1); }
.card h2 { font-size: 14px; font-weight: 600; color: #252423; margin-bottom: 16px;
           padding-bottom: 8px; border-bottom: 1px solid #edebe9; }

/* Milestone timeline */
.timeline { display: flex; flex-direction: column; gap: 0; }
.timeline-item { display: flex; align-items: stretch; gap: 16px; min-height: 64px; }
.timeline-track { display: flex; flex-direction: column; align-items: center; width: 24px; }
.timeline-dot { width: 16px; height: 16px; border-radius: 50%; flex-shrink: 0; margin-top: 4px;
                display: flex; align-items: center; justify-content: center; }
.timeline-dot svg { width: 10px; height: 10px; }
.timeline-line { width: 2px; flex: 1; background: #edebe9; margin: 4px 0; }
.timeline-content { flex: 1; padding-bottom: 16px; }
.timeline-name { font-size: 14px; font-weight: 600; }
.timeline-meta { font-size: 12px; color: #797775; margin-top: 2px; }
.timeline-badge { display: inline-block; padding: 2px 8px; border-radius: 2px; font-size: 11px;
                  font-weight: 600; color: white; margin-left: 8px; }

/* Donut chart (pure CSS) */
.donut-container { display: flex; align-items: center; gap: 32px; }
.donut { width: 120px; height: 120px; border-radius: 50%; position: relative; }
.donut-center { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
                text-align: center; }
.donut-center .value { font-size: 28px; font-weight: 700; color: #252423; }
.donut-center .label { font-size: 11px; color: #797775; }
.donut-legend { display: flex; flex-direction: column; gap: 8px; }
.legend-item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.legend-dot { width: 10px; height: 10px; border-radius: 2px; }

/* Horizontal bar chart */
.hbar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.hbar-label { width: 90px; font-size: 13px; text-align: right; color: #605e5c; }
.hbar-bg { flex: 1; height: 24px; background: #f3f2f1; border-radius: 2px; overflow: hidden; }
.hbar-fill { height: 100%; border-radius: 2px; display: flex; align-items: center;
             padding-left: 8px; font-size: 12px; font-weight: 600; color: white;
             min-width: 24px; transition: width 0.5s; }

/* Blocked tasks table */
.table-blocked { width: 100%; border-collapse: collapse; }
.table-blocked th { text-align: left; font-size: 12px; color: #797775; font-weight: 600;
                    padding: 8px 12px; border-bottom: 2px solid #edebe9; }
.table-blocked td { padding: 10px 12px; font-size: 13px; border-bottom: 1px solid #f3f2f1; }
.table-blocked tr:hover { background: #faf9f8; }
.tag-blocked { background: #fde7e9; color: #d13438; padding: 2px 8px; border-radius: 2px;
               font-size: 11px; font-weight: 600; }

/* Footer */
.footer { text-align: center; color: #a19f9d; font-size: 11px; margin: 32px 0 16px; }
.footer a { color: #0078d4; text-decoration: none; }
</style></head><body>

<div class="topbar">
    <span class="topbar-logo">&#9783; Power BI</span>
    <span class="topbar-sep">|</span>
    <span class="topbar-title">Launch Control</span>
</div>
"""

HTML_FOOTER = """
<div class="footer">
    Launch Control &bull; Data from Microsoft Dataverse Python SDK + pandas &bull;
    <a href="https://github.com/jamesoleinik/launch-control">github.com/jamesoleinik/launch-control</a>
</div>
</body></html>"""


if __name__ == "__main__":
    main()
