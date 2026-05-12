"""Episode 3 visual — flow diagram of the Launch Control data pipeline.

Mermaid flowchart (LR) showing the full pipeline:

    CSVs  ->  staging tables  ->  unified entities  ->  parent launch
                  ^
                  |
            provenance (importrun + sourcefile)

Outputs:
    launch-control/artifacts/flow.mmd
    launch-control/artifacts/flow.png

Usage:
    python launch-control/scripts/python/flow_diagram.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


MERMAID = """flowchart LR

    %% ---------- CSV sources ----------
    subgraph CSVS["5 source spreadsheets"]
        direction TB
        ca[("tracker-a.csv<br/><i>Eng tasks</i>")]
        cb[("tracker-b.csv<br/><i>GTM tasks</i>")]
        cc[("tracker-c.csv<br/><i>Q-milestones</i>")]
        cd[("tracker-d.csv<br/><i>Vendor / infra</i>")]
        ce[("tracker-e.csv<br/><i>Release train</i>")]
    end

    %% ---------- Staging in Dataverse ----------
    subgraph STAGING["Dataverse staging"]
        direction TB
        sa[lc_trackera]
        sb[lc_trackerb]
        sc[lc_trackerc]
        sd[lc_trackerd]
        se[lc_trackere]
    end

    %% ---------- Unified model ----------
    subgraph UNIFIED["Unified model"]
        direction TB
        task[/lc_task/]
        ms[/lc_milestone/]
        launch[["lc_launch<br/><i>Smart Widget Pro Q3</i>"]]
    end

    %% ---------- Provenance (compact box; one anchor edge, others are conceptual) ----------
    subgraph PROV["Provenance<br/><span style='font-size:11px;font-style:italic'>every staging row carries<br/>lc_importrunid + lc_sourcefilename</span>"]
        direction TB
        ir(["lc_importrun"])
        sf(["lc_sourcefile"])
        ir --> sf
    end

    %% ---------- Flows ----------
    ca -- "ingest" --> sa
    cb -- "ingest" --> sb
    cc -- "ingest" --> sc
    cd -- "ingest" --> sd
    ce -- "ingest" --> se

    ir -.-> sa
    ir -.-> se

    sa == "promote" ==> task
    sb == "promote" ==> task
    sd == "promote" ==> task
    sc == "promote" ==> ms
    se == "promote" ==> ms

    task --> launch
    ms  --> launch

    %% ---------- Styling ----------
    classDef csv     fill:#fef3c7,stroke:#b45309,color:#78350f,stroke-width:1px;
    classDef staging fill:#e0e7ff,stroke:#4338ca,color:#1e1b4b,stroke-width:1px;
    classDef prov    fill:#f1f5f9,stroke:#64748b,color:#0f172a,stroke-width:1px,stroke-dasharray:4 3;
    classDef unified fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:1.5px;
    classDef launch  fill:#fde68a,stroke:#b45309,color:#78350f,stroke-width:2px,font-weight:bold;

    class ca,cb,cc,cd,ce csv
    class sa,sb,sc,sd,se staging
    class ir,sf prov
    class task,ms unified
    class launch launch

    linkStyle 0 stroke:#b45309,stroke-width:2px;
    linkStyle 1,2,3,4,5 stroke:#b45309,stroke-width:2px;
    linkStyle 6,7 stroke:#94a3b8,stroke-width:1.2px,stroke-dasharray:5 4;
    linkStyle 8,9,10,11,12 stroke:#15803d,stroke-width:2.5px;
    linkStyle 13,14 stroke:#b45309,stroke-width:2px;

    style CSVS     fill:#fffbeb,stroke:#fbbf24,color:#92400e,padding:20px
    style STAGING  fill:#eef2ff,stroke:#a5b4fc,color:#3730a3,padding:20px
    style PROV     fill:#f8fafc,stroke:#cbd5e1,color:#475569,padding:20px
    style UNIFIED  fill:#f0fdf4,stroke:#86efac,color:#166534,padding:20px
"""


def render_png(mmd: str, out_path: Path) -> bool:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        print("  npx not found; cannot auto-render PNG.", file=sys.stderr)
        return False

    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False, encoding="utf-8") as tmp:
        tmp.write(mmd)
        tmp_path = tmp.name
    cfg = {
        "theme": "default",
        "themeVariables": {"fontFamily": "Segoe UI, Inter, sans-serif", "fontSize": "16px"},
        "flowchart": {
            "htmlLabels": True,
            "curve": "basis",
            "nodeSpacing": 80,
            "rankSpacing": 110,
            "padding": 24,
            "subGraphTitleMargin": {"top": 8, "bottom": 8},
        },
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as cfg_file:
        json.dump(cfg, cfg_file)
        cfg_path = cfg_file.name
    try:
        cmd = [
            npx, "-y", "@mermaid-js/mermaid-cli@latest",
            "-i", tmp_path,
            "-o", str(out_path),
            "-b", "#ffffff",
            "-w", "2400",
            "-c", cfg_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if result.returncode != 0:
            print(f"  mmdc failed (rc={result.returncode}): {result.stderr.strip()[:300]}", file=sys.stderr)
            return False
        return True
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        Path(cfg_path).unlink(missing_ok=True)


def main() -> None:
    out_dir = ROOT / "artifacts"
    out_dir.mkdir(exist_ok=True)

    mmd_path = out_dir / "flow.mmd"
    mmd_path.write_text(MERMAID, encoding="utf-8")
    print(f"Wrote {mmd_path.relative_to(ROOT)}")

    png_path = out_dir / "flow.png"
    if render_png(MERMAID, png_path):
        print(f"Wrote {png_path.relative_to(ROOT)}")
    else:
        print("  Tip: paste artifacts/flow.mmd into https://mermaid.live to preview / export.")


if __name__ == "__main__":
    main()
