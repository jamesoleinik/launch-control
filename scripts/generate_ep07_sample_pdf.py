"""Generate the sample PDF for ep-07.

Produces episodes/ep-07-scout-autopilot/sample-feedback.pdf — a short
beta-tester report seeded with distinctive risk phrases the agent
will pick up via `file_download` during the dedup beat:

- "blocker"
- "escalation"
- "can't ship"
- "customer impact"

The PDF should be uploaded onto the Q3 Widget Launch record before
the recording so that Scout has something to find when it sweeps
SharePoint.

Re-runnable. Overwrites the existing PDF.
"""

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "episodes"
    / "ep-07-scout-autopilot"
    / "sample-feedback.pdf"
)


def main() -> None:
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        leading=15,
        spaceAfter=10,
    )

    story = []
    story.append(Paragraph("Q3 Widget Launch — Beta tester report", h1))
    story.append(Paragraph("Compiled by: Tester Cohort 4 (n=22)", body))
    story.append(Paragraph("Status: draft, for the launch team only", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Summary", h2))
    story.append(
        Paragraph(
            "Overall sentiment is positive on the core workflow. Two issues "
            "from this round rise to the level of escalation and one is a "
            "hard blocker for ship. Customer impact is concentrated in the "
            "first-run experience and the export path.",
            body,
        )
    )

    story.append(Paragraph("Issue 1 — Export path crash on Windows ARM", h2))
    story.append(
        Paragraph(
            "Repro on 6 of 22 testers. The export action raises an unhandled "
            "exception when the destination folder contains a non-ASCII "
            "character. This is a blocker — we cannot ship with a 27% crash "
            "rate on ARM hardware. Estimated customer impact at GA: every "
            "Surface Pro X user who exports.",
            body,
        )
    )

    story.append(Paragraph("Issue 2 — Pricing page disagrees with billing", h2))
    story.append(
        Paragraph(
            "Three testers reported that the per-seat price shown on the "
            "marketing page does not match what their finance team was "
            "quoted. This is an escalation — finance and marketing need to "
            "agree on one number before we open the buy flow.",
            body,
        )
    )

    story.append(Paragraph("Issue 3 — First-run tour terminates early", h2))
    story.append(
        Paragraph(
            "The tour ends after step 2 of 5 if the user resizes the window. "
            "Annoying but not a blocker. Filing for next sprint.",
            body,
        )
    )

    story.append(Paragraph("Verbatim quotes", h2))
    story.append(
        Paragraph(
            "\"We can't ship this to enterprise with the export crash. It "
            "looked great until I tried to share my report.\" — Tester 17",
            body,
        )
    )
    story.append(
        Paragraph(
            "\"The pricing on the website is not what my procurement team "
            "is being told. That has to be resolved before we sign.\" — "
            "Tester 4",
            body,
        )
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=LETTER,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        title="Q3 Widget Launch — Beta tester report",
        author="Launch Control",
    )
    doc.build(story)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
