"""
Generate FIVE additional Episode 7 Part 2 trigger artifacts (PDFs +
copy/paste cheat-sheet) into episodes/ep-07-scout-autopilot/seed-artifacts/.

These are extra samples modeled on the canonical two in
scripts/generate_q3_trigger_artifacts.py (Email A / Email B). They are
labelled Email C..G so they read as "more, just like those two", and
they give the sweep a deeper bench of findings to act on.

The mix is intentional, so the dedup beat has both outcomes to show:

  - Email C (ENRICH) overlaps the seeded pricing-page-mismatch task
    (q3-bug-pricing-mismatch.pdf): same $19-vs-$24 promo-tier story.
  - Email D (ENRICH) overlaps the seeded first-paint perf regression
    task (q3-perf-regression.pdf): same 380ms -> 740ms cold-start story.
  - Email E (NEW)    accessibility keyboard trap. No seed covers it.
  - Email F (NEW)    autosave data loss on session timeout. No seed
    covers it (and it deliberately avoids export/CSV/crash phrasing so
    it does NOT false-match the export-crash baseline).
  - Email G (NEW)    SharePoint embed blocked by CSP. No seed covers it.

The ENRICH bodies repeat the seeded tasks' risk phrases on purpose so
`search_data` matches inside the attached PDF and the skill enriches the
existing task instead of filing a duplicate. The NEW bodies use distinct
phrasing so they return no in-launch match and file a fresh lc_task.

Emits into seed-artifacts/:
  - Q3-widget-pricing-mismatch-promo.pdf       (Email C attachment)
  - Q3-widget-first-paint-regression.pdf       (Email D attachment)
  - Q3-widget-accessibility-keyboard-trap.pdf  (Email E attachment)
  - Q3-widget-autosave-data-loss.pdf           (Email F attachment)
  - Q3-widget-sharepoint-embed-csp.pdf         (Email G attachment)
  - q3-trigger-emails-extra.md                 (subjects + body text
                                                to paste into Outlook)
"""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUT_DIR = (
    Path(__file__).resolve().parent.parent
    / "episodes"
    / "ep-07-scout-autopilot"
    / "seed-artifacts"
)

RECIPIENT = os.environ.get("Q3_TRIGGER_RECIPIENT", "<recipient-upn>")

