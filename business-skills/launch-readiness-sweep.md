# Launch Readiness Sweep (Scout, on-demand or scheduled)

## Description

The intake sweep. When invoked against a launch, Scout scans the
places where issues actually get reported (SharePoint and email),
then **uses the new Dataverse MCP tool shape to check whether an
existing task on the launch already covers the same issue** before
filing anything. The agent calls `search` to locate the `lc_task`
entity, `describe` to load its schema, then `read_query` (the
execute surface) to pull the open tasks on the launch and compare
them, in-context, against each new finding. When a candidate looks
plausible but not certain, the agent calls `file_download` to read
inside the candidate's attached collateral and break the tie. If a
match exists, the new artifact is attached to the matching task and
a one-line update is appended. If not, a new task is filed with the
source attached.

The whole point of this skill is duplicate prevention. Filing the
same bug five mornings in a row is worse than not filing it at all,
because it trains the team to ignore the queue. What makes the new
MCP shape work for this is the combination: `read_query` returns the
candidates the agent needs to compare against, and `file_download`
lets the agent open a candidate's attached PDF in-context when the
title and notes alone are not enough to decide. The dedup decision
lives in the agent, on real candidate rows, with real file content
available on demand.

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

### Step 4 (key step): Dedup via `read_query` over open tasks on the launch

For each finding from Steps 2 and 3, decide whether an existing task
already covers it. This is the value beat of the skill, so do it
deliberately.

**4a. Pull the candidate set with `read_query`.** One call, scoped to
open tasks on this launch:

```sql
SELECT lc_taskid, lc_title, lc_notes, lc_priority, lc_taskstatus,
       lc_relateddocuments_name
FROM lc_task
WHERE _lc_launchid_value = '<launch GUID>'
  AND lc_taskstatus IN (10600301, 10600302)
ORDER BY modifiedon DESC
```

(`10600301` = Not Started, `10600302` = In Progress. Done tasks
should not block deduplication of new findings.)

**4b. Compare each finding against the candidate set, in-context.**
For each finding, the agent reads `lc_title` and `lc_notes` on every
candidate and decides whether the candidate covers the same
underlying issue. The comparison is semantic, not literal: a finding
worded *"export to CSV is hanging"* matches a task whose notes say
*"export hangs ~30s then crashes the app"*. Use plain reasoning over
the candidate set; do not try to match by string equality.

**4c. Break ties with `file_download` when needed.** If a candidate's
`lc_relateddocuments_name` is non-empty and the title plus notes are
not enough to decide, call `file_download` against that task's
`lc_relateddocuments` column to read the attached collateral
in-context, then decide. Only download when the decision is
genuinely ambiguous; do not download for every candidate.

Classify each finding as:

- **Strong match.** A candidate clearly covers the same issue. Go to
  Step 5a (enrich).
- **No match.** Nothing in the candidate set covers the finding. Go
  to Step 5b (create).

When in doubt between strong and weak, prefer match. A duplicate
filed by mistake is far worse than a new artifact appended to the
right existing task.

### Step 5a: Strong match. Enrich the existing task

For each finding with a strong-match existing task:

1. Attach the new source artifact to the existing task via the MCP
   file-upload trio against the task's file column (`lc_relateddocuments`):
   - `init_file_upload({tablename: "lc_task", recordId: <existing
     task id>, fileAttributeName: "lc_relateddocuments", fileName:
     <source filename>})`
   - HTTP PUT the bytes to the returned `sasUrl` with
     `x-ms-blob-type: BlockBlob`.
   - `commit_file_upload({continuationToken, fileName})`.

   The file column holds a single file. The new file replaces the
   prior artifact; the prior artifact remains discoverable through the
   task's annotations history.

2. Call `update_record` against the matched task with:
   - `lc_notes` = the existing notes plus a single appended line:
     `Update <YYYY-MM-DD>: <source URL or sender + subject>`.

Do not change `lc_taskstatus` or `lc_priority` on enriched tasks.

### Step 5b: No match. File a new task

For each non-matching finding, call `create_record` against `lc_task`
with:

- `lc_title` = a one-line summary of the issue (~60 chars).
- `lc_notes` = the matched excerpt, plus a `Source: <URL or
  sender + subject>` line.
- `lc_taskstatus` = `NotStarted`.
- `lc_priority` = `High` if the signal is `blocker`, `escalation`,
  `P0`, or `can't ship`; otherwise `Medium`.
- `lc_launchid` = the launch GUID via the lookup shape
  `{ "relatedTable": "lc_launch", "recordId": "<guid>" }`.

Then attach the source artifact to the new task via the same
file-upload trio (`init_file_upload` → HTTP PUT → `commit_file_upload`)
against `lc_relateddocuments`.

### Step 6: Report back to the invoker

Return a single chat message with four sections:

1. **Headline.** Launch name, count of SharePoint findings, count of
   email findings, count of new tasks filed, count of existing tasks
   enriched.
2. **New tasks.** Task name, source, one-line excerpt, link.
3. **Enriched tasks (the dedup wins).** Existing task name, the
   matched signal phrase from the source, the new attachment's
   filename, and (when applicable) a note that the agent broke the
   tie by `file_download`-ing the prior attached collateral.
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
