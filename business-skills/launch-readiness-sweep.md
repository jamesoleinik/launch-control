# Launch Readiness Sweep (Scout, scheduled)

## Description

The morning sweep. Every weekday at 9am Scout runs this skill against the
Launch Control environment and reports back in Teams. The job is to find
risks that have shown up in the last day, write them into Dataverse as
`lc_task` rows, and then post one consolidated readiness summary.

The sweep reads from two sources of truth:

1. The structured launch data in Dataverse: `lc_launch`, `lc_milestone`,
   `lc_task`, `lc_statusupdate`.
2. The unstructured artifacts attached to each launch as **files** on the
   `lc_launch` record itself, such as PRDs, beta-tester reports, support
   transcripts, community threads saved as PDF. These are searched by
   content (embeddings), not by metadata, via the Dataverse MCP
   `search_data` tool.

The verdict is sourced from the `lc_risksummary` AI prompt column on
`lc_launch` plus the count of blocked `lc_task` rows. The sweep never
hand-tallies readiness. It surfaces what changed, not what is.

## Instructions

### Step 1: Resolve the scope

Use the Dataverse MCP `describe` tool against `scopes/` to find the
`LaunchControl` scope name. All subsequent `search` and `search_data`
calls in this skill pass `scope = <that name>`. If the LaunchControl
scope is not present, stop and report that the environment is not set
up. Do not fall back to a broader scope.

### Step 2: Pull the at-risk launches

Call `read_query` with:

```sql
SELECT lc_launchid, lc_name, lc_risksummary
FROM lc_launch
WHERE statecode = 0
  AND (lc_status = 'At Risk' OR lc_status = 'Blocked')
ORDER BY lc_targetdate
```

If the result is empty, post a single Teams message ("No at-risk
launches today.") and stop. Do not search files, do not file tasks.

### Step 3: For each at-risk launch, search inside its files

For each launch returned in Step 2, call `search_data` with:

- `query` = `"blocker OR escalation OR regression OR slip OR \"can't ship\" OR \"customer impact\""`
- `scope` = the LaunchControl scope from Step 1

`search_data` returns filesystem-style paths plus matched content
excerpts. Filter the results to records whose path is
`tables/lc_launch/records/<this launch's id>` so file matches stay
scoped to the launch being processed. Each match contains a quoted
content excerpt from inside an uploaded file.

This is the headline move of the skill. The right hit comes from inside
a PDF or transcript nobody indexed by hand, because the platform built
embeddings over the file content when it was committed.

### Step 4: De-duplicate against existing tasks

For each surviving match, call `read_query`:

```sql
SELECT lc_taskid, lc_description
FROM lc_task
WHERE lc_launch = '<launch id>'
  AND lc_source = 'file-sweep'
```

Skip any match whose excerpt is already represented in an existing
`lc_task.lc_description`. Approximate match is fine. The sweep must not
re-file the same finding day after day.

### Step 5: File new tasks

For each non-duplicate match, call `create_record` against `lc_task`
with:

- `lc_name` = a one-line summary of the finding (no quotes)
- `lc_description` = the matched content excerpt, prefixed with `[file-sweep]` and the filename it came from
- `lc_status` = `Open`
- `lc_priority` = `High` if the excerpt contains "blocker", "escalation", or "can't ship", otherwise `Normal`
- `lc_launch` = the launch's GUID (use the lookup shape `{ "relatedTable": "lc_launch", "recordId": "<guid>" }`)
- `lc_source` = `file-sweep`

### Step 6: Post one Teams summary

Send one Teams direct message to the runner. The message has three
sections:

1. **Headline**: count of at-risk launches and count of new tasks filed
   in this run.
2. **Per launch**: launch name, the `lc_risksummary` value (verbatim,
   one paragraph), the names of any new `lc_task` rows filed in Step 5
   for that launch, and the count of pre-existing blocked tasks.
3. **No-op cases**: launches in Step 2 that produced zero new tasks
   ("nothing new today"). Keep these short, one line each.

Do not include a global GO/CONDITIONAL/NO-GO verdict in this message.
This skill is the morning surface, not the readiness gate. The verdict
belongs to the Launch Readiness Review playbook, which is invoked
on-demand from chat.

## What this skill is NOT

- It is **not** a status report. It only fires on `At Risk` and
  `Blocked` launches.
- It does **not** update launch or milestone records. The only writes
  it performs are `lc_task` inserts in Step 5.
- It does **not** read or write files. `search_data` reads file
  content; the actual upload of artifacts onto launches is done by
  launch managers using the `init_file_upload` / `commit_file_upload`
  tools and is outside the scope of this skill.
- It does **not** call the readiness Custom API. Use the Launch
  Readiness Review playbook for that.