EMAILS = [
    {
        "letter": "C",
        "filename": "Q3-widget-pricing-mismatch-promo.pdf",
        "subject": "Q3 Widget Launch - promo tier price on the pricing page does not match the invoice",
        "role": "ENRICH (overlaps the seeded pricing-page mismatch baseline task)",
        "body_lines": [
            "Q3 Widget Launch pricing escalation from a customer ticket.",
            (
                "The pricing page disagrees with billing on the Q3 promo "
                "tier. The page advertises the promo tier at $19, but the "
                "invoice charges $24. Customers who clicked through during "
                "the promo window are being billed the higher amount."
            ),
            (
                "Several inbound tickets already. Severity from the "
                "customer side: high, a customer-facing pricing "
                "escalation. Attached PDF has the screenshot notes and "
                "the two amounts side by side."
            ),
        ],
    },
    {
        "letter": "D",
        "filename": "Q3-widget-first-paint-regression.pdf",
        "subject": "Q3 Widget Launch - cold-start first paint regressed after the widget bundle",
        "role": "ENRICH (overlaps the seeded first-paint perf regression baseline task)",
        "body_lines": [
            "Q3 Widget Launch perf note from the performance dashboard.",
            (
                "First paint regressed from 380ms to 740ms on the "
                "cold-start path after the Q3 widget bundle was added. "
                "The regression reproduces on a clean profile with the "
                "cache cleared."
            ),
            (
                "Not a blocker for GA but it should stay on the watch "
                "list. Attached PDF has the trace summary and the "
                "before/after first-paint numbers."
            ),
        ],
    },
    {
        "letter": "E",
        "filename": "Q3-widget-accessibility-keyboard-trap.pdf",
        "subject": "Q3 Widget Launch - keyboard focus trap in the widget designer",
        "role": "NEW TASK (no existing task on the launch covers this)",
        "body_lines": [
            "Q3 Widget Launch accessibility issue from the a11y review pass.",
            (
                "Keyboard-only users get trapped in the widget property "
                "panel. Once focus enters the panel, Tab and Shift+Tab "
                "cycle inside it and never return to the canvas, so the "
                "rest of the designer is unreachable without a mouse. "
                "NVDA does not announce the panel boundaries."
            ),
            (
                "No existing task on the launch covers this. Filed via "
                "this email so the morning sweep picks it up. Attached "
                "PDF has the steps, the failing WCAG criteria, and the "
                "assistive-tech matrix."
            ),
        ],
    },
    {
        "letter": "F",
        "filename": "Q3-widget-autosave-data-loss.pdf",
        "subject": "Q3 Widget Launch - canvas autosave drops edits after session timeout",
        "role": "NEW TASK (no existing task on the launch covers this)",
        "body_lines": [
            "Q3 Widget Launch data-loss report from the beta cohort.",
            (
                "When a designer session sits idle long enough for the "
                "auth token to refresh, the canvas silently reverts to "
                "the last manual save on the next edit. Any work done "
                "since the last manual save is gone with no warning. "
                "Reproduced twice on the current beta build."
            ),
            (
                "No existing task on the launch covers this. Filed via "
                "this email so the morning sweep picks it up. Attached "
                "PDF has the timeline, the affected build number, and "
                "the repro steps."
            ),
        ],
    },
    {
        "letter": "G",
        "filename": "Q3-widget-sharepoint-embed-csp.pdf",
        "subject": "Q3 Widget Launch - embedded widget blocked by CSP on SharePoint pages",
        "role": "NEW TASK (no existing task on the launch covers this)",
        "body_lines": [
            "Q3 Widget Launch integration issue from a pilot customer.",
            (
                "Embedding a Q3 widget in a SharePoint page fails. The "
                "browser blocks the iframe with a Content-Security-Policy "
                "frame-ancestors violation, and the widget area renders "
                "blank. The same widget loads fine in the standalone app."
            ),
            (
                "No existing task on the launch covers this. Filed via "
                "this email so the morning sweep picks it up. Attached "
                "PDF has the failing page URL, the console error, and "
                "the CSP header that needs the allowance."
            ),
        ],
    },
]


def write_pdf(path: Path, title: str, paragraphs: list[str]) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=LETTER, title=title)
    styles = getSampleStyleSheet()
    story: list = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for p in paragraphs:
        story.append(Paragraph(p, styles["BodyText"]))
        story.append(Spacer(1, 8))
    doc.build(story)


def write_cheatsheet(path: Path) -> None:
    lines = [
        "# Q3 trigger emails - extra batch (Episode 7 Part 2, Setup B)",
        "",
        "Five additional trigger samples (Emails C-G) modeled on the two in",
        "[`q3-trigger-emails.md`](q3-trigger-emails.md). Send any of these to",
        "**`" + RECIPIENT + "`** and attach the matching PDF from this directory.",
        "",
        "Mix: **C, D enrich** existing seeded tasks (pricing mismatch, perf",
        "regression); **E, F, G** file **new** tasks (a11y keyboard trap,",
        "autosave data loss, SharePoint embed CSP).",
        "",
    ]
    for e in EMAILS:
        lines.append(f"## Email {e['letter']} - {e['role']}")
        lines.append("")
        lines.append(f"**Subject:** `{e['subject']}`")
        lines.append("")
        lines.append(f"**Attachment:** `{e['filename']}`")
        lines.append("")
        lines.append("**Body:**")
        lines.append("")
        for p in e["body_lines"]:
            lines.append(f"> {p}")
            lines.append(">")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for e in EMAILS:
        path = OUT_DIR / e["filename"]
        write_pdf(path, e["subject"], e["body_lines"])
        print(f"  wrote {path}  ({path.stat().st_size} bytes)")
    cheat = OUT_DIR / "q3-trigger-emails-extra.md"
    write_cheatsheet(cheat)
    print(f"  wrote {cheat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
