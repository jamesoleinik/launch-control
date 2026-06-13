# Q3 Widget Launch — SharePoint upload set (Episode 7)

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
