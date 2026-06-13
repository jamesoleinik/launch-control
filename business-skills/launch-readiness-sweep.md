# Launch Readiness Sweep (Scout, on-demand or scheduled)

## Description

The intake sweep. When invoked against a specific launch (or against all
at-risk launches), Scout scans the places where issues actually get
reported, turns each finding into a tracked task in Dataverse on the
matching launch, and attaches the source document (PDF, email, etc.)
to the task so the artifact lives next to the work.

The two sources of truth this skill sweeps:

1. **The LaunchControl SharePoint site.** Documents, beta feedback,
   support exports, anything filed under the site Scout has access to.
2. **The Q3 launch team mailbox** (`q3-launch@<tenant>`) plus the
   runner's own inbox. Customer escalations and partner reports
   typically land here.

For each issue found, the skill creates an `lc_task` on the matching
`lc_launch` row and attaches the source artifact (the PDF, the email
saved as text or `.eml`, the SharePoint doc) to that task via the
Dataverse MCP file-upload tools. The attached collateral is
immediately searchable by content because the platform builds
embeddings on commit.

## Instructions

### Step 1: Resolve the target launch

If the invoker named a launch ("the Q3 Widget Launch", "the Atlas
launch"), call `read_query` to resolve it to a row:

```sql
SELECT lc_launchid, lc_name
FROM lc_launch
WHERE statecode = 0
  AND lc_name LIKE '%<name>%'
```

If the invoker did not name a launch, fall back to all launches with
`lc_status IN ('At Risk', 'Blocked')` and run Steps 2 through 5 for
each one. If no launch matches and no at-risk launches exist, stop and
report.

### Step 2: Sweep SharePoint for issue reports on this launch

Use Scout's SharePoint connector. Query the LaunchControl SharePoint
site for documents whose title or content references the launch by
name or by short code (e.g. "Q3 Widget Launch", "Q3", "widget") and
that contain at least one issue signal: **blocker, escalation,
regression, slip, can't ship, customer impact, defect, P0, P1**.

For each matching document, capture: the title, the URL, the issue
signal it matched on, and a 1-2 sentence excerpt of the surrounding
text. Skip anything older than 30 days. Skip anything you have
already filed (see Step 4 dedup).

### Step 3: Sweep email for issue reports on this launch

Use Scout's Outlook connector. Search the runner's inbox plus the
shared team mailbox for messages whose subject or body references
the launch and contains an issue signal (same list as Step 2). Limit
to the last 7 days unless the invoker overrides it.

For each matching message, capture: subject, from, sent date, the
matched signal, and a 1-2 sentence excerpt. If the message has
attachments, capture those too as candidate collateral.

### Step 4: De-duplicate against existing tasks

For the target launch, call `read_query`:

```sql
SELECT lc_taskid, lc_name, lc_description
FROM lc_task
WHERE lc_launch = '<launch id>'
  AND lc_source IN ('sharepoint-sweep', 'email-sweep')
```

Skip any SharePoint finding whose URL is already referenced in an
existing task's description. Skip any email finding whose subject is
already referenced. Approximate match on filename or subject is fine.
The sweep must not re-file the same issue day after day.

### Step 5: File one task per surviving finding, attach the source

For each non-duplicate finding:

1. Call `create_record` against `lc_task` with:
   - `lc_name` = a one-line summary of the issue (no quotes, ~60 chars).
   - `lc_description` = the matched excerpt, plus a line `Source: <SharePoint URL or email subject + sender>`.
   - `lc_status` = `Open`.
   - `lc_priority` = `High` if the signal is `blocker`, `escalation`, `P0`, or `can't ship`; otherwise `Normal`.
   - `lc_launch` = the launch GUID via the lookup shape `{ "relatedTable": "lc_launch", "recordId": "<guid>" }`.
   - `lc_source` = `sharepoint-sweep` for SharePoint findings, `email-sweep` for email findings.

2. Attach the source artifact to the new task via the MCP file-upload
   trio:
   - `init_file_upload` against `tablename: "lc_task"`, the new task's
     id, and the task's file column (`lc_artifact` by convention).
   - HTTP PUT the bytes (the downloaded SharePoint document, or the
     email saved as `.eml`) to the returned SAS URL with
     `x-ms-blob-type: BlockBlob`.
   - `commit_file_upload` with the returned `continuationToken` and the
     original filename.

The attached collateral becomes searchable by content via `search_data`
within ~30 seconds because the platform builds embeddings on commit.

### Step 6: Report back to the invoker

Return a single chat message with three sections:

1. **Headline.** Launch name. Count of SharePoint findings, count of
   email findings, count of new tasks filed, count of duplicates
   skipped.
2. **Per finding.** Task name, source (SharePoint URL or email subject
   + sender), one-line excerpt, link to the new task.
3. **No-op cases.** If a source produced zero new findings, say so in
   one line ("SharePoint: nothing new today").

When the skill is invoked from a Scout Automation, also post the same
summary as a Teams direct message to the runner.

## What this skill is NOT

- It is **not** a status report. It only fires on launches the invoker
  names, or on launches already flagged `At Risk` / `Blocked`.
- It does **not** update launch or milestone records. The only writes
  it performs are `lc_task` `create_record` calls and the file uploads
  attached to those new tasks.
- It does **not** call the readiness Custom API. Use the Launch
  Readiness Review playbook for that.
- It does **not** delete anything. Stale tasks are the runner's call.
