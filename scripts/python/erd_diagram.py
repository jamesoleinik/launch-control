"""Episode 3 visual — ERD of the Launch Control data model.

Emits a Mermaid `erDiagram` showing all 10 tables with their key
columns and relationships:

    lc_launch  -|<-  lc_task, lc_milestone
    lc_milestone  -|<-  lc_task
    lc_importrun  -|<-  lc_sourcefile, lc_trackera..e
    lc_trackera..e  -.->  lc_task / lc_milestone   (logical, via lc_stagingsource)

Outputs:
    launch-control/artifacts/erd.mmd       Mermaid source (paste into
                                           mermaid.live or render in any
                                           Markdown that supports Mermaid)
    launch-control/artifacts/erd.png       Rendered via mermaid.ink

Usage:
    python launch-control/scripts/python/erd_diagram.py
"""

from __future__ import annotations

import base64
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


# ---------- Entity definitions (column lists) ----------
#
# Keep each box to ~6 columns max so the diagram stays legible.
# PK first, primary text next, then 1-2 status/priority columns,
# then the lookups (FK columns) that drive the relationships.

ENTITIES: dict[str, list[tuple[str, str, str | None]]] = {
    "lc_launch": [
        ("guid",     "lc_launchid",      "PK"),
        ("string",   "lc_name",          None),
        ("date",     "lc_targetdate",    None),
        ("choice",   "lc_status",        None),
    ],
    "lc_task": [
        ("guid",     "lc_taskid",          "PK"),
        ("string",   "lc_title",           None),
        ("choice",   "lc_taskstatus",      None),
        ("choice",   "lc_priority",        None),
        ("guid",     "lc_launchid",        "FK"),
        ("guid",     "lc_milestoneid",     "FK"),
        ("string",   "lc_stagingsource",   None),
    ],
    "lc_milestone": [
        ("guid",     "lc_milestoneid",     "PK"),
        ("string",   "lc_title",           None),
        ("choice",   "lc_milestonestatus", None),
        ("date",     "lc_duedate",         None),
        ("guid",     "lc_launchid",        "FK"),
        ("string",   "lc_stagingsource",   None),
    ],
    "lc_importrun": [
        ("guid",     "lc_importrunid",     "PK"),
        ("string",   "lc_name",            None),
        ("datetime", "lc_startedat",       None),
        ("int",      "lc_recordsprocessed", None),
        ("choice",   "lc_status",          None),
    ],
    "lc_sourcefile": [
        ("guid",     "lc_sourcefileid",    "PK"),
        ("string",   "lc_filename",        None),
        ("guid",     "lc_importrunid",     "FK"),
    ],
    "lc_trackera": [
        ("guid",     "lc_trackeraid",      "PK"),
        ("string",   "lc_title",           None),
        ("choice",   "lc_status",          None),
        ("choice",   "lc_priority",        None),
        ("string",   "lc_sourcefilename",  None),
        ("guid",     "lc_importrunid",     "FK"),
    ],
    "lc_trackerb": [
        ("guid",     "lc_trackerbid",      "PK"),
        ("string",   "lc_title",           None),
        ("choice",   "lc_status",          None),
        ("choice",   "lc_priority",        None),
        ("string",   "lc_sourcefilename",  None),
        ("guid",     "lc_importrunid",     "FK"),
    ],
    "lc_trackerc": [
        ("guid",     "lc_trackercid",      "PK"),
        ("string",   "lc_name",            None),
        ("choice",   "lc_status",          None),
        ("string",   "lc_quarter",         None),
        ("string",   "lc_sourcefilename",  None),
        ("guid",     "lc_importrunid",     "FK"),
    ],
    "lc_trackerd": [
        ("guid",     "lc_trackerdid",      "PK"),
        ("string",   "lc_name",            None),
        ("choice",   "lc_priority",        None),
        ("string",   "lc_vendor",          None),
        ("string",   "lc_sourcefilename",  None),
        ("guid",     "lc_importrunid",     "FK"),
    ],
    "lc_trackere": [
        ("guid",     "lc_trackereid",      "PK"),
        ("string",   "lc_name",            None),
        ("choice",   "lc_status",          None),
        ("choice",   "lc_priority",        None),
        ("string",   "lc_release",         None),
        ("string",   "lc_sourcefilename",  None),
        ("guid",     "lc_importrunid",     "FK"),
    ],
}

