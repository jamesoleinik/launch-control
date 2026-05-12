"""Visual — 4-tier tree view of the Launch Control data model.

Emits a Mermaid `flowchart TB` showing the data flow as a tree:

    Tier 1 — lc_sourcefile         (raw source files)
       |
    Tier 2 — lc_importrun          (ingest event)
       |
    Tier 3 — lc_trackerA..E        (staging tables, 1 per source system)
       |
    Tier 4 — lc_launch, lc_milestone, lc_task   (unified model)

Solid arrows = hard Dataverse lookups. Dashed arrows = logical
"promoted to" edges (staging rows get unified into a real launch/
milestone/task via the lc_stagingsource string).

Outputs:
    launch-control/artifacts/erd.mmd       Mermaid source (paste into
                                           mermaid.live or render in any
                                           Markdown that supports Mermaid)
    launch-control/artifacts/erd.png       Rendered via mermaid-cli (npx)

Usage:
    python launch-control/scripts/python/erd_diagram.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def build_mermaid() -> str:
    return r"""flowchart TB
    classDef tier1 fill:#fef3c7,stroke:#b45309,stroke-width:1px,color:#1f2937;
    classDef tier2 fill:#dbeafe,stroke:#1d4ed8,stroke-width:1px,color:#1f2937;
    classDef tier3 fill:#e0e7ff,stroke:#4338ca,stroke-width:1px,color:#1f2937;
    classDef tier4 fill:#dcfce7,stroke:#15803d,stroke-width:1.5px,color:#1f2937;

    subgraph T1 [" "]
        direction LR
        SF["<b>lc_sourcefile</b><br/><span style='font-size:11px'>Tier 1 &middot; Raw source file<br/>lc_filename &middot; lc_importrunid</span>"]:::tier1
    end

    subgraph T2 [" "]
        direction LR
        IR["<b>lc_importrun</b><br/><span style='font-size:11px'>Tier 2 &middot; Ingest event<br/>lc_name &middot; lc_startedat<br/>lc_recordsprocessed &middot; lc_status</span>"]:::tier2
    end

    subgraph T3 [" "]
        direction LR
        TA["<b>lc_trackerA</b><br/><span style='font-size:11px'>Tier 3 &middot; Staging<br/>title &middot; status &middot; priority</span>"]:::tier3
        TB["<b>lc_trackerB</b><br/><span style='font-size:11px'>Tier 3 &middot; Staging<br/>title &middot; status &middot; priority</span>"]:::tier3
        TC["<b>lc_trackerC</b><br/><span style='font-size:11px'>Tier 3 &middot; Staging<br/>name &middot; status &middot; quarter</span>"]:::tier3
        TD["<b>lc_trackerD</b><br/><span style='font-size:11px'>Tier 3 &middot; Staging<br/>name &middot; priority &middot; vendor</span>"]:::tier3
        TE["<b>lc_trackerE</b><br/><span style='font-size:11px'>Tier 3 &middot; Staging<br/>name &middot; status &middot; release</span>"]:::tier3
    end

    subgraph T4 [" "]
        direction LR
        L["<b>lc_launch</b><br/><span style='font-size:11px'>Tier 4 &middot; Unified<br/>lc_name &middot; lc_targetdate</span>"]:::tier4
        M["<b>lc_milestone</b><br/><span style='font-size:11px'>Tier 4 &middot; Unified<br/>lc_title &middot; lc_duedate</span>"]:::tier4
        TK["<b>lc_task</b><br/><span style='font-size:11px'>Tier 4 &middot; Unified<br/>lc_title &middot; lc_taskstatus &middot; lc_priority</span>"]:::tier4
    end

    SF -->|"recorded in"| IR
    IR -->|"loads"| TA
    IR -->|"loads"| TB
    IR -->|"loads"| TC
    IR -->|"loads"| TD
    IR -->|"loads"| TE

    TA -.->|"promoted"| TK
    TB -.->|"promoted"| TK
    TD -.->|"promoted"| TK
    TC -.->|"promoted"| M
    TE -.->|"promoted"| M

    L -->|"has"| M
    L -->|"has"| TK
    M -->|"groups"| TK

    style T1 fill:transparent,stroke:transparent
    style T2 fill:transparent,stroke:transparent
    style T3 fill:transparent,stroke:transparent
    style T4 fill:transparent,stroke:transparent
"""


def render_via_mermaid_cli(mmd: str, out_path: Path) -> bool:
    """Render the .mmd via mermaid-cli (mmdc), invoked through npx. Returns True on success."""
    import json
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
    cfg = {
        "theme": "default",
        "themeVariables": {"fontFamily": "Segoe UI, Inter, sans-serif"},
        "flowchart": {"htmlLabels": True, "curve": "basis", "nodeSpacing": 40, "rankSpacing": 70},
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as cfg_file:
        json.dump(cfg, cfg_file)
        cfg_path = cfg_file.name
    try:
        cmd = [
            npx, "-y", "@mermaid-js/mermaid-cli@latest",
            "-i", tmp_path,
            "-o", str(out_path),
            "-b", "#f8fafc",
            "-w", "1800",
            "-c", cfg_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if result.returncode != 0:
            print(f"  mmdc failed (rc={result.returncode}): {result.stderr.strip()[:400]}", file=sys.stderr)
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
    print(f"Wrote {mmd_path.relative_to(ROOT)}  (4-tier tree view)")

    png_path = out_dir / "erd.png"
    if render_via_mermaid_cli(mmd, png_path):
        print(f"Wrote {png_path.relative_to(ROOT)}")
    else:
        print("  Tip: paste artifacts/erd.mmd into https://mermaid.live to preview / export.")


if __name__ == "__main__":
    main()
