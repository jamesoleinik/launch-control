"""Generate the Q3 Widget Launch field-issue PDFs for SharePoint upload.

These are the "field-reported issues" that James drops into the
LaunchControl SharePoint site before recording Episode 7. The Ep-7
Part 2 sweep finds them through Scout's SharePoint connector, then
the skill's Step 4 fires `search_data` against the LaunchControl
search model and dedups each finding against the existing [SEED]
`lc_task` rows on Q3 Widget Launch.

The mix is intentional:

1. `q3-sp-export-csv-customer-report.pdf` (dedup target #1)
   Near-duplicate of the seeded *export-to-CSV crash* task. Different
   reporter (enterprise field engineer, not internal QA), different
   tone, different exact phrasing — but the same underlying issue.
   The on-camera win: `search_data` matches the seeded task's
   attached PDF body content, the sweep ENRICHES the existing task
   instead of filing a duplicate.

2. `q3-sp-pricing-billing-escalation.pdf` (dedup target #2)
   Near-duplicate of the seeded *pricing page mismatch* task.
   Worded as a CSM escalation memo about a specific customer
   account, not a generic ops report. Same dedup outcome: enrich the
   existing task.

3. `q3-sp-a11y-keyboard-nav-regression.pdf` (net-new #1)
   Net-new P1 accessibility regression on widget keyboard nav. No
   existing task should match. The sweep should file a fresh
   `lc_task` with this PDF attached to `lc_relateddocuments`.

4. `q3-sp-figs-localization-slip.pdf` (net-new #2)
   Net-new slip notice from the FIGS localization team. There IS a
   seeded localization task on Q3, but it covers a different scope
   (ship the strings); this PDF reports a downstream slip on the
   signoff. Either net-new or borderline enrich — good test of the
   dedup decision.

5. `q3-sp-telemetry-payload-customer-escalation.pdf` (net-new #3)
   Net-new customer escalation about widget telemetry payload size
   blowing up at scale. There is a seeded security/telemetry task,
   but it covers signoff on the payload format, not size complaints
   from production. Should file a new task.

6. `q3-sp-status-update-week-of-jun-9.pdf` (no-op)
   Mentions Q3 Widget Launch by name but contains zero issue signals
   (no blocker, escalation, regression, slip, can't-ship, P0, P1).
   It's a routine status update. The sweep's Step 2 signal filter
   should drop it, and the Step 6 report should list it under the
   "no-op cases" line. Proves the filter works on camera.

The output lands in `episodes/ep-07-scout-autopilot/sharepoint-uploads/`
alongside a `README.md` that maps each PDF to its expected dedup
outcome, so anyone re-running the demo can verify the sweep behaves
as designed.

Requires `reportlab`. Idempotent — re-running overwrites in place.
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
    / "sharepoint-uploads"
)


ARTIFACTS = {
    "Q3 Widget Launch - Field report - Export to CSV crash (Northwind).pdf": [
        "Q3 Widget Launch &mdash; Field report from Enterprise Engineering",
        "Launch: Q3 Widget Launch",
        "Reported by: Field Engineering, Enterprise West",
        "Account: Northwind Pharmaceuticals (enterprise pilot)",
        "",
        "Customer hit a hard failure on the Q3 Widget Launch build "
        "trying to take widget compositions out of the designer this "
        "morning. Repro on their side:",
        "",
        "- Open a saved composition that has roughly 14 widgets on it.",
        "- Hit Export &gt; CSV.",
        "- About thirty seconds of spinner.",
        "- The application stops responding and the tab has to be reloaded.",
        "",
        "They flagged it as a Q3 Widget Launch blocker for their pilot. "
        "Their entire design-review workflow flows through CSV export "
        "into Excel for the review board. Without the export they have "
        "no path to sign off on Q3 Widget Launch.",
        "",
        "Asking the Q3 Widget Launch team to confirm whether this is "
        "the same issue Platform already has eyes on, or a new one. If "
        "it's the same one, please link this report onto that ticket "
        "so the customer comms stay coordinated.",
        "",
        "Severity (per customer): blocker.",
        "Launch: Q3 Widget Launch.",
        "Source channel: SharePoint &gt; LaunchControl &gt; Q3 Field Reports.",
    ],
    "Q3 Widget Launch - CSM escalation - Pricing mismatch (ACME).pdf": [
        "Q3 Widget Launch &mdash; CSM escalation memo",
        "Launch: Q3 Widget Launch",
        "Filed by: Customer Success, Strategic Accounts",
        "Customer reference: ACME Industries (strategic, ARR &gt;= $2M)",
        "",
        "ACME's procurement lead reached out this morning. They clicked "
        "through the Q3 Widget Launch promo-tier signup flow during the "
        "launch window and were quoted nineteen dollars per seat on the "
        "pricing page. Their finance team received the first invoice "
        "yesterday at twenty-four dollars per seat across 800 seats. "
        "The four-dollar delta on a strategic account is roughly $38k a "
        "year that they did not authorize.",
        "",
        "They want to know:",
        "- Was the Q3 Widget Launch pricing page wrong, or was the billing system wrong?",
        "- Are other customers from the same Q3 Widget Launch promo window affected?",
        "- What's the credit posture?",
        "",
        "I know Pricing Ops already has an item open on the disagreement "
        "between the Q3 Widget Launch pricing page and billing. This is "
        "the same root cause, with a named customer attached. Please "
        "pull this into the existing track so we stay on one story when "
        "we reply to ACME.",
        "",
        "Severity: customer escalation.",
        "Launch: Q3 Widget Launch.",
        "Source channel: SharePoint &gt; LaunchControl &gt; Q3 CSM Escalations.",
    ],
    "Q3 Widget Launch - Accessibility regression - Keyboard nav.pdf": [
        "Q3 Widget Launch &mdash; Accessibility regression report",
        "Launch: Q3 Widget Launch",
        "Filed by: Accessibility Team",
        "Reviewed against: WCAG 2.2 AA",
        "",
        "Keyboard navigation regressed on the widget designer after the "
        "Q3 Widget Launch bundle landed. Specifically: tab order on the "
        "widget palette skips the second column entirely, and focus "
        "indicators are no longer visible on the resize handles when "
        "the user is in high-contrast mode. Both behaviors worked "
        "correctly on the Q2 build.",
        "",
        "This is a P1 accessibility regression and a Q3 Widget Launch "
        "blocker per the org-wide policy on shipping with known WCAG AA "
        "regressions. We need a fix or an approved exception in writing "
        "before GA.",
        "",
        "Suggested owner: Widget Platform team (the bundle change is "
        "the likely cause).",
        "",
        "Severity: P1, blocker on the accessibility track.",
        "Launch: Q3 Widget Launch.",
        "Source channel: SharePoint &gt; LaunchControl &gt; Q3 A11y Reviews.",
    ],
    "Q3 Widget Launch - Localization slip - FIGS signoff.pdf": [
        "Q3 Widget Launch &mdash; Localization slip notice",
        "Launch: Q3 Widget Launch",
        "Filed by: International Engineering, FIGS pod",
        "",
        "Heads up &mdash; the Q3 Widget Launch FIGS (French / Italian / "
        "German / Spanish) localization signoff is slipping by one week. "
        "The strings landed on time and the in-product review is going "
        "well, but the German legal review of the widget asset terms "
        "has surfaced two phrases that need a second pass before we can "
        "publish. Expected new signoff date: one calendar week after "
        "the original target.",
        "",
        "This is a slip, not a blocker &mdash; Q3 Widget Launch GA "
        "itself can proceed if the decision is to ship FIGS as a "
        "fast-follow. Calling it out so the Launch Control register has "
        "the slip on file before the morning readiness sweep, rather "
        "than after.",
        "",
        "Severity: slip (one week).",
        "Launch: Q3 Widget Launch.",
        "Source channel: SharePoint &gt; LaunchControl &gt; Q3 Intl Reports.",
    ],
    "Q3 Widget Launch - Production escalation - Telemetry payload (Globex).pdf": [
        "Q3 Widget Launch &mdash; Production telemetry escalation",
        "Launch: Q3 Widget Launch",
        "Filed by: Site Reliability Engineering",
        "Customer reference: Globex Corp (top-10 by widgets-in-production)",
        "",
        "Globex's platform team escalated overnight. The Q3 Widget "
        "Launch telemetry payload, when the widget count on a single "
        "canvas passes roughly 50, balloons to multiple megabytes per "
        "emission. On their production deployment that pushed their "
        "telemetry ingestion bill up by 31% in the first week of the "
        "Q3 Widget Launch rollout and is starting to throttle their "
        "other workloads.",
        "",
        "This is not a content or format issue &mdash; the schema is "
        "fine. It is a payload-size issue at scale. Reasonable fixes "
        "are: per-widget delta emission instead of full-canvas, "
        "sampling above a threshold, or a server-side compaction step.",
        "",
        "Severity: customer escalation, revenue-at-risk.",
        "Launch: Q3 Widget Launch.",
        "Source channel: SharePoint &gt; LaunchControl &gt; Q3 SRE Escalations.",
    ],
    "Q3 Widget Launch - Weekly status (Week of Jun 9).pdf": [
        "Q3 Widget Launch &mdash; weekly status update (Week of Jun 9)",
        "Launch: Q3 Widget Launch",
        "Filed by: Q3 Widget Launch PM",
        "",
        "Quick weekly update on Q3 Widget Launch progress. Nothing on "
        "fire this week. Highlights:",
        "",
        "- Design review for the launch landing page wrapped on Tuesday.",
        "- Sales enablement deck is in editorial review.",
        "- The Q3 Widget Launch battlecard draft is out to Field for comments.",
        "- Localization is on track (FIGS, plus JP, plus ZH-CN).",
        "",
        "Standing meeting moved to Thursdays at 10am next week to clear "
        "the Wednesday all-hands. No decisions needed on this update.",
        "",
        "Launch: Q3 Widget Launch.",
        "Source channel: SharePoint &gt; LaunchControl &gt; Q3 Weekly Updates.",
    ],
}


README_BODY = """# Q3 Widget Launch — SharePoint upload set (Episode 7)

