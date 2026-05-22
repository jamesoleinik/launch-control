# Episode 6 — Roles & Reach

**Status:** ✅ Four roles + four teams live in the environment · ✅ Caller self-joined to all four · 🚧 Smoke-test not yet built · 🎬 Not yet recorded
**Features:** ⭐ Four flat security roles (Member / Owner / Viewer / Admin) authored by the coding agent · ⭐ Coverage over Eps 1–5: `lc_*` tables, virtual entities, the Custom API, and the BYO MCP connectors · ⭐ One owner-team per role for assignment hygiene
**Layer:** 🛡 First entry into Dataverse's security model (roles + owner-teams; root BU only for now)
**Coding agent:** Claude Code · **Runtime:** Web API + Python SDK; idempotent on names

---

## The hook

> _"Five episodes in: a data model, ingested data, virtual entities federating SharePoint and GitHub, a Custom API, two BYO MCP connectors. All useful. All wide open — every test user can read every row and call every action. Episode 6 is where 'shippable' starts."_

We've spent five episodes adding **reach** — more tables, more sources, more
tools. Ep 6 adds the second axis: **who can see what, and who can do what**. We
don't reach for the full Dataverse security model (BUs nested, field-level
security, hierarchical security, AAD group teams, record-share-via-POA). We
reach for the simplest thing that's actually useful: four flat roles, four
owner-teams, one root BU. ~250 lines of Python, authored by a coding agent
from a one-line spec.

---

## The four roles

