# Chat source-routing customization

This customization permits combined briefings without treating communications
as authoritative business status. It was saved in native Copilot Chat settings.
It applies account-wide, not just to this episode. The previous customization
was backed up privately before replacement.

## Saved instructions

When I ask what people said or to summarize emails, chats, meetings, or documents,
use Microsoft 365 content. For current status, numbers, ownership, blockers, and
saved decisions, use Dynamics 365 / Power Platform business-application records
as the source of truth. When I ask for an overall view, a combined briefing, or
both communications and business status, retrieve both source types and reconcile
them in one answer. Cite each source and clearly distinguish recorded business
facts, communications context, inference, conflicts, and missing evidence. Match
sources using explicit project names, codes, or links; do not merge unrelated
projects. For business-app questions, resolve the requested app and use its
relevant views and related records to retrieve task titles, relationships,
assignees, dates, blocked flags, reasons, and saved gate fields. Missing or empty
approval fields do not mean approved. Never invent evidence or a relationship,
and never change records, send messages, or schedule work unless explicitly
requested and approved.

Keep each field attached to its source table and record. A related task blocked
flag or due date is not a launch-level field. Retrieve the task itself before
naming its blocker, owner, or completion state; if unavailable, state that
limitation. For communications, search the exact project name and any code
verified from its business record before broadening. An empty search result
means not retrieved, not proof the source does not exist. Preserve fictional-demo
labels and actual authorship; prepared demo content is not a real approval.

For Launch Control Demo, verify the app metadata and use its custom tables
lc_launch, lc_milestone, lc_task, lc_statusupdate, and lc_teammember, rather than
assuming the standard Task table. Traverse the actual launch and milestone
relationships to retrieve related tasks. A loosely similar title such as Partner
Launch Demo is not sufficient to link an email to Q3 Widget Launch. Exclude a
candidate from the briefing and conflict analysis unless its content establishes
the exact project name, verified code, or a direct record link. State missing
matching evidence instead of comparing unrelated dates. Treat drafts as drafts,
not sent communications.

## Verification and remaining preparation

The original customization explicitly prohibited combining communications and
business data. After replacement, a fresh run of the unchanged Revision B Chat
prompt attempted both sources and returned the cited launch record, but no
attributable M365 communications or files. This verifies the saved customization
and attempted retrieval, not successful cross-source grounding.
After a later rehearsal conflated a task's blocked flag with launch status, the
field-provenance paragraph above was added. Native settings confirmed that the
custom instructions were saved. A fresh unchanged stage prompt then searched both
the launch name and verified code, and explicitly distinguished missing retrieval
from source absence. Its answer did not repeat the launch-level blocked claim,
but returned an entity-grid surface instead of the required complete briefing.
This is partial behavioral improvement, not a successful recording rehearsal.

The latest saved addition names the verified custom tables and strengthens
project matching. The next unchanged rehearsal excluded the unrelated Partner
Launch Demo email and correctly identified the handoff as a draft. Business
retrieval remained inconsistent: that run reported no saved fields, and a
separate direct-table diagnostic reported no available table-query route.
The exact saved SharePoint file URL also failed native file retrieval.
Neither limitation establishes that the records or file are absent.
After additional elapsed time, an unchanged rehearsal did retrieve and cite the
saved certification brief, the handoff draft, the launch and its blocked task.
It preserved source authority and did not claim approval. Teams, complete related
records, and a saved assignee were still not retrieved. This improves coverage
but does not establish complete or repeatable retrieval.

A read-only SDK audit confirmed four related tasks and three milestones. The
blocked task is Confirm partner security evidence, assigned to Partner Review
Lead, with the recorded reason that certification evidence remains under review.
These records do not need reseeding to fill a retrieval gap.

The [source pack](revision-b-source-pack.json) contains fictional supporting
content. Its Teams coordination message was published with confirmation and read
back in the private Launch Control channel. The certification brief was saved and
reopened in SharePoint. Email remains a saved, unsent draft. Publish remaining material only after checking the
intended demo account and destinations and obtaining confirmation of the exact
writes. Include the launch record link resolved at runtime. Keep publication
timestamps genuine. Do not relabel unrelated material or backdate new content.
Read back each published source, then verify indexed retrieval in fresh Chat
and Cowork runs before recording.

## Cowork is configured separately

Chat customization does not enable Cowork plugins. The latest native Cowork
inspection found all three installed Business apps (preview) entries switched
off. The inspected Microsoft plugin had an existing connection and an available
enable switch. With the presenter's explicit approval, the inspected plugin was
enabled and its switch read back as checked. No connection or organization policy
was changed. A fresh review with the unchanged approved read-only prompt returned
the launch, four tasks, three milestones, two status updates, and the absence of a
quality-gate decision. It proposed role-owned tasks and monitoring, but still found
no matching communications or files. Business retrieval is restored; combined
cross-source grounding remains unverified.

Use native browser surfaces for this workflow. The presenter excluded the
separate Work IQ MCP tool, so its authentication is not a demo prerequisite.
