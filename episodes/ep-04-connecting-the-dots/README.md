# Episode 4 — Connecting the Dots

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Virtual Entities (OOB SharePoint + custom GitHub Issues provider)
**Layer:** 🟢 Layer 1 expands (Data — without copying it)
**Coding agent:** Claude Code · **Runtime:** .NET Framework 4.6.2 plugin (Sandbox)

---

## The hook

> _"Our engineering backlog lives in GitHub. The PM playbook is on SharePoint. The launch tracker is in Dataverse. What if they were all the same table?"_

Episode 3 promoted the staging trackers into the unified `lc_Task` / `lc_Milestone` /
`lc_Launch` model. The unified core is real. But the work itself doesn't all live
in Dataverse — it never will. Engineering issues live in GitHub. Some teams keep
status in SharePoint lists. Copying that data nightly is exactly what we don't
want.

Episode 4 closes that loop without copying anything: **virtual entities**. Two
approaches, one query surface.

---

## The narrative beat

The opening shot is a query:

```sql
SELECT lc_name, source_system FROM (lc_Task ∪ lc_SharePointTask ∪ lc_GitHubIssue)
WHERE state = 'open'
```

That query is impossible in any one system. By the end of the episode, it
returns rows from three.

---

## Part 1 · OOB SharePoint List virtual entity

> Ten clicks, no code.

In the Power Apps maker portal:

1. **Tables → New table → Virtual table**
2. Pick **SharePoint** as the data provider (built-in)
3. Paste the SharePoint site URL and list name
4. Map the SharePoint columns to Dataverse columns — title, status, owner,
   due date
5. Save

The list now appears alongside `lc_Task` and friends. Every read goes live to
SharePoint — no sync, no schedule, no stale data.

**The point of Part 1:** Microsoft already wrote a SharePoint provider. For the
common cases — Excel/SharePoint/SQL — you don't write code. You point and
click.

---

## Part 2 · Custom GitHub Issues virtual entity

> When OOB doesn't cover your system, you build the provider.

GitHub doesn't ship as a Dataverse virtual entity provider. So we build one —
a .NET 4.6.2 plugin that implements `RetrieveMultiple` and `Retrieve` against
the GitHub REST API, mapping each issue to a deterministic Dataverse record.

### The plugin (Claude Code writes it)

[`GitHubIssuesProvider/Class1.cs`](../../datamodel/virtual-entities/GitHubIssuesProvider/GitHubIssuesProvider/Class1.cs) is two
plugin classes:

- `RetrieveMultiplePlugin.Execute` — calls `GET /repos/{owner}/{repo}/issues`,
  filters out pull requests (the GitHub API returns them as issues), and maps
  each issue to a Dataverse `Entity` with deterministic GUID derived from the
  issue number so the same issue always maps to the same record ID.
- `RetrievePlugin.Execute` — single-issue lookup by GUID.

### The columns

| Dataverse column | GitHub field | Type |
|---|---|---|
| `lc_name` | `title` | String |
| `lc_description` | `body` | Memo |
| `lc_issuenumber` | `number` | Integer |
| `lc_state` | `state` (open/closed) | String |
| `lc_url` | `html_url` | String |
| `lc_assignee` | `assignee.login` | String |
| `lc_createdat` | `created_at` | DateTime |
| `lc_updatedat` | `updated_at` | DateTime |
| `lc_labels` | `labels[]` (comma-joined) | String |

### Registration in seven steps

The full procedure — including every gotcha — is in
[`SETUP-GUIDE.md`](../../datamodel/virtual-entities/SETUP-GUIDE.md). The short
version:

1. **Build** the plugin (`dotnet build --configuration Release`, .NET 4.6.2,
   strong-named).
2. **Register the assembly** via Web API (`POST /pluginassemblies`) —
   isolation mode = Sandbox.
3. **Register the plugin types** explicitly (`POST /plugintypes`) — uploading
   the assembly does not auto-register them.
4. **Register the data provider** in the Plugin Registration Tool (PRT). PRT
   is required here because it creates the `entitydataprovider` AND the
   `lc_githubdatasource` data-source entity together — the Web API can't.
5. **Create the virtual table** via Web API with `TableType: "Virtual"` and
   the critical managed property `CanCreateCharts: {Value: false, CanBeChanged: false}`.
6. **Add the columns** via Web API, with each `ExternalName` matching the key
   the plugin sets on the entity.