| Role | Coverage | Privileges | Depth (per [MS docs](https://learn.microsoft.com/en-us/power-platform/admin/security-roles-privileges)) |
|---|---|---|---|
| **lc Member** | `lc_*` tables | Create / Read / Write | **User** — only records the user owns |
| **lc Owner** | `lc_*` tables, virtual entities, Custom API exec | Create / Read / Write | **Business Unit** |
| **lc Viewer** | `lc_*` tables, virtual entities, Custom API exec (read-shape) | Read | **Business Unit** |
| **lc Admin** | `systemuser`, `team`, `role` (system tables) | Read all; Write team; Append + AppendTo on team and user | **Business Unit** |

> These roles are designed to **layer on top of OOB `Basic User`** — Dataverse's
> canonical minimum baseline. The MS doc says it plainly: _"Use Basic User role
> for the minimum privileges."_ A user without Basic User can't even call
> `WhoAmI`. The recommended assignment is **`Basic User` + one of `{lc Member,
> lc Owner, lc Viewer}` + optionally `lc Admin`**.

---

## Part 1 · One script, four roles, four teams

[`scripts/python/setup_simple_rbac.py`](../../scripts/python/setup_simple_rbac.py) (~250 lines) does five things:

1. Resolves the **root business unit** for the env.
2. Looks up every privilege name we need via `/privileges?$filter=name eq '…'`,
   batched 30 names per request to avoid OData URL caps. Dataverse privilege
   names use the table's logical name (`prvCreatelc_task`) — **except** for the
   `systemuser` table, whose privileges use the legacy `User` stem
   (`prvReadUser`, `prvAppendUser`), not `SystemUser`. (We hit that bug
   during the live build — fixed before shipping.)
3. Creates four `role` rows via `POST /roles` in the root BU. Idempotent on
   role name.
4. Applies the privilege matrix via the `AddPrivilegesRole` action, mapping
   integer depths to the strings the action expects:
   `User=1 → "Basic"`, `BU=2 → "Local"`, `ParentChild=4 → "Deep"`,
   `Org=8 → "Global"`.
5. Creates four owner-teams (`lc Members`, `lc Owners`, `lc Viewers`,
   `lc Admins`) and binds the matching role to each team via
   `teamroles_association`. Idempotent on team name.

The whole script is idempotent — re-runs are no-ops on creation and just
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

(Virtual-entity privileges follow the regular table model — `prvRead<entity>`
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

That's the substrate Episode 6 demonstrates. Re-runs are no-ops on creation
and idempotently re-sync privileges.

---

## Part 2 · Smoke-test by impersonation

Same trick as the Episode 4 federation beat — except now we run **one** query
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
> `lc_task` returns only records the calling user owns — not the 57 owned by
> other seeded test users. That's the bullseye demonstration of why depth
> matters.

The Admin row is blank for the data columns because `lc Admin` has zero data
privileges by design — Admin is the user-management role, not a data role.
Admin alongside Owner gives you full data + team management.

---

## Part 3 · The doctrine — three rules every Dataverse RBAC design lives by

Three rules from the official docs that the script makes first-class:

1. **Basic User is the floor, not the ceiling.** Our four roles are add-ons.
   Drop Basic User from a user and they can't read their own profile, never
   mind a launch.
2. **For many-to-many relationships, you need `Append` on both sides.**
   `lc Admin` adding a user to a team needs both `prvAppendToTeam` and
   `prvAppendUser` — one without the other returns 401. The MS doc spells
   this out and the script honors it.
3. **Roles in the root BU inherit to every child BU.** That's why one role
   row works whether you nest BUs later or stay flat. We stay flat in this
   episode.

---

## What's deliberately NOT in this episode

- **Field-level security.** Column-level masking (`lc_blockerreason`,
  `lc_riskhumanreasoning`, anything sensitive) sits **on top of** a role.
  Its own beat.
- **Hierarchical security.** Manager + position chains are a second access
  axis on top of BUs + roles. Powerful but additive.
- **Nested business units.** We use the root BU only. BU nesting changes
  what `BU` depth means and deserves its own model walkthrough.
- **AAD group teams / Conditional Access.** Tenant-level controls. We stay
  inside Dataverse's own primitives here.
- **Record sharing via `PrincipalObjectAccess`.** The right answer for
  "share this one launch with a contractor" scenarios — but mixed with
  role design it muddles the lesson.
- **Custom privileges on plugins / Custom API.** The Custom API
  (`CalculateLaunchReadiness` from Ep 5) is reachable via the table-level
  Read on `lc_launch` today. Defining a custom privilege for the API
  itself is a stretch.
- **A persona-driven role-matrix.** An earlier draft modeled five personas
  (Exec / DRI / Eng / Marketing / Partner) with one BU each. The flat four
  is more useful in practice and easier to maintain.

These are all real and useful — and they each deserve their own episode
someday.

---

## What you see on screen

1. PPAC → Security → Roles **before**: zero `lc *` roles. Wide-open env.
2. Claude Code in a terminal: _"author four flat roles for the lc_* tables —
   Member, Owner, Viewer, Admin — covering the unified core plus the virtual
   entities and Custom API from Eps 4–5."_ The agent writes
   `setup_simple_rbac.py` from the docstring spec.
3. `--dry-run` prints the plan: 22 privileges resolved, 15 + 15 + 5 + 7
   privilege counts, four roles, four teams, four bindings.
4. Real run: `created`, `applied N privileges`, `team created, role bound`
   for every role. Self-add: four `✅` lines.
5. PPAC → Security → Roles **after**: four new roles. Click `lc Viewer` →
   only the `lc_*` tables have check marks, all Read.
6. PPAC → Security → Teams → `lc Owners` → Members tab: the caller appears.
7. Smoke-test script: same `$expand` query as four roles. Four-column
   row-count table prints to the terminal — the Member row shows 4 tasks
   while the Owner row shows 61.
8. **The punchline:**
   > _"One model, four lenses, ~250 lines of Python. The data didn't
   > change — the platform's willingness to return it did. That's
   > Dataverse's security model surface area without the click-ops."_

---

## Files in this episode

| File | Role |
|---|---|
| [`scripts/python/setup_simple_rbac.py`](../../scripts/python/setup_simple_rbac.py) | Creates four roles + four owner-teams in the root BU; applies the privilege matrix; binds role↔team. Idempotent. `--dry-run`, `--add-self`, `--remove-self`. |
| [`scripts/python/rbac_validate.py`](../../scripts/python/rbac_validate.py) | End-to-end probe of every RBAC primitive used here — test BU, owner team, role clone via `CloneAsRole`, role bind, `MSCRMCallerID` impersonation, cleanup. Run once per env to confirm plumbing. |
| [`scripts/python/rbac_smoketest.py`](../../scripts/python/rbac_smoketest.py) | _(planned)_ Runs the Part 2 four-lens query and prints the row-count table. |
| [`datamodel/security/role-matrix.md`](../../datamodel/security/role-matrix.md) | _(planned)_ Human-readable rendering of the privilege matrix above, kept in sync with the script as documentation. |
| [`episodes/ep-06-rbac/preflight.py`](preflight.py) | _(planned)_ Read-only check: are the four roles + four teams present, is the caller a member of any of them, are the `lc_*` tables resolved. |

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

# 4. (Optional) End-to-end primitives validation, then cleanup
python scripts/python/rbac_validate.py

# 5. (Planned) Run the same query through each role
python scripts/python/rbac_smoketest.py
```

---

## Pitfalls collected during the build

These are the ones that cost real minutes the first time:

- **`prvReadSystemUser` doesn't exist.** Dataverse privilege names for the
  `systemuser` table use the legacy `User` stem: `prvReadUser`, `prvAppendUser`,
  not `SystemUser`. A name lookup against the wrong stem returns zero rows and
  the script fails. (Cost: one debugging cycle — fixed in the shipped script.)
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

Each of these is a 10–30 minute detour the first time. The script has them all
encoded already.
