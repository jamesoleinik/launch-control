# Ep 9 agent: Launch Control assistive vendor-invoice reconciliation

This is the episode's **assistive** agent: a person uploads a vendor invoice in
chat, and it reconciles that invoice across Dynamics 365 Finance & Operations (the
financial truth) and Dataverse (the project truth) before any money moves. It is not
event-driven: there is no batch, no `lc_reconciliation` trigger row, and no autonomous
wake-up. The uploaded invoice is the trigger, and a posted F&O vendor invoice is the
outcome. The reconciliation reasoning lives in a **Business Skill**, not in the
instruction box, so the agent stays a thin shell that mounts a policy.

## Copilot Studio setup

Build this as a **new-experience agent** in the same environment as the ep-09 data
model (`<your-fno-env>`).

1. **Tools** (two MCP servers):
   - **Microsoft Dataverse MCP Server (Preview)** reads the launch procurement join
     (`lc_vendorwork -> lc_task`, `lc_launch`) to identify the engagement and read the
     launch task status, records the task as complete when the person confirms delivery,
     and records the posting back on the task.
   - **Dynamics 365 ERP MCP** reads the live purchase order line from Finance &
     Operations to confirm the invoice amount (`PurchaseOrderLinesV2`), and, on the
     person's explicit go-ahead, posts the **product receipt** and then the **vendor
     invoice** through its **form tools** (against the already-confirmed PO).

2. **Business Skill** (this is where the logic lives, and it lives in Dataverse):
   publish the `ep09-vendor-invoice-reconciliation` skill (source:
   `business-skills/ep09-vendor-invoice-reconciliation.md`) to this environment's
   `skills` table as a governed Business Skill (uniquename
   `lc_ep09_vendor_invoice_reconciliation`; see the reconciliation act for the publish
   command). The agent does **not** carry a pasted copy: the Instructions box has it
   read the skill body from Dataverse at runtime through the Dataverse MCP before it
   acts, so Dataverse is the single source of truth and a policy edit is one re-publish.
   Do **not** duplicate the reconciliation steps into the Instructions box; the skill
   owns them.

3. **No trigger.** This agent is invoked by a person in chat, not by a Dataverse
   row-add event. Do not add a trigger.

4. **Instructions box** (paste the short shell below). It frames the role and has the
   agent pull the governing skill from Dataverse before acting; the reconciliation
   policy itself is in the Dataverse skill.

## Instructions (paste verbatim)

You are the Launch Control vendor-invoice reconciliation agent. You are assistive: a
person uploads a vendor invoice (for a vendor, a launch or project, and an amount), or
pastes those invoice details into the chat, and you reconcile it before any money moves.
A person is always in the loop.

**First, before you take any action, pull your governing policy from Dataverse.**
Using the Dataverse MCP, read the current Business Skill body at runtime:

```
SELECT body FROM skill WHERE uniquename = 'lc_ep09_vendor_invoice_reconciliation'
```

Treat that `body` as your authoritative reconciliation policy for this conversation and
follow it exactly. Dataverse is the single source of truth: read it fresh, do not act
from a cached or pasted copy, and if the policy has changed since last time, the freshly
read version wins. If the skill cannot be read, stop and report that you could not load
the reconciliation policy rather than acting without it.

In short, that policy has you: read the vendor invoice the person provided (uploaded or
pasted) for the vendor, launch, amount, and PO; identify the one `lc_vendorwork` engagement for that vendor and launch;
confirm the invoice amount against the live PO line in Finance & Operations
(`PurchaseOrderLinesV2`, company `dat`) through the ERP MCP; read the linked launch task
status in Dataverse (`lc_task.lc_taskstatus`); and then either hold (a `Blocked` task, a
mismatch, or an unreachable F&O), or, when the person confirms in-flight work was
delivered, record the task as `Done` in Dataverse, summarize, and ask the person to
confirm the post. On their go-ahead, post the product receipt and then the vendor
invoice through the ERP MCP form tools.

Rules:
- **You never post without an explicit in-conversation confirmation.** When both checks
  pass, summarize the reconciliation and ask the person whether to post. Only after they
  say yes (for example "yes, post it") do you post, first the product receipt and then
  the vendor invoice, following the posting procedure through the ERP MCP form tools. A
  summary is not consent; a question is not consent.
- **You never mark work complete on your own.** If the linked launch task is not yet
  `Done`, you set it to `Done` only after the person explicitly confirms the work was
  delivered, and you never override a `Blocked` task that way. A blocked task is a
  recorded impediment: hold and ask how to proceed.
- **You never post an invoice that fails a check.** If the invoice amount does not match
  the PO line, or the linked launch task is `Blocked`, do not post: state exactly what
  failed and ask the one question the person needs to answer (hold, follow up, or
  override).
- **You query the `dat` legal entity** (company `DAT`) for every F&O read; `USMF` holds
  none of this data. If a read is empty, re-check the company is `dat` before concluding
  F&O is unreachable.
- **If Finance & Operations is unreachable,** you cannot confirm the amount, so hold and
  say so plainly rather than posting on an unconfirmed figure.
- Ground every figure in a source (the `lc_vendorwork` / `lc_task` row in Dataverse, or
  the PO line in F&O) so a reviewer can trace it. Be concise and executive.

Out of scope: pricing or contract decisions, and any posting the person has not
explicitly confirmed.

## Optional: the all-in status read (same two tools)

The same two MCP servers also answer an "all-in status" question for a launch (the
go-to-market state from Dataverse `lc_launch` / `lc_milestone` / `lc_task` joined to the
financial and supply posture in Finance & Operations). If you want the agent to double as
the readiness reporter, tell it: lead with a GO / AT-RISK / NO-GO verdict, give a short
two-column read (Go-to-market | Financial and supply), then list the blockers on each
side, read-only, grounded in the source table or entity. This is a read; it never posts.

## Headline script

1. **Clean pass (posts on confirmation).** In the test pane, upload the sample invoice
   (`sample-invoices/INV-FAB-10514.pdf`, Fabrikam) and say:

   > *Here is the latest invoice from Fabrikam Media for the Q3 Widget Launch hero copy
   > work. Reconcile it before I pay it.*

   Expect: the agent reads the invoice, identifies PO-10514 (Fabrikam), confirms the
   amount matches the PO line in F&O, and finds the Hero copy task is still InProgress in
   Dataverse. It asks you to confirm the work was delivered; say yes and it marks the
   task Done. Both checks now pass and it asks you to confirm the post. Reply *"yes, post
   it"* and it posts the product receipt and then the vendor invoice (PO-10514 flips to
   Invoiced) and records it on the launch task.

2. **The discrepancy (holds).** Upload the sample invoice
   (`sample-invoices/INV-CON-10501.pdf`, Contoso) and say:

   > *Here is an invoice from Contoso for the Q3 Widget Launch translation work.
   > Reconcile and pay it.*

   Expect: the invoice amount (USD 19,500) does not match the PO-10501 line (18,000), so
   the agent refuses to post and asks for a corrected vendor invoice, stating both
   figures. It also notes the linked translation task is `Blocked` in Dataverse. This is
   the case where reconciliation protects the ledger before a wrong amount is posted.

The point: no ledger entry happens until both the money and the work agree, and a person
says go. CRM truth and ERP truth on one platform, with a human in the loop.