# ---------- Relationships ----------
# (parent, child, label, hard_or_logical)
# hard = real Dataverse lookup; logical = via lc_stagingsource string

RELATIONSHIPS: list[tuple[str, str, str, str]] = [
    ("lc_launch",     "lc_task",        "has",       "hard"),
    ("lc_launch",     "lc_milestone",   "has",       "hard"),
    ("lc_milestone",  "lc_task",        "groups",    "hard"),
    ("lc_importrun",  "lc_sourcefile",  "produced",  "hard"),
    ("lc_importrun",  "lc_trackera",    "ingested",  "hard"),
    ("lc_importrun",  "lc_trackerb",    "ingested",  "hard"),
    ("lc_importrun",  "lc_trackerc",    "ingested",  "hard"),
    ("lc_importrun",  "lc_trackerd",    "ingested",  "hard"),
    ("lc_importrun",  "lc_trackere",    "ingested",  "hard"),
    ("lc_trackera",   "lc_task",        "promoted",  "logical"),
    ("lc_trackerb",   "lc_task",        "promoted",  "logical"),
    ("lc_trackerd",   "lc_task",        "promoted",  "logical"),
    ("lc_trackerc",   "lc_milestone",   "promoted",  "logical"),
    ("lc_trackere",   "lc_milestone",   "promoted",  "logical"),
]


def build_mermaid(include_columns: bool = True) -> str:
    lines: list[str] = ["erDiagram"]

    for parent, child, label, kind in RELATIONSHIPS:
        connector = "||--o{" if kind == "hard" else "}o..o|"
        lines.append(f"    {parent} {connector} {child} : \"{label}\"")

    if include_columns:
        lines.append("")
        for entity, cols in ENTITIES.items():
            lines.append(f"    {entity} {{")
            for typ, name, marker in cols:
                suffix = f" {marker}" if marker else ""
                lines.append(f"        {typ} {name}{suffix}")
            lines.append("    }")

    return "\n".join(lines) + "\n"


def render_via_mermaid_ink(mmd: str, out_path: Path) -> bool:
    """Render the .mmd via mermaid-cli (mmdc), invoked through npx. Returns True on success."""
    import shutil
    import subprocess
    import tempfile

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        print("  npx not found on PATH; cannot auto-render PNG.", file=sys.stderr)
        return False

    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False, encoding="utf-8") as tmp:
        tmp.write(mmd)
        tmp_path = tmp.name
    try:
        cfg = {"theme": "default", "themeVariables": {"fontFamily": "Segoe UI, Inter, sans-serif"}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as cfg_file:
            import json
            json.dump(cfg, cfg_file)
            cfg_path = cfg_file.name
        cmd = [
            npx, "-y", "@mermaid-js/mermaid-cli@latest",
            "-i", tmp_path,
            "-o", str(out_path),
            "-b", "#f8fafc",
            "-w", "1600",
            "-c", cfg_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"  mmdc failed (rc={result.returncode}): {result.stderr.strip()[:300]}", file=sys.stderr)
            return False
        return True
    except Exception as exc:
        print(f"  mmdc render failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return False
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
            Path(cfg_path).unlink(missing_ok=True)
        except Exception:
            pass


def main() -> None:
    mmd = build_mermaid()

    out_dir = ROOT / "artifacts"
    out_dir.mkdir(exist_ok=True)

    mmd_path = out_dir / "erd.mmd"
    mmd_path.write_text(mmd, encoding="utf-8")
    print(f"Wrote {mmd_path.relative_to(ROOT)}  ({len(ENTITIES)} entities, "
          f"{len(RELATIONSHIPS)} relationships)")

    png_path = out_dir / "erd.png"
    if render_via_mermaid_ink(mmd, png_path):
        print(f"Wrote {png_path.relative_to(ROOT)}")
    else:
        print("  Tip: paste artifacts/erd.mmd into https://mermaid.live to preview / export.")


if __name__ == "__main__":
    main()
