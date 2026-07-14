"""Generate the Episode 9 sample vendor invoices (PDF) for the live agent test.

Two invoices back the two demo cases the assistive reconciliation agent handles:

- INV-FAB-10514.pdf: Fabrikam Media, Q3 Widget Launch hero copy, 22,000, PO-10514.
  The clean pass: the amount matches the PO-10514 line and, once the person confirms
  delivery, the agent marks the launch task complete and posts.
- INV-CON-10501.pdf: Contoso Supply Co, Q3 Widget Launch translation, 19,500, PO-10501.
  The discrepancy: the amount is higher than the PO-10501 line of 18,000, and the
  linked launch task is Blocked in Dataverse, so the agent holds.

The Fabrikam figure mirrors the live F&O purchase order line (dat company) so the
agent's financial check passes. The Contoso figure intentionally does not match the PO
line. Text is selectable so an agent can read the PDF.

Run:
    python episodes/ep-09-dataverse-fno/sample-invoices/make_sample_invoices.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

OUT_DIR = Path(__file__).resolve().parent

BUYER = {
    "name": "Launch Control Inc.",
    "attn": "Accounts Payable",
    "line": "Q3 Widget Launch program",
}

INVOICES = [
    {
        "file": "INV-FAB-10514.pdf",
        "vendor": "Fabrikam Media",
        "vendor_account": "V0002",
        "vendor_addr": ["1200 Market Street, Suite 400", "Portland, OR 97205"],
        "invoice_number": "INV-FAB-10514",
        "invoice_date": "August 14, 2026",
        "due_date": "September 13, 2026",
        "po_number": "PO-10514",
        "currency": "USD",
        "line_desc": "Q3 Widget Launch: hero copy + three key visuals (landing page and social), two revision rounds",
        "qty": 1,
        "unit_price": 22000,
        "amount": 22000,
    },
    {
        "file": "INV-CON-10501.pdf",
        "vendor": "Contoso Supply Co",
        "vendor_account": "V0001",
        "vendor_addr": ["45 Corvin Way", "Redmond, WA 98052"],
        "invoice_number": "INV-CON-10501",
        "invoice_date": "August 12, 2026",
        "due_date": "September 11, 2026",
        "po_number": "PO-10501",
        "currency": "USD",
        "line_desc": "Q3 Widget Launch: localization / translation outsourcing (source copy to five locales)",
        "qty": 1,
        "unit_price": 19500,
        "amount": 19500,
    },
]


def money(value, currency):
    return f"{currency} {value:,.2f}"


def draw_invoice(inv):
    path = OUT_DIR / inv["file"]
    c = canvas.Canvas(str(path), pagesize=LETTER)
    width, height = LETTER
    left = inch
    y = height - inch

    c.setFont("Helvetica-Bold", 22)
    c.drawString(left, y, inv["vendor"])
    c.setFont("Helvetica", 10)
    for addr in inv["vendor_addr"]:
        y -= 14
        c.drawString(left, y, addr)

    c.setFont("Helvetica-Bold", 26)
    c.drawRightString(width - inch, height - inch, "INVOICE")

    y -= 34
    c.setFont("Helvetica", 10)
    right_x = width - inch
    meta = [
        ("Invoice number", inv["invoice_number"]),
        ("Invoice date", inv["invoice_date"]),
        ("Due date", inv["due_date"]),
        ("Purchase order", inv["po_number"]),
        ("Vendor account", inv["vendor_account"]),
        ("Currency", inv["currency"]),
    ]
    my = height - inch - 40
    for label, value in meta:
        c.setFont("Helvetica", 9)
        c.drawRightString(right_x - 130, my, f"{label}:")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(right_x, my, str(value))
        my -= 14

    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Bill to")
    c.setFont("Helvetica", 10)
    y -= 14
    c.drawString(left, y, BUYER["name"])
    y -= 14
    c.drawString(left, y, f'Attn: {BUYER["attn"]}')
    y -= 14
    c.drawString(left, y, BUYER["line"])

    y -= 40
    c.setFillColorRGB(0.12, 0.12, 0.12)
    c.rect(left, y, width - 2 * inch, 20, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left + 6, y + 6, "Description")
    c.drawRightString(left + 4.6 * inch, y + 6, "Qty")
    c.drawRightString(left + 5.6 * inch, y + 6, "Unit price")
    c.drawRightString(width - inch - 6, y + 6, "Amount")
    c.setFillColorRGB(0, 0, 0)

    y -= 22
    c.setFont("Helvetica", 9)
    desc = inv["line_desc"]
    # simple wrap at ~62 chars
    words = desc.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 62:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    for i, ln in enumerate(lines):
        c.drawString(left + 6, y - i * 12, ln)
    row_y = y
    c.drawRightString(left + 4.6 * inch, row_y, str(inv["qty"]))
    c.drawRightString(left + 5.6 * inch, row_y, money(inv["unit_price"], inv["currency"]))
    c.drawRightString(width - inch - 6, row_y, money(inv["amount"], inv["currency"]))

    y = row_y - (len(lines) * 12) - 16
    c.line(left + 3.5 * inch, y, width - inch, y)
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawRightString(left + 5.6 * inch, y, "Subtotal:")
    c.drawRightString(width - inch - 6, y, money(inv["amount"], inv["currency"]))
    y -= 16
    c.drawRightString(left + 5.6 * inch, y, "Tax:")
    c.drawRightString(width - inch - 6, y, money(0, inv["currency"]))
    y -= 18
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(left + 5.6 * inch, y, "Total due:")
    c.drawRightString(width - inch - 6, y, money(inv["amount"], inv["currency"]))

    y -= 44
    c.setFont("Helvetica", 9)
    c.drawString(left, y, f'Please reference purchase order {inv["po_number"]} on remittance.')
    y -= 13
    c.drawString(left, y, "Payment terms: Net 30. Thank you for your business.")

    c.showPage()
    c.save()
    return path


def main():
    for inv in INVOICES:
        path = draw_invoice(inv)
        print(f"[invoice] wrote {path.name} ({inv['vendor']}, {inv['po_number']}, "
              f"{inv['currency']} {inv['amount']:,})")


if __name__ == "__main__":
    main()
