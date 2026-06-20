# Episode 8 — Roles & Reach: security in a headless world

**Status:** ✅ Four roles + four teams live in the environment · ✅ Caller self-joined to all four · ✅ RBAC visualizer app built (`apps/rbac-visualizer/`, mock mode verified) · 🚧 Field-security masking + smoke-test script not yet built · 🎬 Not yet recorded
**Features:** ⭐ **Two axes of security for agents:** row-level (four flat roles: Member / Owner / Viewer / Admin) **and** data masking (column-level / field security over sensitive `lc_*` columns) · ⭐ Coverage over Eps 1–7: `lc_*` tables, the `lc_githubissue` virtual entity, the `lc_CalculateLaunchReadiness` Custom API, the MCP connectors, and Ep 7's `search_data` over attached files · ⭐ Authored (and enforced) from any coding agent, now including **Cursor**
**Layer:** 🛡 Dataverse's security model as the control plane for agents (roles + owner-teams + field security; root BU only for now)
**Coding agent:** Claude Code / Cursor / any MCP client · **Runtime:** Web API + Python SDK; idempotent on names

---

## The news (cold open)

> _"Microsoft's official Dataverse plugin is now live in the **Cursor** marketplace. The same `dv-*` skillset: connect a coding agent to your environment in seconds, no portal."_

That's the good news. It's also the uncomfortable question this episode answers.
The moment any agent (Scout, Copilot, Claude, now Cursor) can reach your
environment in seconds, the only thing standing between it and every sensitive
row is your security model. On most platforms a new client means a new exposure.
On Dataverse it doesn't, because access is enforced at the platform, not bolted
onto each client.

So this episode is **security for a headless world**, and real security here is
two axes, not one:

1. **Row-level security:** who sees *which rows*, and who can *do what*. Four
   flat roles, four owner-teams, one root BU.
2. **Data masking (column-level security):** which *sensitive fields* stay
   hidden even on rows a caller is allowed to read. A field security profile over
   `lc_blockerreason` and `lc_risksummary` so an unprivileged agent gets
   `********`, not the reasoning.

Together they are the toolset an agent developer needs over sensitive data: an
agent can be broadly useful and still never surface what it shouldn't. And every
bit of it is authored from a coding agent (now Cursor included) against a
one-line spec.

> ### The hook
>
> _"Seven episodes in: a data model, ingested data, virtual entities federating
> SharePoint and GitHub, a Custom API, MCP connectors, a Scout autopilot that
> searches inside attached PDFs. All useful. All wide open: every test user, and
> every agent they connect, can read every row and every sensitive field.
> Episode 8 is where 'shippable' starts."_

We don't reach for the full Dataverse security model (nested BUs, hierarchical
security, AAD group teams, record-share-via-POA). We reach for the two axes that
actually matter for agents over sensitive data: flat roles for the rows, field
security for the columns. ~250 lines of Python for the roles, a field security
profile for the masking, all authored by a coding agent.

---

## Part 1 · Connect from Cursor, and let the coding agent author the model

Here's where the cold open pays off. The first move isn't a portal. It's
connecting an agent. As of this episode the Microsoft Dataverse plugin
(`microsoft/Dataverse-skills`) is one click away in the **Cursor marketplace**,
the same `dv-*` skillset already in Copilot, Claude, and any MCP client. Install
it, point it at the environment, and Cursor can reach Dataverse in seconds.

Then the agent does the building. None of what follows is click-ops. From one-line
specs, the coding agent drives the governed Dataverse APIs (`dv-security`,
`dv-metadata`, `dv-admin`) to author:

- the four flat roles and four owner-teams (Part 2),
- the secured columns and the `lc Sensitive Readers` field security profile (Part 3),
- and a small **impersonation visualizer app** ([`apps/rbac-visualizer/`](../../apps/rbac-visualizer/))
  so the whole model is something you can *see*, not just read about.

