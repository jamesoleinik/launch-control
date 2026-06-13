# Launch Readiness Sweep (Scout, on-demand or scheduled)

## Description

The intake sweep. When invoked against a launch, Scout scans the
places where issues actually get reported (SharePoint and email),
then **uses the new Dataverse MCP agentic `search` tool to check
whether an existing task on the launch already covers the same issue,
matching against task fields *and* the content of any files attached
to those tasks**. If a match exists, the new collateral is appended
to the matching task instead of creating a duplicate. If not, a new
task is filed with the source attached.

The whole point of this skill is duplicate prevention. Filing the
same bug five mornings in a row is worse than not filing it at all,
because it trains the team to ignore the queue. The new MCP `search`
tool makes the dedup feasible: it returns hits not just from column
metadata but from the content of attached PDFs, emails, transcripts.
So a finding worded *"export to CSV is hanging"* matches an existing
task whose attached repro PDF says *"the export hangs for 30 seconds
then crashes"* even though the task title says nothing about hangs.

Sources of truth this skill sweeps:

1. **The LaunchControl SharePoint site.** Documents, beta feedback,
   support exports.
2. **The Q3 launch team mailbox** (`q3-launch@<tenant>`) plus the
   runner's own inbox.

## Instructions

### Step 1: Resolve the target launch

If the invoker named a launch, call `read_query` to resolve it:

```sql
SELECT lc_launchid, lc_name
FROM lc_launch
WHERE statecode = 0
  AND lc_name LIKE '%<name>%'
```

If the invoker did not name a launch, fall back to all launches with
`lc_status IN ('At Risk', 'Blocked')` and run Steps 2 through 6 for
each one.

### Step 2: Sweep SharePoint for issue reports on this launch

Use Scout's SharePoint connector. Query the LaunchControl site for
documents that reference the launch by name or short code and contain
at least one issue signal: **blocker, escalation, regression, slip,
can't ship, customer impact, defect, P0, P1**.

For each match capture: title, URL, the signal it matched on, and a
1-2 sentence excerpt. Skip anything older than 30 days.

### Step 3: Sweep email for issue reports on this launch

Use Scout's Outlook connector. Search the runner's inbox plus the
shared team mailbox for messages whose subject or body references the
launch and contains an issue signal (same list as Step 2). Limit to
the last 7 days.

For each match capture: subject, from, sent date, the matched signal,
a 1-2 sentence excerpt, and any attachments.

### Step 4 (key step): Dedup via agentic `search` over rows + attachments

For each finding from Steps 2 and 3, **call the MCP `search` tool**
with the finding's one-line summary plus the most distinctive excerpt
phrase as the query, scoped to `lc_task` rows on the target launch.

`search` returns hits based on both:

- column data (`lc_name`, `lc_description`)
- the **content of files attached** to those task rows, via the
  platform's embedding index over committed file columns.

This is the headline reason the new tool shape matters for this
skill. The old shape would force a literal-string scan over
`lc_description`; the new shape matches *semantic* overlap, including
text that only lives inside an attached repro PDF.

Treat the dedup decision as:

- **Strong match** (high score, top hit, content overlap visible in
  the matched excerpt): the finding is a duplicate. **Do not create a
  new task.** Go to Step 5a.
- **No match** or weak match: the finding is new. Go to Step 5b.

When in doubt, prefer match. A duplicate filed by mistake is far
worse than a new artifact appended to the right existing task.

### Step 5a: Strong match. Enrich the existing task

For each finding with a strong-match existing task:

1. Attach the new source artifact to the existing task via the MCP
   file-upload trio against the task's file column:
   - `init_file_upload({tablename: "lc_task", recordId: <existing
     task id>, fileAttributeName: "<file column>", fileName:
     <source filename>})`
   - HTTP PUT the bytes to the returned `sasUrl` with
     `x-ms-blob-type: BlockBlob`.
   - `commit_file_upload({continuationToken, fileName})`.

   The file column may already hold a prior artifact. The new file
   replaces it; the prior artifact remains discoverable through the
   task's annotations history. If your environment uses a multi-file
   attachment pattern (a child entity), follow that instead.

2. Call `update_record` against the matched task with:
   - `lc_description` = the existing description plus a single
     appended line: `Update <YYYY-MM-DD>: <source URL or sender + subject>`.

Do not change `lc_status` or `lc_priority` on enriched tasks.

### Step 5b: No match. File a new task

For each non-matching finding, call `create_record` against `lc_task`
with:

- `lc_name` = a one-line summary of the issue (~60 chars).
- `lc_description` = the matched excerpt, plus a `Source: <URL or
  sender + subject>` line.
- `lc_status` = `Open`.
- `lc_priority` = `High` if the signal is `blocker`, `escalation`,
  `P0`, or `can't ship`; otherwise `Normal`.
- `lc_launchid` = the launch GUID via the lookup shape
  `{ "relatedTable": "lc_launch", "recordId": "<guid>" }`.
- `lc_source` = `sharepoint-sweep` for SharePoint findings,
  `email-sweep` for email findings.

Then attach the source artifact to the new task via the same
file-upload trio (`init_file_upload` → HTTP PUT → `commit_file_upload`).

### Step 6: Report back to the invoker

Return a single chat message with four sections:

1. **Headline.** Launch name, count of SharePoint findings, count of
   email findings, count of new tasks filed, count of existing tasks
   enriched.
2. **New tasks.** Task name, source, one-line excerpt, link.
3. **Enriched tasks (the dedup wins).** Existing task name, the
   matched signal phrase from the source, the new attachment's
   filename, and a note that the agent matched via `search` over the
   prior attached collateral when applicable.
4. **No-op cases.** Sources that produced zero findings, in one line.

When invoked from a Scout Automation, also post the same summary as
a Teams direct message to the runner.

## What this skill is NOT

- It is **not** a status report. It only fires on launches the invoker
  names, or on launches already flagged `At Risk` / `Blocked`.
- It does **not** update launch or milestone records. The only writes
  it performs are `lc_task` `create_record`, `update_record` (Step 5a
  description append), and the file uploads attached to those tasks.
- It does **not** call the readiness Custom API.
- It does **not** delete anything. Stale tasks are the runner's call.
