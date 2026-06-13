"""Generate the Q3 Widget Launch seed-task artifacts.

Emits PDFs into `episodes/ep-07-scout-autopilot/seed-artifacts/`:

- `q3-bug-export-crash.pdf`     attached to the seed bug task on the
                                 export crash. This is the dedup target:
                                 the on-camera `sample-feedback.pdf` is
                                 about the same issue, so the sweep
                                 should match this existing task and
                                 attach the new feedback to it instead
                                 of filing a new row.
- `q3-bug-pricing-mismatch.pdf` attached to the seed bug task on the
                                 pricing-page mismatch. The on-camera
                                 email seeds the same concern; same
                                 dedup target as above.
- `q3-perf-regression.pdf`      attached to the seed perf regression
                                 task. No on-camera match; this exists
                                 to populate the search results so the
                                 dedup tool-use bubble has something to
                                 reject against.

Requires `reportlab`. The bodies are seeded with the same risk
phrases that `sample-feedback.pdf` uses, so when the agent dedups by
calling `file_download` against the candidate task's
`lc_relateddocuments` and reading inside, the right tasks score
above the noise.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUT = (
    Path(__file__).resolve().parent.parent
    / "episodes"
    / "ep-07-scout-autopilot"
    / "seed-artifacts"
)


ARTIFACTS = {
    "q3-bug-export-crash.pdf": [
        "Q3 Widget Launch | Bug Report | Export crash",
        "Filed by: QA Team",
        "",
        "Repro steps:",
        "1. Open the widget designer.",
        "2. Build any composition with more than 10 widgets.",
        "3. Click Export to CSV.",
        "4. The export hangs for 30 seconds, then the app crashes.",
        "",
        "Severity: blocker. We can't ship this to enterprise with the "
        "export crash in place. Customer impact is severe; the export "
        "path is the #1 use case for the design-review workflow.",
        "",
        "Owner: Platform team. Tracking under this lc_task.",
    ],
    "q3-bug-pricing-mismatch.pdf": [
        "Q3 Widget Launch | Bug Report | Pricing page mismatch",
        "Filed by: Pricing Ops",
        "",
        "The pricing page disagrees with billing. The page shows the "
        "Q3 promo tier at $19, but the billing system charges $24. "
        "Escalation: customers who clicked through during the promo "
        "window are being charged the higher number.",
        "",
        "Severity: high. Customer-facing pricing escalation.",
        "Owner: Pricing Ops + Billing. Tracking under this lc_task.",
    ],
    "q3-perf-regression.pdf": [
        "Q3 Widget Launch | Perf Note | First-paint regression",
        "Filed by: Perf Team",
        "",
        "First paint regressed from 380ms to 740ms on the cold-start "
        "path after the Q3 widget bundle was added. Not a blocker for "
        "GA but should be on the watch list.",
        "",
        "Severity: normal. Watch list, not a slip.",
        "Owner: Perf team. Tracking under this lc_task.",
    ],
}


def write_pdf(path: Path, lines: list[str]) -> None:
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontSize = 11
    body.leading = 15
    doc = SimpleDocTemplate(
        str(path), pagesize=letter, title=path.stem, author="LaunchControl Seed"
    )
    flow = []
    for line in lines:
        if not line:
            flow.append(Spacer(1, 8))
            continue
        flow.append(Paragraph(line, body))
    doc.build(flow)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, lines in ARTIFACTS.items():
        out = OUT / name
        write_pdf(out, lines)
        print(f"wrote {out.relative_to(OUT.parent.parent.parent)} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