Drop the PDFs in this folder into the LaunchControl SharePoint site
(`/sites/LaunchControl/Q3 Field Reports`, or wherever the on-camera
folder lives) before recording Episode 7 Part 2. The Scout sweep
discovers them through the SharePoint connector and runs each one
through `search_data` on the Dataverse MCP preview endpoint to
dedup against the existing `[SEED]` `lc_task` rows.

> ⏱ **SharePoint / Graph indexer latency.** Newly uploaded files do
> not show up in Graph search instantly. After uploading, expect to
> wait roughly 10–30 minutes (occasionally longer for the first
> upload to a fresh library) before Scout's SharePoint connector
> returns them. If the on-camera sweep returns *"no Q3 Widget
> Launch evidence found"* right after upload, that is almost always
> indexer lag, not a sweep bug. Re-run the sweep in 15 minutes.
>
> The filenames lead with `Q3 Widget Launch - …` and each body
> repeats the launch name in the first line of text on purpose,
> because Graph search weights the filename and leading content
> much more heavily than buried mentions.

| PDF | Expected outcome | Why |
|---|---|---|
| `Q3 Widget Launch - Field report - Export to CSV crash (Northwind).pdf` | **Enrich** the existing `[SEED] Bug: Export to CSV crashes on >10-widget compositions` task | Same root cause, different reporter; `search_data` should match the seeded PDF body content on the existing task |
| `Q3 Widget Launch - CSM escalation - Pricing mismatch (ACME).pdf` | **Enrich** the existing `[SEED] Bug: Pricing page disagrees with billing on Q3 promo tier` task | Same root cause with a named customer (ACME) attached |
| `Q3 Widget Launch - Accessibility regression - Keyboard nav.pdf` | **New `lc_task`** (P1 accessibility) | Net-new finding; no seeded task covers WCAG keyboard-nav regressions |
| `Q3 Widget Launch - Localization slip - FIGS signoff.pdf` | **New `lc_task`** (slip) — borderline enrich on the seeded `[SEED] Localization: ship Q3 widget UI strings to FIGS` task | Different scope (slip on signoff vs. ship strings); good test of the dedup decision boundary |
| `Q3 Widget Launch - Production escalation - Telemetry payload (Globex).pdf` | **New `lc_task`** (customer escalation) | Different scope from the seeded telemetry-signoff task; production payload-size complaint |
| `Q3 Widget Launch - Weekly status (Week of Jun 9).pdf` | **No-op** | Contains no issue signal; should be filtered out at Step 2 and listed in the Step 6 report's "no-op cases" line |

The intended on-camera summary is roughly:
**5 findings · 3 new tasks · 2 enriched · 1 no-op.**

Regenerate with:

```powershell
python scripts/generate_q3_sharepoint_issues.py
```
"""


def write_pdf(path: Path, lines: list[str]) -> None:
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontSize = 11
    body.leading = 15
    doc = SimpleDocTemplate(
        str(path), pagesize=letter, title=path.stem, author="LaunchControl Field"
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
        rel = out.relative_to(OUT.parent.parent.parent)
        print(f"wrote {rel} ({out.stat().st_size} bytes)")
    readme = OUT / "README.md"
    readme.write_text(README_BODY, encoding="utf-8")
    print(f"wrote {readme.relative_to(OUT.parent.parent.parent)} ({readme.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