7. **Test** — `SELECT lc_name, lc_state FROM lc_githubissue` via MCP triggers
   the plugin, which calls the GitHub API, which returns 6 live issues as
   Dataverse records.

The episode shows Claude Code writing the plugin from a one-line spec ("build
a virtual entity provider for GitHub issues") and walking the developer
through the registration commands. The narrative beat is _"Claude can do this
in .NET too — Microsoft's plugin framework is just C# at the end of the day."_

---

## Part 3 · Stitching the VE into the model

> A virtual entity beside `lc_task` is interesting. A virtual entity *as a
> lookup target on* `lc_task` is the unlock.

Reading the same data shape from three systems is the warm-up. The real prize
is making the GitHub issue a **first-class related row** of the launch task —
so the lookup field on `lc_task` resolves to a live GitHub issue title, the
Power Apps form shows it, MCP `$expand` returns it, the Python SDK can join
on it.

### One column, one relationship

```python
client.tables.create_lookup_field(
    "lc_task",                  # source
    "lc_GitHubIssueId",          # the new column
    "lc_githubissue",           # target — the virtual entity
    display_name="GitHub Issue",
)
```

That single SDK call creates a real Dataverse `Lookup` attribute on `lc_task`
(`AttributeType = Lookup`, `Targets = ['lc_githubissue']`), plus the implicit
N:1 relationship. From that moment on, every Dataverse-aware surface treats
the GitHub issue like any other related row.

### What about the lookup label?

Lookup columns display the target row's **primary name** by default. For a
virtual entity, that means `RetrievePlugin` is suddenly on the hot path —
every form render, every `$expand`, every Power Apps gallery row will hit it.
The original `RetrievePlugin` was anemic (returned just the issue number).
We rewrote it to call `GET /repos/{owner}/{repo}/issues/{number}` and populate
all VE fields, with a graceful fallback if GitHub is unreachable.

### Bind 6 tasks to live issues

The provider already publishes deterministic GUIDs — issue #N → a fixed
`0000cdab-0000-0000-0000-0000{N:02x}000000` GUID. So binding is just six
PATCHes:

```python
PATCH /api/data/v9.2/lc_tasks({task_id})
{ "lc_GitHubIssueId@odata.bind":
    "/lc_githubissues(0000cdab-0000-0000-0000-000001000000)" }
```

[`scripts/python/bind_ve_lookup.py`](../../scripts/python/bind_ve_lookup.py)
maps six tasks to six issues by topic — rate limiting, load test, docs,
security, marketing, OSS license — and PATCHes them in one pass.

### The unified query, for real

```python
# scripts/python/unified_view.py
GET /api/data/v9.2/lc_tasks
   ?$select=lc_taskid,lc_title,_lc_githubissueid_value
   &$expand=lc_GitHubIssueId($select=lc_issuenumber,lc_name,lc_state,lc_url)
```

One Web API call. Dataverse joins `lc_task` (relational, in-database) with
`lc_githubissue` (virtual, projected from GitHub on demand) through the new
lookup. The plugin runs once per linked task, the GitHub API answers, and the
result set looks like any other relational join:

```
=== Tasks linked to live GitHub Issues (6 of 30 total) ===

Task                                  Issue   State   GitHub Title
-------------------------------------------------------------------------------
Audit widget API rate limits          #1      open    Widget API: Add rate limiting...
Customer-facing widget documentation  #3      open    Docs: Update API reference for v2...
Open-source license audit             #6      open    Legal: OSS license compliance check
GTM campaign for Smart Widget Pro     #5      open    Marketing: Landing page copy...
Snyk for SCA scanning                 #4      open    Security: Rotate pre-launch API keys
k6 Cloud subscription                 #2      open    Load test: Verify 10k concurrent users
```

> _"From the task form, I search live GitHub issues, pick one, save. The
> Power Apps code app, the MCP agent, the Python SDK — they all see one
> model. The foreign table just happens to live in GitHub."_

---

## What's deliberately NOT in this episode

- **A custom MCP server.** Custom MCP is Episode 5, and it solves a different
  problem (server-side actions, not federated reads). Mixing the two would
  blur the lesson.
- **Write-through.** Both providers are read-only. Letting agents modify the
  source systems is a meaningful next step but it's a write-path concern with
  its own auth story; out of scope for the "connecting" beat.
- **Re-platforming the SharePoint Word-doc playbook.** Episode 2 already
  codified the playbook into business skills. The SharePoint VE here is for
  the team's task list, not the Word doc.

---

## What you see on screen

1. The maker portal: ten clicks build the SharePoint List virtual entity.
   Live rows appear in the table designer.
2. Claude Code in a terminal: _"build a virtual entity provider for GitHub
   issues"_ → it writes `Class1.cs`, the `.csproj`, and the registration
   walkthrough.
3. PRT — the one mandatory GUI step — fills in the data provider + data
   source.
4. Web API calls (via Python helpers) create the virtual table and its
   columns.
5. MCP query: `SELECT lc_name, lc_state FROM lc_githubissue` — 6 live GitHub
   issues appear as Dataverse rows.
6. The `$expand` query from Part 3 — `lc_task` joined to live GitHub issues
   through the new lookup, in one Web API call.
7. **The punchline:**
   > _"Three systems. Zero copies. One query.
   > That's what 'native to Dataverse' really means."_

---

## Files in this episode

| File | Role |
|---|---|
| [`datamodel/virtual-entities/GitHubIssuesProvider/`](../../datamodel/virtual-entities/GitHubIssuesProvider/) | The .NET 4.6.2 plugin — both `RetrieveMultiplePlugin` and `RetrievePlugin`. |
| [`datamodel/virtual-entities/README.md`](../../datamodel/virtual-entities/README.md) | Provider overview + column map. |
| [`datamodel/virtual-entities/SETUP-GUIDE.md`](../../datamodel/virtual-entities/SETUP-GUIDE.md) | The full step-by-step including PRT MFA workaround, virtual-table flags, and `DataContractJsonSerializer` date-format fix. |
| [`scripts/python/add_ve_lookup.py`](../../scripts/python/add_ve_lookup.py) | One-line SDK helper: adds the `lc_GitHubIssueId` lookup on `lc_task` targeting the VE. |
| [`scripts/python/bind_ve_lookup.py`](../../scripts/python/bind_ve_lookup.py) | Web API PATCHes that wire 6 tasks to 6 GitHub issues by topic. |
| [`scripts/python/unified_view.py`](../../scripts/python/unified_view.py) | The climactic `$expand` query — relational core × live VE in one call. |
| [`scripts/register_ve_plugin.py`](../../scripts/register_ve_plugin.py) | Web API helper that uploads the assembly + registers plugin types. |
| [`scripts/setup_virtual_entity.py`](../../scripts/setup_virtual_entity.py) | Web API helper that creates the virtual table + columns. |
| [`scripts/create_ve_table.py`](../../scripts/create_ve_table.py) | Lower-level table-creation helper (used during iteration). |
| [`scripts/check_ve.py`](../../scripts/check_ve.py) | One-line existence check against `EntityDefinitions(LogicalName='lc_githubissue')`. |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# 1. Build the plugin (.NET 4.6.2)
dotnet build datamodel/virtual-entities/GitHubIssuesProvider/GitHubIssuesProvider --configuration Release

# 2. Register assembly + plugin types (Web API)
python scripts/register_ve_plugin.py

# 3. Manual: register the data provider + data source via PRT
#    (see SETUP-GUIDE.md — leave username blank for MFA browser auth)

# 4. Create the virtual table + columns
python scripts/setup_virtual_entity.py

# 5. Verify
python scripts/check_ve.py
# → EXISTS: lc_githubissue (TableType=Virtual)

# 6. Query via MCP (in your IDE):
#    SELECT lc_name, lc_state, lc_issuenumber FROM lc_githubissue
```

---

## Pitfalls collected during the build

These are the ones the SETUP-GUIDE catches in detail:

- `CanChangeTrackingBeEnabled can not be active` — virtual entities require this managed property explicitly set to `{Value: false, CanBeChanged: false}`.
- `Cannot create charts for virtual Entity` — same fix, `CanCreateCharts`.
- `DateTime content does not start with /Date(` — `DataContractJsonSerializer` defaults to MS-format dates. Use `DateTimeFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'"`.
- `dependent component does not exist` when creating the table — happens when the data provider was created without a paired data source. PRT creates both; the Web API alone does not.
- `AADSTS50076 MFA error` in PRT — leave username/password blank → PRT pops a browser auth dialog that supports MFA.
- `lc_launches not found` — the auto-pluralized entity-set name is `lc_launchs`, not `lc_launches`. Check `client.tables.get()` if in doubt.

Each one is a 30-minute detour the first time. The setup guide makes the
second time take five minutes.
