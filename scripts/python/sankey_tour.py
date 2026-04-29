"""Episode 3 visual — Sankey of the multi-spreadsheet merge.

Three flowing layers, left to right:

    [ 5 source CSVs ]  ->  [ unified entity ]  ->  [ status bucket ]

Reads live data from Dataverse so the diagram always matches what's
in the org. Outputs:

    launch-control/artifacts/sankey.html   (interactive, drag/zoom)
    launch-control/artifacts/sankey.png    (still frame for video, if kaleido installed)

Requires:
    pip install plotly kaleido

Usage:
    python launch-control/scripts/python/sankey_tour.py
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402

from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402


# Staging table -> (csv source label, target unified entity)
STAGING_MAP = {
    "lc_trackera": ("tracker-a.csv\nEng tasks",       "lc_task"),
    "lc_trackerb": ("tracker-b.csv\nGTM tasks",       "lc_task"),
    "lc_trackerc": ("tracker-c.csv\nQ-milestones",    "lc_milestone"),
    "lc_trackerd": ("tracker-d.csv\nVendor / infra",  "lc_task"),
    "lc_trackere": ("tracker-e.csv\nRelease train",   "lc_milestone"),
}

# Unified status int -> (label, color)
TASK_STATUS = {
    10600020: ("Not started",  "#9ca3af"),
    10600021: ("In progress",  "#2563eb"),
    10600022: ("Done",         "#16a34a"),
    10600023: ("Blocked",      "#dc2626"),
}
MILESTONE_STATUS = {
    10600010: ("Not started",  "#9ca3af"),
    10600011: ("In progress",  "#2563eb"),
    10600012: ("Complete",     "#16a34a"),
    10600013: ("At risk",      "#f59e0b"),
    10600014: ("Blocked",      "#dc2626"),
}

UNIFIED_COLORS = {
    "lc_task":      "#0ea5e9",
    "lc_milestone": "#a855f7",
}
SOURCE_COLOR  = "#475569"
DEFAULT_STATUS_COLOR = "#9ca3af"


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _client()-> DataverseClient:
    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    return DataverseClient(url, get_credential())


def build_sankey(client: DataverseClient) -> go.Figure:
    # 1. Source -> Unified (counts per staging table)
    source_to_unified: dict[tuple[str, str], int] = {}
    for staging, (label, unified) in STAGING_MAP.items():
        df = client.dataframe.get(staging, select=["lc_sourcefilename"])
        source_to_unified[(label, unified)] = len(df)

    # 2. Unified -> Status (from lc_task / lc_milestone)
    unified_to_status: dict[tuple[str, str], int] = defaultdict(int)
    status_colors: dict[str, str] = {}

    task_df = client.dataframe.get("lc_task", select=["lc_taskstatus"])
    for code, group in task_df.groupby("lc_taskstatus"):
        label, color = TASK_STATUS.get(int(code), (f"Status {code}", DEFAULT_STATUS_COLOR))
        unified_to_status[("lc_task", label)] += len(group)
        status_colors[label] = color

    ms_df = client.dataframe.get("lc_milestone", select=["lc_milestonestatus"])
    for code, group in ms_df.groupby("lc_milestonestatus"):
        label, color = MILESTONE_STATUS.get(int(code), (f"Status {code}", DEFAULT_STATUS_COLOR))
        unified_to_status[("lc_milestone", label)] += len(group)
        status_colors[label] = color

    # Build node index (preserve order so layout reads left-to-right)
    nodes: list[str] = []
    node_color: list[str] = []
    idx: dict[str, int] = {}

    def add_node(label: str, color: str) -> int:
        if label not in idx:
            idx[label] = len(nodes)
            nodes.append(label)
            node_color.append(color)
        return idx[label]

    for (src_label, _unified), _n in source_to_unified.items():
        add_node(src_label, SOURCE_COLOR)
    for unified in ("lc_task", "lc_milestone"):
        add_node(unified, UNIFIED_COLORS[unified])
    for (_unified, status_label), _n in unified_to_status.items():
        add_node(status_label, status_colors.get(status_label, DEFAULT_STATUS_COLOR))

    # Build links
    src, tgt, val, link_color = [], [], [], []
    for (src_label, unified), n in source_to_unified.items():
        src.append(idx[src_label])
        tgt.append(idx[unified])
        val.append(n)
        link_color.append(_rgba(UNIFIED_COLORS[unified], 0.35))
    for (unified, status_label), n in unified_to_status.items():
        src.append(idx[unified])
        tgt.append(idx[status_label])
        val.append(n)
        link_color.append(_rgba(status_colors.get(status_label, DEFAULT_STATUS_COLOR), 0.45))

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=nodes,
                color=node_color,
                pad=24,
                thickness=22,
                line=dict(color="#1f2937", width=0.5),
            ),
            link=dict(source=src, target=tgt, value=val, color=link_color),
        )
    )

    total = sum(source_to_unified.values())
    fig.update_layout(
        title=dict(
            text=(
                f"<b>Project Atlas — Smart Widget Pro</b><br>"
                f"<sub>{total} rows across 5 spreadsheets &nbsp;->&nbsp; "
                f"unified in Dataverse &nbsp;->&nbsp; live status</sub>"
            ),
            x=0.5,
            xanchor="center",
        ),
        font=dict(family="Segoe UI, Inter, sans-serif", size=14, color="#0f172a"),
        paper_bgcolor="#f8fafc",
        margin=dict(l=20, r=20, t=80, b=20),
        height=620,
        width=1280,
    )
    return fig


def main() -> None:
    client = _client()
    fig = build_sankey(client)

    out_dir = ROOT / "artifacts"
    out_dir.mkdir(exist_ok=True)

    html_path = out_dir / "sankey.html"
    fig.write_html(str(html_path), include_plotlyjs="cdn")
    print(f"Wrote {html_path.relative_to(ROOT)}")

    png_path = out_dir / "sankey.png"
    try:
        fig.write_image(str(png_path), scale=2)
        print(f"Wrote {png_path.relative_to(ROOT)}")
    except Exception as exc:
        print(f"Skipped PNG export ({exc.__class__.__name__}). "
              f"Run `pip install -U kaleido` to enable static export.")


if __name__ == "__main__":
    main()
