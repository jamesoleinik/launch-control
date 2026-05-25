# Episode 4 — Extending & Enforcing the Model

**Status:** ✅ Part 1 built and verified · ✅ Part 2 + Part 3 scripts written and verified end-to-end · 🎬 Not yet recorded
**Features:** ⭐ Virtual Entities (custom GitHub Issues provider, .NET 4.6.2) · ⭐ **Server-side rule trio** (three sync plugin steps on `lc_task` Update — block, unblock, completion-guard) authored by the coding agent — guardrails the agent layer must honor
**Layer:** 🟢 Layer 1 expands (Data — without copying it) + 🟢 server-side enforcement expressed as code
**Coding agent:** Claude Code · **Runtime:** .NET Framework 4.6.2 plugin (Sandbox) for both the VE provider AND the enforcement step

---

## The hook

> _"'Engineering wants their bugs in GitHub Issues.' 'The other engineering team lives in ADO.' 'The platform crew swears by Linear.' 'Sales just emails them to me personally.' Every PM running a cross-team launch rolls their eyes, opens a 47-tab Notion doc, and resigns themselves to copy-pasting work items between five tools."_
>
> _"Fine. I'll just unify it in Dataverse — without copying a single row. And while I'm in there, I'll write the rule that every agent in this org has to honor."_

Episode 3 promoted the staging trackers into a unified `lc_Task` / `lc_Milestone` /
`lc_Launch` model. The core is real. But the work itself doesn't all live in
Dataverse — and it never will. Engineering's open backlog lives in GitHub.
Copying it nightly is exactly what we don't want; by the time the sync runs,
half the rows are stale.

Episode 4 closes the loop without copying anything: **virtual entities**. Then
it does the thing that turns this model from "a schema" into "a contract" — the
coding agent writes a **trio of server-side enforcement rules** over the unified
shape. Not JavaScript on a form. Not advice your client app can choose to ignore.
Three sync plugin steps that live in the platform and run on every write,
including writes from the agent layer we're about to build in later episodes.
Enforcement is just three `sdkmessageprocessingstep` rows in Dataverse, and the
agent can write records — so the agent can author its own guardrails.

---

## The narrative beat

The opening shot is a query:

```sql
SELECT lc_name, source_system FROM (lc_Task ∪ lc_GitHubIssue)
WHERE state = 'open'
```

That query is impossible in any one system. By the end of the episode, it
returns rows from two — one of them not Dataverse.

---

## Part 1 · Custom GitHub Issues virtual entity

> When OOB doesn't cover your system, you build the provider.

GitHub doesn't ship as a Dataverse virtual entity provider. So we build one —
a .NET 4.6.2 plugin that implements `RetrieveMultiple` and `Retrieve` against
the GitHub REST API, mapping each issue to a deterministic Dataverse record.

