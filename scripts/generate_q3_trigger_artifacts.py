"""
Generate the two Episode 7 Part 2 trigger artifacts (PDFs +
copy/paste cheat-sheet) into episodes/ep-07-scout-autopilot/seed-artifacts/.

Use this when you'd rather send the trigger emails manually (from a
phone, a different account, etc.) instead of running
scripts/send_q3_trigger_emails.ps1 / .py.

Emits:
  - Q3-widget-export-crash-northwind.pdf      (Email A attachment)
  - Q3-widget-mobile-auth-callback.pdf        (Email B attachment)
  - q3-trigger-emails.md                      (subjects + body text
                                               to paste into Outlook)
"""
from __future__ import annotations

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

RECIPIENT = "jamesol@a365preview001.onmicrosoft.com"

EMAILS = [
    {
        "filename": "Q3-widget-export-crash-northwind.pdf",
        "subject": "Q3 Widget Launch - export to CSV crashes the app for Northwind",
        "role": "ENRICH (overlaps the seeded export-crash baseline task)",
        "body_lines": [
            "Q3 Widget Launch field report from Northwind.",
            (
                "Northwind hit a hard crash on Export to CSV with a "
                "large widget composition (about 14 widgets on one "
                "canvas). The export spinner runs for roughly 30 "
                "seconds and then the app crashes back to the home "
                "screen. They lose unsaved work."
            ),
            (
                "Repro is consistent on their tenant. Severity from "
                "their side: blocker for the Q3 rollout. Attached PDF "
                "has the customer's repro notes verbatim."
            ),
        ],
    },
    {
        "filename": "Q3-widget-mobile-auth-callback.pdf",
        "subject": "Q3 Widget Launch - mobile auth callback fails after SSO",
        "role": "NEW TASK (no existing task on the launch covers this)",
        "body_lines": [
            "Q3 Widget Launch issue from mobile beta cohort.",
            (
                "Mobile users on the Q3 Widget Launch beta build "
                "cannot complete sign-in. After the IdP redirect the "
                "OAuth callback returns a 500 and the app drops the "
                "user back at the login screen. Reproduced on iOS "
                "and Android in the same build."
            ),
            (
                "No existing task on the launch covers this. Filed "
                "via this email so the morning sweep picks it up. "
                "Attached PDF has the device matrix and the exact "
                "callback URL that 500s."
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
        "# Q3 trigger emails (Episode 7 Part 2, Setup B)",
        "",
        "Send both of these to **`" + RECIPIENT + "`** before the take.",
        "Attach the matching PDF from this directory to each one.",
        "",
    ]
    for i, e in enumerate(EMAILS, start=1):
        letter = "A" if i == 1 else "B"
        lines.append(f"## Email {letter} - {e['role']}")
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
    cheat = OUT_DIR / "q3-trigger-emails.md"
    write_cheatsheet(cheat)
    print(f"  wrote {cheat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