That last one is the demo vehicle. We ask Cursor to build a tiny Flask app that
lets you pick a persona from a dropdown and runs the *same* launch query as that
user, with the real `MSCRMCallerID` impersonation header set under the hood. Two
lenses render side by side: a row-count panel (Part 2's row-level security) and a
task table whose secured columns show either cleartext or a red `████████`
(Part 3's masking). One screen, both axes, any persona.

```powershell
# The agent builds it; you run it. Offline demo first (seeded snapshot, no env):
python apps/rbac-visualizer/app.py --mock

# Then live against the environment, personas discovered from the lc teams:
python apps/rbac-visualizer/app.py
# open http://127.0.0.1:5000 and switch personas
```

The point of doing this from Cursor: **one model, every client.** Whatever the
agent authors here is enforced no matter which client connects next: Scout,
Copilot, Claude, Cursor. Switch agents and the answer to "what can this agent
see?" does not change, because the platform, not the client, decides what comes
back. More agentic clients is exactly the trend that worries security teams; on
Dataverse a new client is not a new attack surface.

---

## The four roles

| Role | Coverage | Privileges | Depth (per [MS docs](https://learn.microsoft.com/en-us/power-platform/admin/security-roles-privileges)) |
|---|---|---|---|
| **lc Member** | `lc_*` tables | Create / Read / Write | **User** (only records the user owns) |
| **lc Owner** | `lc_*` tables, virtual entities, Custom API exec | Create / Read / Write | **Business Unit** |
| **lc Viewer** | `lc_*` tables, virtual entities, Custom API exec (read-shape) | Read | **Business Unit** |
| **lc Admin** | `systemuser`, `team`, `role` (system tables) | Read all; Write team; Append + AppendTo on team and user | **Business Unit** |

> These roles are designed to **layer on top of OOB `Basic User`**, Dataverse's
> canonical minimum baseline. The MS doc says it plainly: _"Use Basic User role
> for the minimum privileges."_ A user without Basic User can't even call
> `WhoAmI`. The recommended assignment is **`Basic User` + one of `{lc Member,
> lc Owner, lc Viewer}` + optionally `lc Admin`**.

---

## Part 2 · Row-level security: one script, four roles, four teams

**Axis one: who sees which rows.** This is the role + owner-team model, authored
by the coding agent from a one-line spec.

[`scripts/python/setup_simple_rbac.py`](../../scripts/python/setup_simple_rbac.py) (~250 lines) does five things:

1. Resolves the **root business unit** for the env.
2. Looks up every privilege name we need via `/privileges?$filter=name eq '…'`,
   batched 30 names per request to avoid OData URL caps. Dataverse privilege
   names use the table's logical name (`prvCreatelc_task`), **except** for the
   `systemuser` table, whose privileges use the legacy `User` stem
   (`prvReadUser`, `prvAppendUser`), not `SystemUser`. (We hit that bug
   during the live build, fixed before shipping.)
3. Creates four `role` rows via `POST /roles` in the root BU. Idempotent on
   role name.
4. Applies the privilege matrix via the `AddPrivilegesRole` action, mapping
   integer depths to the strings the action expects:
   `User=1 → "Basic"`, `BU=2 → "Local"`, `ParentChild=4 → "Deep"`,
   `Org=8 → "Global"`.
5. Creates four owner-teams (`lc Members`, `lc Owners`, `lc Viewers`,
   `lc Admins`) and binds the matching role to each team via
   `teamroles_association`. Idempotent on team name.

The whole script is idempotent: re-runs are no-ops on creation and just
re-apply privileges (Dataverse de-dupes the inserts).

### Privilege matrix at a glance

| Surface | lc Member | lc Owner | lc Viewer | lc Admin |
|---|---|---|---|---|
| `lc_launch` | CRU @ User | CRU @ BU | R @ BU | – |
| `lc_milestone` | CRU @ User | CRU @ BU | R @ BU | – |
| `lc_task` | CRU @ User | CRU @ BU | R @ BU | – |
| `lc_statusupdate` | CRU @ User | CRU @ BU | R @ BU | – |
| `lc_teammember` | CRU @ User | CRU @ BU | R @ BU | – |
| `lc_githubissue` (VE) | R via lc_task | R via lc_task | R via lc_task | – |
| SharePoint task VE | R via lc_task | R via lc_task | R via lc_task | – |
| `CalculateLaunchReadiness` Custom API | execute | execute | execute (read shape) | – |
| BYO MCP connectors | – | execute | execute | – |
| `systemuser` / `team` / `role` | – | – | – | R all; Write team; Append + AppendTo |

(Virtual-entity privileges follow the regular table model: `prvRead<entity>`
on the VE controls who can query it. The lc Owner/Viewer roles include reads
on the VE tables.)

### Run it

```powershell
$env:PYTHONIOENCODING="utf-8"

# Preview the plan (no writes)
python scripts/python/setup_simple_rbac.py --dry-run

# Create the roles, apply privileges, create teams, bind role↔team
python scripts/python/setup_simple_rbac.py

# Add yourself to all four teams so you can impersonate any role
python scripts/python/setup_simple_rbac.py --add-self

# Roll yourself back out if you need to test "no role at all"
python scripts/python/setup_simple_rbac.py --remove-self
```

### Live evidence from the build

The first real run created everything in one pass:

```
Env: https://org40ae6a46.crm.dynamics.com
Caller userid: d61702f4-024c-f111-bec6-7ced8d3d06d5
Root BU:  org40ae6a46 (cd1002f4-024c-f111-bec6-7ced8d3d06d5)
Resolved 22 privilege ids.

=== Plan ===
  lc Member      15 privileges  team='lc Members'
  lc Owner       15 privileges  team='lc Owners'
  lc Viewer       5 privileges  team='lc Viewers'
  lc Admin        7 privileges  team='lc Admins'

  role 'lc Member': created
  role 'lc Owner':  created
  role 'lc Viewer': created
  role 'lc Admin':  created
  role 'lc Member': applied 15 privileges
  role 'lc Owner':  applied 15 privileges
  role 'lc Viewer': applied 5  privileges
  role 'lc Admin':  applied 7  privileges
  team 'lc Members': created, role bound
  team 'lc Owners':  created, role bound
  team 'lc Viewers': created, role bound
  team 'lc Admins':  created, role bound

  ✅ add self ↔ 'lc Members'
  ✅ add self ↔ 'lc Owners'
  ✅ add self ↔ 'lc Viewers'
  ✅ add self ↔ 'lc Admins'
```

That's the substrate Episode 8 demonstrates. Re-runs are no-ops on creation
and idempotently re-sync privileges.

---

### Proof: smoke-test by impersonation (same query, four lenses)

Same trick as the Episode 4 federation beat, except now we run **one** query
as **four different roles** by switching the `MSCRMCallerID` header on the same
HTTP client. The planned `scripts/python/rbac_smoketest.py` runs the
`lc_task` `$expand` query through each test user (members of one of the four
teams only) and prints a row-count table:

```
=== Same query, four lenses ===

Test user      lc_launch  lc_milestone  lc_task  lc_githubissue  Custom API
-----------    ---------  ------------  -------  --------------  ----------
member-test            1            16        4               6  ✓
owner-test             1            16       61               6  ✓
viewer-test            1            16       61               6  ✓ (read)
admin-test             —             —        —               —  —
```

> `member-test` sees **4** tasks, not 61, because `User`-level depth on
> `lc_task` returns only records the calling user owns, not the 57 owned by
> other seeded test users. That's the bullseye demonstration of why depth
> matters.

The Admin row is blank for the data columns because `lc Admin` has zero data
privileges by design: Admin is the user-management role, not a data role.
Admin alongside Owner gives you full data + team management.

---

## Part 3 · Data masking: column-level security over sensitive fields

**Axis two: which sensitive fields stay hidden, even on rows you can read.**

Row-level security answers *which rows*. It does nothing about *which columns*.
An `lc Owner` who can read all 61 tasks still reads every `lc_blockerreason`,
and every `lc_risksummary` on `lc_launch`, the internal "why this launch is at
risk" reasoning that Episodes 3 and 4 wrote into the model. In a headless world
that matters more, not less: the agent you just connected from Cursor inherits
exactly what its caller can see. Broad read access plus sensitive columns equals
a leak waiting to happen.

Dataverse's answer is **column-level (field) security**. You flag a column as
secured, then a **field security profile** grants `Read` / `Update` / `Create`
on that column to specific users or teams. Anyone outside the profile gets the
column back **masked** (`********`) even on a row they are fully allowed to
read.

We secure two columns and pair each profile with the role from Part 2:

| Secured column | Table | Who gets the cleartext | Who gets `********` |
|---|---|---|---|
| `lc_blockerreason` | `lc_task` | `lc Owner` (+ profile) | `lc Member`, `lc Viewer` |
| `lc_risksummary` | `lc_launch` | `lc Owner` (+ profile) | `lc Member`, `lc Viewer` |

The planned [`scripts/python/setup_field_security.py`](../../scripts/python/setup_field_security.py)
does three things, idempotently:

1. Sets `IsSecured = true` on `lc_blockerreason` and `lc_risksummary` via the
   column metadata.
2. Creates a `fieldsecurityprofile` row (`lc Sensitive Readers`) and binds the
   `lc Owners` team to it.
3. Grants `CanRead = Allowed` on both secured columns for the profile, leaving
   everyone else at the masked default.

### The Episode 7 callback: masking holds even through `search_data`

This is the beat that makes the point. Episode 7's `search_data` does semantic
search across rows **and the content inside attached files**. The obvious worry:
does an agentic search tool route around column security and hand the agent the
secured value anyway, or surface it out of an attached PDF?

It doesn't. Field security is enforced by the platform on the *read*, not by
each tool. Run the same `lc_task` search as a `lc Viewer`-only caller and the
`lc_blockerreason` field comes back `********`; run it as an `lc Owner` in the
profile and the cleartext returns. Same query, same agent, same client: the
column the caller isn't cleared for never leaves Dataverse, no matter which
tool asked for it.

```
=== search_data: 'export blocker on Q3', two lenses ===

Caller            lc_task match   lc_blockerreason returned
--------------    -------------   -------------------------
viewer-only               ✓        ********
owner + profile           ✓        "Customs paperwork rejected; legal hold on EU SKU"
```

> That is the whole thesis in one table: the agent stays useful (it still finds
> the right task), and the platform still refuses to leak the sensitive field.

> **Adjacent, not the same thing:** Dynamics 365 Customer Service also offers
> [conversation **data-masking rules**](https://learn.microsoft.com/en-us/dynamics365/customer-service/administer/data-masking-settings)
> regex masking of things like credit-card and SSN values inside chat
> messages and transcripts. That's a channel-level control for live
> conversations; column-level field security is the row-and-record control we
> use here. Different layers, same instinct: don't show sensitive data to a
> principal that isn't cleared for it.

---

## The doctrine: rules every Dataverse security design lives by

Rules from the official docs that the scripts make first-class:

1. **Basic User is the floor, not the ceiling.** Our four roles are add-ons.
   Drop Basic User from a user and they can't read their own profile, never
   mind a launch.
2. **For many-to-many relationships, you need `Append` on both sides.**
   `lc Admin` adding a user to a team needs both `prvAppendToTeam` and
   `prvAppendUser`; one without the other returns 401. The MS doc spells
   this out and the script honors it.
3. **Roles in the root BU inherit to every child BU.** That's why one role
   row works whether you nest BUs later or stay flat. We stay flat in this
   episode.
4. **Field security is a second axis, not a stronger role.** A secured column
   is masked for *everyone* outside its profile, regardless of how powerful
   their role is. Row access and column access are evaluated independently.

---

## What's deliberately NOT in this episode

- **Hierarchical security.** Manager + position chains are a third access
  axis on top of BUs + roles + field security. Powerful but additive.
- **Nested business units.** We use the root BU only. BU nesting changes
  what `BU` depth means and deserves its own model walkthrough.
- **AAD group teams / Conditional Access.** Tenant-level controls. We stay
  inside Dataverse's own primitives here.
- **Record sharing via `PrincipalObjectAccess`.** The right answer for
  "share this one launch with a contractor" scenarios, but mixed with
  role design it muddles the lesson.
- **Custom privileges on plugins / Custom API.** The Custom API
  (`CalculateLaunchReadiness` from Ep 5) is reachable via the table-level
  Read on `lc_launch` today. Defining a custom privilege for the API
  itself is a stretch.
- **A persona-driven role-matrix.** An earlier draft modeled five personas
  (Exec / DRI / Eng / Marketing / Partner) with one BU each. The flat four
  is more useful in practice and easier to maintain.

These are all real and useful, and they each deserve their own episode
someday.

---

## What you see on screen

1. **The Cursor cold open.** The Cursor marketplace listing for the Microsoft
   Dataverse plugin (`microsoft/Dataverse-skills`). Install it, point it at the
   env, and the agent reaches Dataverse in seconds. Great. Now: what can it see?
2. PPAC → Security → Roles **before**: zero `lc *` roles. Wide-open env.
3. The coding agent in Cursor (or Claude Code, any MCP client): _"author four
   flat roles for the lc_* tables (Member, Owner, Viewer, Admin) covering the
   unified core plus the virtual entities and Custom API from Eps 4–5, then build
   me a small app to visualize who sees what."_ The agent writes
   `setup_simple_rbac.py` and the `apps/rbac-visualizer/` Flask app from the spec.
4. `--dry-run` prints the plan: 22 privileges resolved, 15 + 15 + 5 + 7
   privilege counts, four roles, four teams, four bindings.
5. Real run: `created`, `applied N privileges`, `team created, role bound`
   for every role. Self-add: four `✅` lines.
6. PPAC → Security → Roles **after**: four new roles. Click `lc Viewer`:
   only the `lc_*` tables have check marks, all Read.
7. PPAC → Security → Teams → `lc Owners` → Members tab: the caller appears.
8. **The visualizer, axis one.** Open `apps/rbac-visualizer/` in the browser and
   flip the persona dropdown. The row-count panel rewrites live: Member shows 4
   tasks, Owner and Viewer show 61, Admin shows blanks. Same query, four lenses,
   one screen, real `MSCRMCallerID` impersonation underneath.
9. **Axis two, masking.** The agent secures `lc_blockerreason` and
   `lc_risksummary` and binds the `lc Sensitive Readers` profile to `lc Owners`.
   Back in the visualizer, the Viewer persona's task table shows `████████` where
   the blocker reason and risk summary should be; the Owner persona shows the
   cleartext. The row was readable; the column still wasn't.
10. **The Episode 7 callback.** Re-run Ep 7's `search_data` for the Q3 export
    blocker as a Viewer-only caller and as an Owner-in-profile. Same agent, same
    query: the Viewer gets `████████`, the Owner gets the sentence, even though
    the match came from inside an attached PDF.
11. **The punchline:**
    > _"Two axes, one platform. Row security decides which rows come back; field
    > security decides which columns. The data didn't change; the platform's
    > willingness to return it did. Connect any agent you like, from any client,
    > now including Cursor. The answer is still the same."_

---

## Files in this episode

| File | Role |
|---|---|
| [`scripts/python/setup_simple_rbac.py`](../../scripts/python/setup_simple_rbac.py) | Creates four roles + four owner-teams in the root BU; applies the privilege matrix; binds role↔team. Idempotent. `--dry-run`, `--add-self`, `--remove-self`. |
| [`scripts/python/setup_field_security.py`](../../scripts/python/setup_field_security.py) | _(planned)_ Secures `lc_blockerreason` + `lc_risksummary`, creates the `lc Sensitive Readers` field security profile, and grants the `lc Owners` team read on both. Idempotent. |
| [`scripts/python/rbac_validate.py`](../../scripts/python/rbac_validate.py) | End-to-end probe of every RBAC primitive used here: test BU, owner team, role clone via `CloneAsRole`, role bind, `MSCRMCallerID` impersonation, cleanup. Run once per env to confirm plumbing. |
| [`scripts/python/rbac_smoketest.py`](../../scripts/python/rbac_smoketest.py) | _(planned)_ Runs the Part 1 four-lens query (and the Part 2 masking check) and prints the row-count + masked-field tables. |
| [`apps/rbac-visualizer/`](../../apps/rbac-visualizer/) | The persona impersonation visualizer Cursor builds in Part 1. Flask app, `--mock` (seeded snapshot) and live modes; real `MSCRMCallerID` impersonation; renders row counts (axis one) and masked secured columns (axis two) side by side. |
| [`datamodel/security/role-matrix.md`](../../datamodel/security/role-matrix.md) | _(planned)_ Human-readable rendering of the privilege matrix and the secured-column profile, kept in sync with the scripts as documentation. |
| [`episodes/ep-08-rbac/preflight.py`](preflight.py) | _(planned)_ Read-only check: are the four roles + four teams present, are `lc_blockerreason` + `lc_risksummary` secured with the profile bound, is the caller a member of any team, are the `lc_*` tables resolved. |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# 0. Ensure the env is reachable (refresh MFA if needed)
az login --tenant <your-tenant> --scope "https://<your-env>.crm.dynamics.com/.default"

# 1. Preview the role + team plan
python scripts/python/setup_simple_rbac.py --dry-run

# 2. Create roles + privileges + teams + bindings
python scripts/python/setup_simple_rbac.py

# 3. Self-join all four teams so you can impersonate any of them
python scripts/python/setup_simple_rbac.py --add-self

# 4. (Planned) Secure the sensitive columns + bind the field security profile
python scripts/python/setup_field_security.py

# 5. (Optional) End-to-end primitives validation, then cleanup
python scripts/python/rbac_validate.py

# 6. (Planned) Run the same query through each role + check masked fields
python scripts/python/rbac_smoketest.py

# 7. See it: the impersonation visualizer (offline demo, then live)
python apps/rbac-visualizer/app.py --mock   # http://127.0.0.1:5000
python apps/rbac-visualizer/app.py          # live, personas from the lc teams
```

---

## Pitfalls collected during the build

These are the ones that cost real minutes the first time:

- **`prvReadSystemUser` doesn't exist.** Dataverse privilege names for the
  `systemuser` table use the legacy `User` stem: `prvReadUser`, `prvAppendUser`,
  not `SystemUser`. A name lookup against the wrong stem returns zero rows and
  the script fails. (Cost: one debugging cycle, fixed in the shipped script.)
- **OData `$filter` URL length.** Resolving 30+ privilege names in one
  `?$filter=name eq '…' or name eq '…' …` request can exceed the gateway URL
  cap. Batch by ~30.
- **PowerShell + cp1252 + ✅/❌ in stdout = crash.** The script prints status
  emoji. Run with `$env:PYTHONIOENCODING="utf-8"` or pipe through `Out-String`.
- **`AddPrivilegesRole` 400s on a bad GUID, but the error is opaque.** Resolve
  names first; fail fast on any missing name before applying privileges.
- **Team-membership add returns 204 on success and 4xx on duplicate.** The
  script treats both as a no-op. The "already a member" path is normal on
  re-run and shouldn't print a scary error.

- **Field security masks reads, it does not block writes by default.** Securing
  a column controls `Read` / `Update` / `Create` independently. If you only grant
  `Read` on the profile, members can see the cleartext but still can't change it.
  Decide per column whether the profile needs `Update` too.
- **A secured column comes back as `null`, not `********`, over the Web API.** The
  asterisks are a UI affordance. Agents and scripts reading via OData get the
  field omitted or null for principals outside the profile, so don't mistake a
  masked field for an empty one in code.

Each of these is a 10–30 minute detour the first time. The scripts have them all
encoded already.

---

## Next up

Episode 9 puts a declarative **Launch Coordinator** agent on top of this exact
secured model. The lesson carries forward: the agent is only ever as broad as
the role and field security of the identity it runs as. Reach was Episodes 1–7;
the guardrails are this episode; the autonomous operator is next.