> **The data is real.** The six issues this provider projects are not seed
> data — they're the actual planning backlog of this series at
> [github.com/jamesoleinik/launch-control/issues](https://github.com/jamesoleinik/launch-control/issues)
> (rate limiting, load test, docs rotation, security keys, GTM copy, OSS
> license). The six `lc_task` rows we'll bind them to in Part 2 are the real
> Smart Widget Pro launch tasks already in the env from Episode 3. The
> `lc_url` value you'll see projected on the form **is the URL you can click
> right now**.

### The plugin

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
4. **Register the data provider.** Either:
   - **(GUI path)** Plugin Registration Tool → Register New Data Provider —
     the documented, on-camera path. PRT writes two rows: an
     `entitydataprovider` and the `lc_githubdatasource` data-source virtual
     entity.
   - **(Web-API path, PRT-optional)**
     [`scripts/python/register_ve_data_provider.py`](../../scripts/python/register_ve_data_provider.py)
     writes the same two rows directly — useful for clean-slate rebuilds
     and CI. Reverse-engineered and verified end-to-end; details in the
     [appendix](#appendix--prt-is-optional) at the bottom of this README.
5. **Create the virtual table** via Web API with `TableType: "Virtual"` and
   the critical managed property `CanCreateCharts: {Value: false, CanBeChanged: false}`.
6. **Add the columns** via Web API, with each `ExternalName` matching the key
   the plugin sets on the entity.
7. **Test** — `SELECT lc_name, lc_state FROM lc_githubissue` via MCP triggers
   the plugin, which calls the GitHub API, which returns the 6 real planning
   issues on this repo's public issues page as Dataverse records.

On camera, Claude Code writes the entire plugin from one prompt, then walks
through the registration commands. The takeaway:
_"Claude can do this in .NET too — Microsoft's plugin framework is just C# at
the end of the day."_

### The on-camera prompt (verbatim)

`datamodel/virtual-entities/GitHubIssuesProvider/GitHubIssuesProvider/Class1.cs`
is deleted before the camera rolls — the hero shot is the agent creating it
from scratch.

```text
Build a Dataverse virtual entity that reads live GitHub issues from
this repo's planning backlog (github.com/jamesoleinik/launch-control)
so I can query lc_githubissue and see the 6 open issues as Dataverse
rows. The provider goes at
datamodel/virtual-entities/GitHubIssuesProvider/. Column map and
registration walkthrough are in datamodel/virtual-entities/README.md
and SETUP-GUIDE.md.
```

---

## Part 2 · Stitching the VE into the model

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
maps the six `lc_task` rows to the six **real** GitHub issues on this repo by
topic — rate limiting (#1), load test (#2), docs (#3), security (#4),
marketing (#5), OSS license (#6) — and PATCHes them in one pass. After the
PATCH, every Dataverse-aware surface treats the public-repo URL as a
first-class related row.

### The on-camera prompt (verbatim)

`scripts/python/unified_view.py` is deleted before the camera rolls — the hero
shot is the agent stitching `lc_task` to live GitHub issues and writing the
verify script in one autonomous pass.

```text
Wire 6 of my 61 lc_task rows to lc_githubissue by topic — rate-limiting,
load testing, docs, security, marketing, OSS license — one task per
issue. Then print me a single table of the 6 tasks joined to their
live GitHub issues: task title, issue number, issue state, issue URL.
```

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
=== Tasks linked to live GitHub Issues (6 of 61 total) ===

Task                                  Issue   State   GitHub Title
-------------------------------------------------------------------------------
Audit widget API rate limits          #1      open    Widget API: Add rate limiting...
k6 Cloud subscription                 #2      open    Load test: Verify 10k concurrent users
Customer-facing widget documentation  #3      open    Docs: Update API reference for v2...
Snyk for SCA scanning                 #4      open    Security: Rotate pre-launch API keys
Landing page copy VP approval         #5      open    Marketing: Landing page copy...
Open-source license audit             #6      open    Legal: OSS license compliance check
```

> _"From the task form, I search live GitHub issues, pick one, save. The
> Power Apps code app, the MCP agent, the Python SDK — they all see one
> model. The foreign table just happens to live in GitHub."_

---

## Part 3 · Server-side rule trio authored by the coding agent

> Dataverse ships drag-and-drop "Business Rules" in the maker portal. They're great — but the moment you need them to honor writes from **outside the form** (SDK, MCP, Power Automate, agents), the Web API rejects every hand-crafted or template-cloned business-rule row with `0x80045037 "Error generating UiData"`. The maker designer's UiData generator is mandatory and not agent-bypassable. So we author the same enforcement as **sync plugin steps** instead — the canonical Dataverse server-side mechanism, fully agent-authorable, and provably fires on every write.

### The lifecycle, in three rules

We layer **three** rules on `lc_task`. Together they enforce a complete blocker-and-completion lifecycle that the agent — and any other caller — must honor:

| # | Rule | Trigger | What it does |
|---|------|---------|---------------|
| 1 | **TaskBlockedRule** | `lc_blockerreason` set to a non-empty value | Force `lc_taskstatus = Blocked` in the same write |
| 2 | **TaskUnblockedRule** | `lc_blockerreason` cleared on a previously-Blocked task | Revert `lc_taskstatus = InProgress` in the same write (needs PreImage) |
| 3 | **TaskCompletionGuardRule** | Caller tries to set `lc_taskstatus = Done` | Reject with `InvalidPluginExecutionException` if a blocker reason is still set (needs PreImage) |

Rule 1 and Rule 2 are symmetric: setting a blocker auto-blocks, clearing it auto-unblocks. Rule 3 is the "you shall not ship" — you cannot mark Done while the platform still sees a blocker on the row, no matter which client is calling.

### Underneath, each rule is just a ~60-line C# plugin + a step row

Dataverse persists every server-side rule as two records: a `plugintype` row that points at a method in a .NET assembly, and an `sdkmessageprocessingstep` row that says "fire this plugintype when message X happens on entity Y." Rules 2 and 3 also need a third record — an `sdkmessageprocessingstepimage` (a **PreImage**) — so the plugin can read fields the caller didn't include in the update.

The simplest of the three, the canonical shape, is Rule 1:

```csharp
public class TaskBlockedRulePlugin : IPlugin
{
    private const int Blocked = 10600303;
    public void Execute(IServiceProvider serviceProvider)
    {
        var context = (IPluginExecutionContext)serviceProvider.GetService(typeof(IPluginExecutionContext));
        var target  = (Entity)context.InputParameters["Target"];
        if (context.MessageName != "Update" || context.PrimaryEntityName != "lc_task") return;
        if (!target.Attributes.Contains("lc_blockerreason")) return;
        if (target["lc_blockerreason"] is string s && !string.IsNullOrWhiteSpace(s))
            target["lc_taskstatus"] = new OptionSetValue(Blocked);
    }
}
```

Each step row is registered with the same skeleton:

- `stage = 20` — Pre-operation (we mutate Target **before** SQL writes it)
- `mode = 0` — Synchronous (runs in the caller's transaction; never deferred)
- `filteringattributes` — only fires when the relevant column is in the write payload (`lc_blockerreason` for rules 1+2, `lc_taskstatus` for rule 3)
- `supporteddeployment = 0` — Server only

Rules 2 and 3 add one extra record — a PreImage named `PreImg` — so they can read `lc_taskstatus` (Rule 2) or `lc_blockerreason` (Rule 3) from the row's pre-update state even when the caller didn't include those fields in the PATCH.

All three plugin classes live in the **same** .NET assembly we built in Part 1 — one DLL, five plugin classes (`RetrieveMultiplePlugin`, `RetrievePlugin`, `TaskBlockedRulePlugin`, `TaskUnblockedRulePlugin`, `TaskCompletionGuardRulePlugin`). Adding the rule trio costs three C# files and three extra entries in the `PLUGIN_TYPES` list in [`scripts/register_ve_plugin.py`](../../scripts/register_ve_plugin.py).

### The coding agent writes the trio

`TaskBlockedRule.cs`, `TaskUnblockedRule.cs`, `TaskCompletionGuardRule.cs`, and `scripts/python/task_rules.py` are all **deleted** before the camera rolls — same hero-shot setup as the GitHub provider in Part 1. The agent writes the three C# plugin classes, rebuilds the assembly, re-registers it (so the new classes show up as `plugintype` rows), and then writes the Python helper that resolves the right `sdkmessageid` + `sdkmessagefilterid` and POSTs the three step rows + the two pre-image rows.

#### The on-camera prompt (verbatim)

```text
Add three server-side rules on the lc_task table and prove each one
fires from a raw SDK PATCH (no form):

1. When the blocker reason gets set, status auto-flips to Blocked.
2. When the blocker reason gets cleared, status reverts to InProgress
   (only if the task was previously Blocked).
3. Trying to mark a task Done while it still has a blocker reason
   fails with a clear error; the row stays unchanged.

These have to be plugin steps, not maker-portal business rules —
see datamodel/virtual-entities/SETUP-GUIDE.md for why workflow rows
aren't agent-authorable via the Web API. Add them to the same
assembly as Part 1's GitHub provider.
```

The output is three new C# files (`TaskBlockedRule.cs`, `TaskUnblockedRule.cs`, `TaskCompletionGuardRule.cs`), one new Python script (`task_rules.py`), and three extra lines in `PLUGIN_TYPES` — all runnable from the CLI.

### The round-trip is the proof

After the script runs, three Web API PATCHes — bypassing the form entirely — prove all three rules fire server-side:

1. **Block:** `PATCH lc_tasks({id}) {"lc_blockerreason": "SLA at risk"}` → the response comes back and `lc_taskstatus` has already flipped to **Blocked (10600303)**. Rule 1 fired pre-SQL.
2. **Unblock:** `PATCH lc_tasks({id}) {"lc_blockerreason": null}` → the response comes back and `lc_taskstatus` has reverted to **InProgress (10600302)**. Rule 2 fired pre-SQL, using its PreImage to confirm the previous status was Blocked.
3. **Refuse Done while blocked:** re-set the blocker, then `PATCH lc_tasks({id}) {"lc_taskstatus": 10600304}` → **HTTP 400** with the body `"Cannot mark this task as Done while a blocker reason is set."` Rule 3 fired pre-SQL, consulted its PreImage for the saved blocker, and threw. The row's status is **unchanged**.

Open `make.powerapps.com → Advanced settings → Plug-In Trace Log` to see each rule's trace lines — the plugin is what enforced it, and the platform now owns the lifecycle.

> _"Declarative no-code and code-first don't have to be enemies. A
> Power Automate flow, a Business Rule clicked together in the maker,
> and a sync plugin step are three doors to the same room — and the
> coding agent can walk through any of them. We picked the door that
> works for the Web API, runs in the caller's transaction, and lives
> in version control. Three small rules. Same model. Same shape. The
> lifecycle belongs to the platform now, not to whichever screen you
> happened to open it from."_

That's the closing beat of Episode 4 — the coding agent extending the platform's enforcement layer it never wrote a UI for.

---

## What's deliberately NOT in this episode

- **An OOB SharePoint virtual entity.** Microsoft ships a SharePoint
  provider and it's ten clicks in the maker portal — but the SharePoint
  Word-doc playbook was already codified into business skills in Episode
  2, the launch tracker is in Dataverse, and the engineering tickets are
  the genuinely-elsewhere data. Adding a SharePoint VE just to demo
  point-and-click would dilute the lesson. The "custom provider end-to-end"
  beat (Part 1) is the one the watcher hasn't seen before.
- **A custom MCP server.** Custom MCP is Episode 5, and it solves a different
  problem (server-side actions, not federated reads). Mixing the two would
  blur the lesson.
- **Write-through.** The GitHub provider is read-only. Letting agents modify
  the source systems is a meaningful next step but it's a write-path concern
  with its own auth story; out of scope for the "connecting" beat.
- **Security roles + business units.** RBAC over this now-federated model
  is the entire subject of [Episode 6 — Roles & Reach](../ep-06-rbac/). We
  finish Ep 4 with three rules visible to everyone; Ep 6 is where _who can
  see what_ gets answered.
- **Multi-action / multi-condition rules.** The three enforcement steps we
  author are intentionally minimal — each is one condition + one action (or
  one veto). The point is that the coding agent can write the C# and register
  the steps + pre-images, not that any single rule is complex.
- **The maker portal's "Business Rules" UI.** It's a real feature and
  it's perfectly fine — but its underlying `workflow` rows are not
  agent-authorable via the Web API (UiData generator is mandatory). Once
  we picked "agent-authored from scratch" as a constraint, the sync
  plugin step became the only honest path. Same enforcement, different
  door.

---

## Files in this episode

| File | Role |
|---|---|
| [`datamodel/virtual-entities/GitHubIssuesProvider/`](../../datamodel/virtual-entities/GitHubIssuesProvider/) | The .NET 4.6.2 plugin assembly — five `IPlugin` classes: `RetrieveMultiplePlugin`, `RetrievePlugin`, and the Part 3 rule trio `TaskBlockedRulePlugin`, `TaskUnblockedRulePlugin`, `TaskCompletionGuardRulePlugin`. |
| [`datamodel/virtual-entities/README.md`](../../datamodel/virtual-entities/README.md) | Provider overview + column map. |
| [`datamodel/virtual-entities/SETUP-GUIDE.md`](../../datamodel/virtual-entities/SETUP-GUIDE.md) | The full step-by-step including PRT MFA workaround, virtual-table flags, and `DataContractJsonSerializer` date-format fix. |
| [`scripts/python/add_ve_lookup.py`](../../scripts/python/add_ve_lookup.py) | One-line SDK helper: adds the `lc_GitHubIssueId` lookup on `lc_task` targeting the VE. |
| [`scripts/python/bind_ve_lookup.py`](../../scripts/python/bind_ve_lookup.py) | Web API PATCHes that wire 6 tasks to 6 GitHub issues by topic. |
| [`scripts/python/unified_view.py`](../../scripts/python/unified_view.py) | The Part 2 climactic `$expand` query — relational core × live VE in one call. |
| [`scripts/register_ve_plugin.py`](../../scripts/register_ve_plugin.py) | Web API helper that uploads (and re-PATCHes) the assembly + registers all five plugin types. |
| [`scripts/python/register_ve_data_provider.py`](../../scripts/python/register_ve_data_provider.py) | Web-API-only replacement for PRT — creates the `entitydataprovider` row + the `lc_githubdatasource` data-source virtual entity. Reverse-engineered from a pre/post PRT snapshot. |
| [`scripts/setup_virtual_entity.py`](../../scripts/setup_virtual_entity.py) | Web API helper that creates the virtual table + columns. |
| [`scripts/python/_ep04_teardown.py`](../../scripts/python/_ep04_teardown.py) | Destructive teardown — removes the three rule steps + their pre-images, the five plugintypes, the assembly, entitydataprovider, data-source entity, lookup, and virtual table so the rebuild path can be verified from a clean slate. |
| [`scripts/create_ve_table.py`](../../scripts/create_ve_table.py) | Lower-level table-creation helper kept from early iteration; `setup_virtual_entity.py` is the version actually used. |
| [`scripts/check_ve.py`](../../scripts/check_ve.py) | One-line existence check against `EntityDefinitions(LogicalName='lc_githubissue')`. |
| [`scripts/python/task_rules.py`](../../scripts/python/task_rules.py) | Claude-authored Web API helper that POSTs the Part 3 rule trio — three `sdkmessageprocessingstep` rows + two `sdkmessageprocessingstepimage` (PreImg) rows. Binds `TaskBlockedRulePlugin`, `TaskUnblockedRulePlugin`, `TaskCompletionGuardRulePlugin` to Pre-operation Update of `lc_task`, sync mode, server-only deployment. Idempotent on step name. |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# 1. Build the plugin (.NET 4.6.2)
dotnet build datamodel/virtual-entities/GitHubIssuesProvider/GitHubIssuesProvider --configuration Release

# 2. Register assembly + plugin types (Web API)
python scripts/register_ve_plugin.py

# 3. Register the data provider + data-source entity. Two equivalent paths:
#    (a) GUI:    open PRT, Register -> Register New Data Provider
#                (see SETUP-GUIDE.md - leave username blank for MFA browser auth)
#    (b) Script: python scripts/python/register_ve_data_provider.py `
#                  --provider-name GitHubIssuesProvider `
#                  --datasource-logical lc_githubdatasource `
#                  --datasource-display "GitHub Data Source" `
#                  --datasource-plural  "GitHub Data Sources" `
#                  --assembly-name      GitHubIssuesProvider
#    Both write the same two rows; the on-camera demo uses PRT, the rebuild
#    path uses the script.

# 4. Create the virtual table + columns
python scripts/setup_virtual_entity.py

# 5. Verify
python scripts/check_ve.py
# → EXISTS: lc_githubissue (TableType=Virtual)

# 6. Query via MCP (in your IDE):
#    SELECT lc_name, lc_state, lc_issuenumber FROM lc_githubissue

# 7. (Part 3) Author + register the server-side rule trio
#    - Agent writes three IPlugin classes in datamodel/.../GitHubIssuesProvider/:
#        TaskBlockedRule.cs / TaskUnblockedRule.cs / TaskCompletionGuardRule.cs
#    - Agent re-builds the assembly:
dotnet build datamodel/virtual-entities/GitHubIssuesProvider/GitHubIssuesProvider/GitHubIssuesProvider.csproj --configuration Release
#    - Re-register so the three new plugintypes show up + new DLL is uploaded:
python scripts/register_ve_plugin.py
#    - Register the three SdkMessageProcessingSteps + two PreImages:
python scripts/python/task_rules.py
#    → resolves plugintype + sdkmessage Update + sdkmessagefilter lc_task,
#      POSTs three steps (stage=20, mode=0, filteringattributes per rule),
#      and POSTs PreImage 'PreImg' on the unblock + completion-guard steps.
#      Idempotent on step name.

# 8. (Part 3 proof) Three PATCHes prove all three rules fire server-side:
#    a) PATCH lc_blockerreason="..."  → status auto-flips to Blocked
#    b) PATCH lc_blockerreason=null   → status reverts to InProgress (PreImg)
#    c) PATCH lc_taskstatus=Done while blocker still set → HTTP 400 rejection
#    All in the same response, no form involved. Lifecycle belongs to the
#    platform.
```

---

## Pitfalls collected during the build

These are the ones the SETUP-GUIDE catches in detail:

- `CanChangeTrackingBeEnabled can not be active` — virtual entities require this managed property explicitly set to `{Value: false, CanBeChanged: false}`.
- `Cannot create charts for virtual Entity` — same fix, `CanCreateCharts`.
- `DateTime content does not start with /Date(` — `DataContractJsonSerializer` defaults to MS-format dates. Use `DateTimeFormat = "yyyy-MM-dd'T'HH:mm:ss'Z'"`.
- `dependent component does not exist` when creating the table — happens when the data provider was created without a paired data source. Both PRT and `register_ve_data_provider.py` create the pair atomically; calling the Web API yourself without the data-source entity will trigger this.
- `An ODataPrimitiveValue was instantiated with a value of type 'ODataEntityReferenceLink'` when POSTing to `entitydataproviders` — the `retrievemultipleplugin` / `retrieveplugin` / etc. columns are `Uniqueidentifier` primitives, **not** lookups. Send raw GUID strings, not `@odata.bind`.
- `CanChangeTrackingBeEnabled can not be active for ... virtual Entity` when creating the data-source entity — the data source is itself a virtual entity and needs the full virtual-entity managed-property set (same gotcha as the consuming `lc_githubissue` table).
- `External Collection Name property required` — set `ExternalCollectionName` on the data-source entity, not just `ExternalName`.
- `AADSTS50076 MFA error` in PRT — leave username/password blank → PRT pops a browser auth dialog that supports MFA.
- `lc_launches not found` — the auto-pluralized entity-set name is `lc_launchs`, not `lc_launches`. Check `client.tables.get()` if in doubt.
- `0x80045037 Error generating UiData` on `POST /workflows` — Dataverse rejects every hand-crafted or template-cloned business-rule row authored via the Web API. The maker-designer's UiData generator is mandatory and not agent-bypassable. This is why Part 3 uses a sync plugin step (`POST /sdkmessageprocessingsteps`) instead — the canonical server-side enforcement path that the Web API does accept.
- **Step registers but never fires** — common causes: (a) `mode=1` (async) instead of `0` (sync), so the change isn't visible until the async job runs, (b) `stage=40` (post-operation) instead of `20` (pre-op), so the Target mutation happens after SQL writes the row, (c) missing `filteringattributes` so the step fires on EVERY Update and you can't tell it apart, (d) plugin throwing silently — check the Plug-In Trace Log in the maker portal.

Each one is a 30-minute detour the first time. The setup guide makes the
second time take five minutes.

---

## Appendix — PRT is optional

> _Skip this unless you're rebuilding from scratch in CI or you want to
> understand exactly what the Plugin Registration Tool wrote during the
> on-camera demo. Part 1's main flow uses PRT because it's more
> discoverable on video._

The traditional advice (and the docs through May 2026) say the Plugin
Registration Tool is **required** to register a virtual-entity data provider,
because PRT creates "both the data provider and the data source entity in one
click — the Web API can't." That claim is wrong. Both rows can be written
directly via the Web API once you know exactly what PRT writes, and
[`scripts/python/register_ve_data_provider.py`](../../scripts/python/register_ve_data_provider.py)
does it.

**What PRT actually writes.** A before/after Web-API snapshot of the affected
tables (`pluginassemblies`, `plugintypes`, `entitydataproviders`,
`sdkmessageprocessingsteps`, and any new entity definitions) shows PRT creates
exactly **two rows** when you complete its Register New Data Provider dialog:

1. **A virtual-entity data SOURCE** — a regular virtual entity
   (`TableType=Virtual`) whose `DataProviderId` points at the OOB
   JsonConverter provider (id `b2112a7e-...`). It's a container for the
   provider's configuration rows. For this episode: `lc_githubdatasource`.
2. **An `entitydataproviders` row** — names the provider, points at the
   data source entity by **logical name** (not GUID), and has one
   `Uniqueidentifier` column per SDK message (`retrievemultipleplugin`,
   `retrieveplugin`, `createplugin`, `updateplugin`, ...). Implemented
   operations get the plugin-type GUIDs from step 3 above; every
   unimplemented operation gets the OOB "Not Implemented" plugintype id
   `c1919979-0021-4f11-a587-a8f904bdfdf9`.

PRT does **not** create `sdkmessageprocessingsteps` for VE data providers —
the message-to-plugin binding IS the entitydataprovider row's own columns.
This is different from "regular" plugins.

**Three Web-API gotchas the replication script handles**
(captured here because the docs don't mention any of them):

| Gotcha | What goes wrong | Fix |
|---|---|---|
| Data-source entity is a virtual entity | `POST /EntityDefinitions` 400s with `CanChangeTrackingBeEnabled can not be active for ... virtual Entity` | Include the full virtual-entity managed-property set (`ChangeTrackingEnabled: false`, `CanChangeTrackingBeEnabled: {Value: false, CanBeChanged: false}`, `IsAvailableOffline`, `IsVisibleInMobileClient`, `CanCreateCharts`). |
| Missing `ExternalCollectionName` | `400 You must specify a value for the External Collection Name property` | Set `ExternalName` AND `ExternalCollectionName` on the data-source entity. |
| `*plugin` columns are `Uniqueidentifier`, not lookups | `400 An ODataPrimitiveValue was instantiated with a value of type 'ODataEntityReferenceLink'` if you use `@odata.bind` | Send each `retrievemultipleplugin`, `retrieveplugin`, etc. as a **raw GUID string**, not as a `/plugintypes(<id>)` nav-link. Verified via `EntityDefinitions(LogicalName='entitydataprovider')/Attributes` — all 20 plugin columns are `AttributeType=Uniqueidentifier`. |

**Verify it on your own org from a clean slate** — to rule out "it only works
because PRT primed the env":

1. Run the canonical teardown script — it removes everything Ep 4 added (the
   `lc_githubissue` and `lc_githubdatasource` entity definitions, the
   `entitydataprovider` row, both plugintypes, and the pluginassembly).
   Destructive — only run against a dev/test environment.
2. Re-run [`scripts/register_ve_plugin.py`](../../scripts/register_ve_plugin.py)
   → fresh assembly + plugintypes via Web API.
3. Run [`scripts/python/register_ve_data_provider.py`](../../scripts/python/register_ve_data_provider.py)
   → fresh `entitydataprovider` + `lc_githubdatasource` via Web API. PRT is
   not opened at any point.
4. Re-run [`scripts/setup_virtual_entity.py`](../../scripts/setup_virtual_entity.py)
   → fresh `lc_githubissue` table.
5. Query `GET /lc_githubissues` → all six live GitHub issues come back.

Running that recipe against a working Ep 4 environment reproduces all six
rows end-to-end with PRT never opened. The on-camera path still uses PRT
(the GUI dialog is more discoverable for viewers who aren't comfortable in
Python), but the GUI is no longer a hard dependency.
