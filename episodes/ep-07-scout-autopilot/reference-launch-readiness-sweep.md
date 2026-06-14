> **Reference artifact, not the canonical body.** This is the exact skill body Microsoft Scout produced during the on-camera Episode 7 run. It is preserved here verbatim so the README, the recording-script, and the video can point at "the skill Scout actually wrote." The canonical, hand-curated version of this skill lives at [`business-skills/launch-readiness-sweep.md`](../../business-skills/launch-readiness-sweep.md) and is the one pushed to Dataverse for ongoing use. Both versions sweep Outlook + Teams and dedup via `search_data`; this one captures the additional tool-call gotchas Scout discovered live (Graph PowerShell single-process auth, `search_data` scope-vs-model distinction, `read_query` parameter name, etc).
>
> Source: `skills/Launch Readiness Sweep` (skillId `2af0c533-0768-f111-a825-000d3a323beb`, uniquename `cr719_launchreadinesssweep`). Fetched at the start of the automation run captured on camera.

---

# Launch Readiness Sweep

**Purpose:** Sweep recent Outlook mail + Teams messages for launch-impacting issues (blockers, escalations, regressions, slips, can't-ship, P0s) and file them as tasks against the right launch in LaunchControl Dataverse, **without ever creating a duplicate**. Always reconcile against existing open tasks first, including the contents of any PDF/doc collateral attached to those tasks.

**Triggers:** "sweep my inbox for launch issues", "launch readiness sweep", "any new blockers on `<launch>`", "scan mail + Teams for `<launch>` issues".

---

## Inputs

- Optional: a specific launch name (e.g. "Phoenix GA"). If omitted, run for **every active launch** the user owns or is on the DRI list for.
- Optional: lookback window. Default = **last 7 days**. Honor explicit user override ("since Monday", "last 24 hours").

## Phase 1 — Resolve launches

1. `launch_control-search` for the launch table (likely `lc_launch`). `launch_control-describe` it to confirm column names and the GUID column.
2. `launch_control-read_query` for active launches:
   ```sql
   SELECT TOP 50 lc_launchid, lc_name, lc_code, lc_launchstatus, lc_targetdate
   FROM lc_launch
   WHERE statecode = 0
   ```
   Note: `read_query` parameter name is `querytext` (not `query` or `sql`).
3. Build a per-launch keyword set: official name, code, common abbreviations, aliases.

## Phase 2 — Collect signals

For each launch, gather candidate issue signals over the lookback window. **Run mail + Teams sweeps in parallel.**

- **Outlook** (`workiq_search_emails` / `workiq_get_email`): subject + body, launch keywords AND any of: `blocker`, `block`, `escalat`, `regression`, `regress`, `slip`, `slipping`, `can't ship`, `cannot ship`, `won't ship`, `P0`, `Sev0`, `Sev 0`, `red`, `at risk`, `stop ship`, `ship-stop`, `livesite`, `incident`.
- **Teams** (`workiq_search_chats` / `workiq_list_chat_messages`): same keyword logic.

For each hit capture: source id/permalink, sender, timestamp, surrounding paragraph, and metadata for any file attachments.

### 2a. Pulling Outlook attachment binaries (required for collateral)

WorkIQ tools surface attachment **metadata** but not bytes. Use Microsoft Graph PowerShell. **Auth + download must be in the SAME PowerShell process**, `Connect-MgGraph` context is in-process only and is lost between separate sync `powershell` invocations. Wrap everything in one script:

```powershell
Import-Module Microsoft.Graph.Authentication
Connect-MgGraph -Scopes "Mail.Read" -NoWelcome -ContextScope Process | Out-Null
# WAM uses cached Windows account; first run may pop a sign-in window.

$out = "<workspace>\Scratchpad"
$emails = @{ "<messageId1>" = "<filename1.pdf>"; "<messageId2>" = "<filename2.pdf>" }
foreach ($mid in $emails.Keys) {
  $name = $emails[$mid]
  $atts = Invoke-MgGraphRequest -Method GET -Uri "https://graph.microsoft.com/v1.0/me/messages/$mid/attachments"
  foreach ($a in $atts.value) {
    if ($a.name -eq $name) {
      [System.IO.File]::WriteAllBytes((Join-Path $out $name), [Convert]::FromBase64String($a.contentBytes))
    }
  }
}
```

If `Microsoft.Graph.Authentication` isn't installed: `Install-Module Microsoft.Graph.Authentication -Scope CurrentUser -Force`.

For Teams attachments, use `workiq_download_file` (OneDrive-backed) where the chat references a file URL.

## Phase 3 — Cluster into findings

Group raw signals into distinct **findings** (one finding = one underlying issue):
- `launch_id`
- `summary` (one sentence)
- `severity` (P0/P1/P2 inferred from language → `lc_priority` choice)
- `category` (`lc_category` choice: Engineering/Marketing/Legal/Operations/Planning/Documentation/Localization/Tooling)
- `evidence[]`: `{source, url, ts, snippet, local_attachment_paths[]}`

Two signals belong to the same finding when they reference the same component/symptom/root-cause, not just the same keyword.

## Phase 4 — Dedup against existing tasks (the critical rule)

**Never call `create_record` for a task before doing this.** For each finding:

1. **Title/notes/collateral match**: `launch_control-search_data` against an `lc_task` scope, using high-signal phrases (component, error text, build #, customer name). `search_data` indexes file column content, so this single call covers titles, notes, AND attached PDF/doc text. *Note:* `scope` must be a skill scope path (`scopes/...`) bound to a Dataverse search index; confirm via `launch_control-search` for available scopes. A model scope path will return "Skill not found".
2. **Structured filter**: `launch_control-read_query`:
   ```sql
   SELECT lc_taskid, lc_title, lc_taskstatus, lc_priority, lc_isblocked, lc_notes, modifiedon
   FROM lc_task
   WHERE lc_launchid = '<launchGuid>'
     AND statecode = 0
     AND lc_taskstatus <> 10600304
   ```
   Choice values: NotStarted=10600301, InProgress=10600302, Blocked=10600303, Done=10600304.
3. **Decision:**
   - **Strong match** → DO NOT create. Instead: attach new collateral (Phase 5b) + `launch_control-update_record` to append:
     ```
     [YYYY-MM-DD HH:MM PT] [SWEEP] <source>: <one-line summary>. Collateral: <filename> attached.
     ```
     Bump `lc_priority` upward only if new evidence clearly warrants it.
   - **No match** → proceed to Phase 5.
   - **Ambiguous** → `m_ask_user` with both candidates side-by-side; never silently merge or split.

## Phase 5 — File a new task (only when Phase 4 found nothing)

### 5a. Create the task
`launch_control-create_record` on `lc_task`. Required param names: `tablename`, `item` (object). Critical fields:
- `lc_title`, `lc_notes` (include source link + timestamp)
- `lc_priority` choice: Critical=10600401, High=10600402, Medium=10600403, Low=10600404
- `lc_category` choice (see Phase 3)
- `lc_taskstatus` = 10600301 (NotStarted) or 10600303 (Blocked)
- `lc_isblocked` (bool) + `lc_blockerreason` (string) when blocked
- `lc_launchid` lookup: `{"relatedTable": "lc_launch", "recordId": "<launchGuid>"}`

Capture the returned GUID.

### 5b. Attach collateral (also reused on Phase 4 strong-match path)
For each local attachment file:
1. `launch_control-init_file_upload` with `tablename`, `recordId`, `fileAttributeName: "lc_relateddocuments"`, `fileName`. Returns `SasUrl` + `FileContinuationToken`.
2. HTTP PUT the bytes:
   ```powershell
   Invoke-WebRequest -Method Put -Uri $sasUrl -InFile $localPath `
     -ContentType "application/octet-stream" `
     -Headers @{"x-ms-blob-type"="BlockBlob"} -UseBasicParsing
   ```
   Expect HTTP 200/201.
3. `launch_control-commit_file_upload` with `continuationToken` + `fileName`.

## Phase 6 — Report

Single chat summary:
- **New tasks filed:** N (title + GUID + launch)
- **Existing tasks updated:** M (title + what was appended/attached)
- **Skipped as duplicate (no update needed):** K
- **Ambiguous, asked user:** open questions

---

## Hard rules

1. **No duplicate tasks, ever.** If Phase 4 is uncertain, ask, don't guess.
2. **Always run `search_data` before `create_record`**, it is the only call that searches inside attached PDFs.
3. **Preserve provenance.** Every task note ends with the source URL/permalink and timestamp.
4. **Private data stays private.** Never include customer names or internal escalation language in any outbound message; this skill writes only to Dataverse, never sends mail/Teams.
5. **Attachments go on the task, not in the note body.** Notes get a one-line pointer; the PDF/doc itself is uploaded to `lc_relateddocuments` via init → PUT → commit.

## Tool-call gotchas (from real runs)

- `read_query` parameter is `querytext` (not `query`/`sql`).
- `update_record` / `create_record` / `init_file_upload` / `delete_record` use `tablename` (not `table`) and `item` (not `data`/`fields`) for the payload.
- `delete_record` requires `hasUserApproved: true` (the field name, not `userApproval`/`approvedByUser`/`userApprovedDeletion`).
- `search_data` requires a real skill `scope`; passing a model scope returns "Skill not found".
- Deactivate (don't delete) duplicates by setting `statecode: 1, statuscode: 2` via `update_record`. Reactivate with `statecode: 0, statuscode: 1`.
- Outlook attachment binaries: not available via `workiq_*`. Use Graph PowerShell in a single-process script (Phase 2a).
