# Q3 trigger emails - extra batch (Episode 7 Part 2, Setup B)

Five additional trigger samples (Emails C-G) modeled on the two in
[`q3-trigger-emails.md`](q3-trigger-emails.md). Send any of these to
**`jamesol@a365preview001.onmicrosoft.com`** and attach the matching PDF from this directory.

Mix: **C, D enrich** existing seeded tasks (pricing mismatch, perf
regression); **E, F, G** file **new** tasks (a11y keyboard trap,
autosave data loss, SharePoint embed CSP).

## Email C - ENRICH (overlaps the seeded pricing-page mismatch baseline task)

**Subject:** `Q3 Widget Launch - promo tier price on the pricing page does not match the invoice`

**Attachment:** `Q3-widget-pricing-mismatch-promo.pdf`

**Body:**

> Q3 Widget Launch pricing escalation from a customer ticket.
>
> The pricing page disagrees with billing on the Q3 promo tier. The page advertises the promo tier at $19, but the invoice charges $24. Customers who clicked through during the promo window are being billed the higher amount.
>
> Several inbound tickets already. Severity from the customer side: high, a customer-facing pricing escalation. Attached PDF has the screenshot notes and the two amounts side by side.
>

## Email D - ENRICH (overlaps the seeded first-paint perf regression baseline task)

**Subject:** `Q3 Widget Launch - cold-start first paint regressed after the widget bundle`

**Attachment:** `Q3-widget-first-paint-regression.pdf`

**Body:**

> Q3 Widget Launch perf note from the performance dashboard.
>
> First paint regressed from 380ms to 740ms on the cold-start path after the Q3 widget bundle was added. The regression reproduces on a clean profile with the cache cleared.
>
> Not a blocker for GA but it should stay on the watch list. Attached PDF has the trace summary and the before/after first-paint numbers.
>

## Email E - NEW TASK (no existing task on the launch covers this)

**Subject:** `Q3 Widget Launch - keyboard focus trap in the widget designer`

**Attachment:** `Q3-widget-accessibility-keyboard-trap.pdf`

**Body:**

> Q3 Widget Launch accessibility issue from the a11y review pass.
>
> Keyboard-only users get trapped in the widget property panel. Once focus enters the panel, Tab and Shift+Tab cycle inside it and never return to the canvas, so the rest of the designer is unreachable without a mouse. NVDA does not announce the panel boundaries.
>
> No existing task on the launch covers this. Filed via this email so the morning sweep picks it up. Attached PDF has the steps, the failing WCAG criteria, and the assistive-tech matrix.
>

## Email F - NEW TASK (no existing task on the launch covers this)

**Subject:** `Q3 Widget Launch - canvas autosave drops edits after session timeout`

**Attachment:** `Q3-widget-autosave-data-loss.pdf`

**Body:**

> Q3 Widget Launch data-loss report from the beta cohort.
>
> When a designer session sits idle long enough for the auth token to refresh, the canvas silently reverts to the last manual save on the next edit. Any work done since the last manual save is gone with no warning. Reproduced twice on the current beta build.
>
> No existing task on the launch covers this. Filed via this email so the morning sweep picks it up. Attached PDF has the timeline, the affected build number, and the repro steps.
>

## Email G - NEW TASK (no existing task on the launch covers this)

**Subject:** `Q3 Widget Launch - embedded widget blocked by CSP on SharePoint pages`

**Attachment:** `Q3-widget-sharepoint-embed-csp.pdf`

**Body:**

> Q3 Widget Launch integration issue from a pilot customer.
>
> Embedding a Q3 widget in a SharePoint page fails. The browser blocks the iframe with a Content-Security-Policy frame-ancestors violation, and the widget area renders blank. The same widget loads fine in the standalone app.
>
> No existing task on the launch covers this. Filed via this email so the morning sweep picks it up. Attached PDF has the failing page URL, the console error, and the CSP header that needs the allowance.
>
