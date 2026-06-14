"""
Send the two Episode 7 Part 2 trigger emails to the on-camera demo
mailbox jamesol@a365preview001.onmicrosoft.com.

This is Setup B from the Ep-7 README appendix, automated. The sweep
needs real inbox traffic to act on, so this script:

  1. Generates two short PDFs in-memory (no on-disk files needed).
  2. Acquires a Microsoft Graph access token via AzureCliCredential.
  3. Calls /v1.0/me/sendMail twice, attaching one PDF to each:

       Email A (will enrich an existing task):
         Subject: Q3 Widget Launch - export to CSV crashes the app for Northwind
         Attachment: Q3-widget-export-crash-northwind.pdf
         Topic overlaps the seeded *export-to-CSV crash* baseline task,
         so search_data should match it inside-the-PDF and the skill
         should enrich the existing task, not file a duplicate.

       Email B (will create a new task):
         Subject: Q3 Widget Launch - mobile auth callback fails after SSO
         Attachment: Q3-widget-mobile-auth-callback.pdf
         No seed task covers this, so search_data should return no
         in-launch matches and the skill should file a fresh lc_task
         with the PDF attached.

Sender and recipient are both jamesol@a365preview001.onmicrosoft.com
(the on-camera demo account). Run before each take.
"""
from __future__ import annotations

import base64
import io
import sys

import requests
from azure.identity import AzureCliCredential
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

RECIPIENT = "jamesol@a365preview001.onmicrosoft.com"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_SEND = "https://graph.microsoft.com/v1.0/me/sendMail"


def _pdf_bytes(title: str, paragraphs: list[str]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, title=title)
    styles = getSampleStyleSheet()
    story: list = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for p in paragraphs:
        story.append(Paragraph(p, styles["BodyText"]))
        story.append(Spacer(1, 8))
    doc.build(story)
    return buf.getvalue()


EMAILS = [
    {
        "subject": "Q3 Widget Launch - export to CSV crashes the app for Northwind",
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
        "attachment_name": "Q3-widget-export-crash-northwind.pdf",
        "_dedup_role": "ENRICH - overlaps the seeded export-crash task baseline",
    },
    {
        "subject": "Q3 Widget Launch - mobile auth callback fails after SSO",
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
        "attachment_name": "Q3-widget-mobile-auth-callback.pdf",
        "_dedup_role": "NEW TASK - no existing task on the launch covers this",
    },
]


def acquire_graph_token() -> str:
    print("Acquiring Microsoft Graph token via AzureCliCredential ...")
    cred = AzureCliCredential()
    tok = cred.get_token(GRAPH_SCOPE)
    return tok.token


def send_one(token: str, spec: dict) -> None:
    pdf_bytes = _pdf_bytes(
        title=spec["subject"],
        paragraphs=spec["body_lines"],
    )
    body_html = "<br/><br/>".join(
        f"<p>{line}</p>" for line in spec["body_lines"]
    )
    payload = {
        "message": {
            "subject": spec["subject"],
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": RECIPIENT}}],
            "attachments": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": spec["attachment_name"],
                    "contentType": "application/pdf",
                    "contentBytes": base64.b64encode(pdf_bytes).decode("ascii"),
                }
            ],
        },
        "saveToSentItems": True,
    }
    print(f"  -> {spec['subject']}")
    print(f"       ({spec['_dedup_role']})")
    r = requests.post(
        GRAPH_SEND,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    if r.status_code >= 300:
        print(f"     FAILED ({r.status_code}): {r.text[:500]}")
        raise SystemExit(2)
    print(f"     sent ({len(pdf_bytes)} byte PDF attached)")


def main() -> int:
    token = acquire_graph_token()
    print(f"Sending {len(EMAILS)} trigger emails to {RECIPIENT} ...")
    for spec in EMAILS:
        send_one(token, spec)
    print("")
    print("Done. Both trigger emails are in the inbox.")
    print("Allow ~1-2 minutes for Outlook indexing before running Step 2b.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
