# Launch Readiness Sweep (Scout, on-demand or scheduled)

## Description

The intake sweep. When invoked against a launch, Scout scans the
places where issues actually get reported (SharePoint and email),
then **uses the new Dataverse MCP preview tool shape to check whether
an existing task on the launch already covers the same issue** before
filing anything. The dedup decision lives in a single call:
`search_data`, scoped to the LaunchControl search model, returns the
candidate `lc_task` rows whose title, notes, or **attached
collateral** match the finding. The agent reads the matched-content
excerpt the tool returns and decides. If a match exists, the new
artifact is attached to the matching task and a one-line update is
appended. If not, a new task is filed with the source attached.

The whole point of this skill is duplicate prevention. Filing the
same bug five mornings in a row is worse than not filing it at all,
because it trains the team to ignore the queue. What makes the new
preview MCP shape work for this is `search_data`: one call surfaces
candidates whose evidence lives inside an attached PDF on
`lc_relateddocuments`, not just in task titles and notes. The agent
no longer has to pull a candidate set and `file_download` every
ambiguous attachment to decide; the tool returns the relevant
excerpt directly. `file_download` remains a fallback when an excerpt
is not enough.

Sources of truth this skill sweeps:

1. **The LaunchControl SharePoint site.** Documents, beta feedback,
   support exports.
2. **The Q3 launch team mailbox** (`q3-launch@<tenant>`) plus the
   runner's own inbox.

## Instructions

### Step 1: Resolve the target launch

If the invoker named a launch, call `read_query` to resolve it:

```sql
SELECT lc_launchid, lc_name, lc_risksummary
FROM lc_launch
WHERE statecode = 0
  AND lc_name LIKE '%<name>%'
```

Capture `lc_risksummary` (the Ep-5 AI prompt column) for the report
in Step 6. If the invoker did not name a launch, fall back to all
launches with `lc_status IN ('At Risk', 'Blocked')` and run Steps 2
through 6 for each one.

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

### Step 4 (key step): Dedup via `search_data` across rows + attached file content

For each finding from Steps 2 and 3, decide whether an existing task
already covers it. This is the value beat of the skill and the reason
this episode uses `/api/mcp_preview` instead of GA — `search_data` is
preview-only.

**4a. Run `search_data` once per finding.** Build a short, distinctive
query phrase from the finding (the most specific noun-phrase from the
excerpt: e.g. *"export to CSV crashes on big compositions"*, not
*"export issue"*). Scope-bind to the LaunchControl search model:

```json
{
  "name": "search_data",
  "arguments": {
    "query": "<finding phrase>",
    "scope": "new_dvtablesearch_aiplugin_model_lc_Model"
  }
}
```

`search_data` returns row paths of the form
`tables/lc_task/records/<guid>` along with excerpts of matched content
from inside the `lc_relateddocuments` file column on those rows
(provided the column has *Available for Search* enabled in the table
metadata). Filter the returned rows to `lc_task` only, and only those
whose `_lc_launchid_value` matches the current launch (call
`read_query` to look up the launch id on each candidate if the path
alone is insufficient).

**4b. Read the matched excerpt and classify the finding.** For each
candidate `lc_task` row `search_data` returned, read the matched
content excerpt. The match is semantic: a finding worded *"export to
CSV is hanging"* will surface a task whose attached PDF says *"export
hangs ~30s then crashes the app on a 500-row composition"*. Classify:

- **Strong match.** The excerpt clearly covers the same issue. Go to
  Step 5a (enrich).
- **No match.** `search_data` returned zero rows, or none of the
  returned excerpts cover the finding. Go to Step 5b (create).
- **Ambiguous.** An excerpt looks plausible but is not decisive. Call
  `file_download` against that task's `lc_relateddocuments` to read
  the full document, then decide. Use this path sparingly.

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

1. **Headline.** Launch name, the launch's verbatim `lc_risksummary`,
   count of SharePoint findings, count of email findings, count of
   new tasks filed, count of existing tasks enriched.
2. **New tasks.** Task name, source, one-line excerpt, link.
3. **Enriched tasks (the dedup wins).** Existing task name, the
   matched signal phrase from the source, the new attachment's
   filename, and the excerpt `search_data` returned from the prior
   attached collateral (so the reader sees the evidence the dedup
   decision was based on).
4. **No-op cases.** Sources that produced zero findings, in one line.

When invoked from a Scout Automation, also post the same summary as
a Teams direct message to the runner.

## What this skill is NOT

- It is **not** a status report. It only fires on launches the invoker
  names, or on launches already flagged `At Risk` / `Blocked`.
- It does **not** update launch or milestone records. The only writes
  it performs are `lc_task` `create_record`, `update_record` (Step 5a
  description append), and the file uploads attached to those tasks.
- It does **not** call the readiness Custom API. (It could, via
  `invoke_api` on the preview MCP — that is a different skill.)
- It does **not** hand-tally readiness from milestone or task status
  counts. Readiness comes from the launch's `lc_risksummary` AI
  prompt column plus the blocked `lc_task` rows, never from a
  derived count.
- It does **not** delete anything. Stale tasks are the runner's call.
