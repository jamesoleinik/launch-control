---
name: ep-08-dataverse-security
description: |
  Teaches the Dataverse security model (the two axes: row-level security via
  roles + owner-teams + business-unit depth, and column-level security via
  field security profiles) and drives an agent to build a small, testable
  slice of it against a Dataverse environment. Use when the user asks to
  "explain the Dataverse security model", "do Episode 8", "create two roles
  to test row-level security", "add a data masking role", "secure a column",
  or "set up a field security profile".

  Two tasks, run in order:
  (1) Row-level: create two roles (one broad reader, one narrow owner) bound
      to teams, so the same query returns different row counts per persona.
  (2) Column-level: secure the sensitive columns and a field security profile
      so the same row returns cleartext for one role and a mask for the other.
license: MIT
metadata:
  author: Launch Control
  version: "1.1"
---

# Skill: Dataverse security model (row-level + data masking)

This skill explains how security works in Dataverse and then asks the agent to
build a small, testable slice of it. It is the knowledge layer behind Episode 8,
so the prompts that use it can stay one line long: the *how* lives here, the
*ask* lives in the README.

The whole point: connect any agent you like (Copilot, Claude, Cursor) to a
Dataverse environment, and what it can read is decided by the platform, not the
client. This skill makes that boundary something you can author and test.

## The model in one screen

Dataverse enforces access on two independent axes. A request has to clear both.

1. **Row-level security: which rows come back.**
   Access is granted to a **security role**, the role is bound to an **owner
   team**, and a user becomes a member of the team. A role grants **privileges**
   (Create / Read / Write / Delete / Append / AppendTo / Assign / Share) on each
   table, and every privilege carries a **depth** that decides *how many* rows it
   reaches:

   | Depth | Reaches | Action string |
   |---|---|---|
   | **User** | only rows the user owns | `Basic` |
   | **Business Unit** | every row in the user's BU | `Local` |
   | **Parent: Child BU** | the BU and its children | `Deep` |
   | **Organization** | every row, every BU | `Global` |

   The same `Read` privilege at User depth versus BU depth is the entire
   difference between "I see my 4 tasks" and "I see all 61".

2. **Column-level security (data masking): which fields come back.**
   Row access says nothing about sensitive *columns*. Microsoft calls this
   **column-level security** (the API still uses the older "field security"
   names). You flag a column as **secured** (`IsSecured = true`), then a
   **column security profile** (`fieldsecurityprofile`) grants permissions on
   that column to specific users or teams. The profile exposes four permissions:

   | Permission | Stored column | Effect |
   |---|---|---|
   | **Read** | `canread` | Can view the column. With a masking rule applied, a plain read returns the *masked* value. |
   | **Read unmasked** | `canreadunmasked` | Can pull the cleartext behind a masking rule, and only when the request opts in (see below). Values: `0` Not allowed, `1` One record, `3` All records. |
   | **Update** | `canupdate` | Can change the column value. |
   | **Create** | `cancreate` | Can set the column value on insert. |

   Over the Web API the states are distinct, and were verified live against
   `lc_task`:

   - **Outside the profile** (no Read): the column comes back **null / omitted**.
     It is withheld, not masked. Treat absent as no-access in code.
   - **In the profile with Read, no masking rule:** cleartext.
   - **In the profile with Read + a masking rule:** a plain `GET` returns the
     *masked* value (e.g. `###-##-6789`). The cleartext comes back **only** when the
     caller adds the **`?UnMaskedData=true`** query parameter *and* holds **Read
     unmasked**. Without the parameter the value is never unmasked, whatever the
     permission.

   A masking rule is a regular expression plus a mask character on a **Text or
   Number** column and requires a **Managed Environment**. With no masking rule a
   secured column is all-or-nothing (full value for the profile, omitted for
   everyone else); a masking rule adds the partial-reveal middle state.

   Column security is **organization-wide** and applies to every data access
   request. Configuring it requires the **System Administrator** role.

These axes are evaluated **independently**. Field security is not a stronger
role; a secured column is governed by its profile no matter how powerful the
caller's role is.

> **Critical for testing, verified live: a masking rule masks a plain read for
> *everyone*, System Administrators included.** A sysadmin reading a masked column
> with a plain `GET` still gets `###-##-6789`; the cleartext returns only when the
> request adds `?UnMaskedData=true` (the platform always honors that for a sysadmin,
> and for a non-admin only if their profile grants Read unmasked). What sysadmins
> *do* bypass is classic column **access**: on a secured column with **no** masking
> rule a sysadmin always reads cleartext, while a principal outside the profile gets
> the column omitted. So test the two cases differently: prove full-hide with a
> **non-admin** (they get null), and prove partial masking by comparing a plain `GET`
> (masked) against `?UnMaskedData=true` (cleartext only for the unmasked-cleared).

References: [Column-level security](https://learn.microsoft.com/en-us/power-platform/admin/field-level-security)
· [Masking rules](https://learn.microsoft.com/en-us/power-platform/admin/create-manage-masking-rules).

## Rules the docs make you live by

- **Basic User is the floor, not the ceiling.** Custom roles layer on top of the
  out-of-box `Basic User` role. Without it a user cannot even call `WhoAmI`.
- **Roles in the root BU inherit to child BUs.** One role row works whether you
  stay flat or nest BUs later.
- **`Append` is needed on both sides of a many-to-many.** Adding a user to a team
  needs `prvAppendToTeam` *and* `prvAppendUser`; one without the other is a 401.
- **`systemuser` privileges use the legacy `User` stem.** It is `prvReadUser`,
  `prvAppendUser`, not `prvReadSystemUser`. A lookup against the wrong stem
  returns zero rows.
- **Resolve privilege names, then apply.** Look names up via
  `/privileges?$filter=name eq '…'`, batched ~30 per request to dodge the OData
  URL length cap, then apply with the `AddPrivilegesRole` action.
- **Field security masks reads; it does not block writes by default.** Granting
  only `Read` on the profile lets members see cleartext but not change it; add
  `Update` / `Create` if the profile also needs to write.
- **Not every column can be secured.** Securable columns exclude virtual-table
  columns, lookup columns, formula/calculated columns, primary-name columns, and
  system columns (`createdon`, `modifiedon`, `statecode`, `statuscode`). The
  eligibility flags are `CanBeSecuredForRead/Update/Create`. (So `lc_githubissue`,
  a virtual entity, cannot be secured at the column level: govern it at the row
  level instead.)
- **Secure the calculated twin too.** If a calculated or composite column reads a
  secured column, secure that calculated/composite column as well, or the value
  leaks through it.
- **Agents are users; secure them per agent.** A connection authenticates as a real
  `systemuser`, a human or an **application user** (e.g. the Cowork app user
  `LaunchControl-Cowork-MCP-agent365`, which has `applicationid` set). Field security binds to
  the agent's identity too, so assign profiles to application users for least
  privilege. Effective column access is the **intersection** of the human's profile
  and the agent's profile: the value returns only when both clear it.

## This environment

- Tables: the `lc_*` model (`lc_launch`, `lc_milestone`, `lc_task`,
  `lc_statusupdate`, `lc_teammember`, plus the `lc_githubissue` virtual entity).
- Secured columns are live in this environment now, shipped in the `LaunchControl`
  solution:
  - **`lc_task.lc_blockerreason`** (`IsSecured = true`), no masking rule, governed
    by the **`lc Sensitive Readers`** column security profile: in-profile principals
    read cleartext, everyone else gets the column omitted.
  - **`lc_launch.lc_risksummary`** (`IsSecured = true`), masked by the custom
    **`lc_RiskSummaryMask`** rule: mask character `#` plus the regex `(?<=:.*).`,
    which collapses everything after the first colon so only the leading severity
    word (e.g. `High:`) survives a plain read.
- Auth + base URL come from `.env` (`DATAVERSE_URL`); reuse `scripts/auth.py` for
  the token. API base is `${DATAVERSE_URL}/api/data/v9.2`.

## Hard rules

1. **Confirm the environment first.** Print `DATAVERSE_URL` from `.env` and have
   the user confirm before any write. This skill makes real changes (roles,
   teams, secured columns, profiles).
2. **Idempotent by name.** Re-runs must be no-ops on creation and safely re-sync
   privileges. Never create a duplicate role/team/profile on a second run.
3. **One task at a time.** Run Task 1, test it in the local app, then Task 2.
4. **Python only**, consistent with the other episodes; reuse `scripts/auth.py`.

---

## Task 1: Two roles to test row-level security

Goal: two roles that make the row-level axis visible by returning *different*
row counts for the same query.

- **`lc Owner`**: `Read` (plus Create/Write) on every `lc_*` table at
  **Business Unit** depth. Sees every row in the BU.
- **`lc Member`**: `Read` (plus Create/Write) on every `lc_*` table at **User**
  depth. Sees only the rows it owns.

Create an owner team per role (`lc Owners`, `lc Members`) and bind the matching
role to each via `teamroles_association`. Resolve the privilege names first,
apply with `AddPrivilegesRole`, and make the whole thing idempotent with
`--dry-run`, `--add-self`, and `--remove-self` so the author can join either
team and impersonate it.

**Test:** run the visualizer (`apps/rbac-visualizer/`) and flip between the two
personas. `lc Owner` returns all 12 tasks; `lc Member` returns only the 4 it
owns. Same query, two lenses.

## Task 2: A data masking role to test column-level security

Goal: a profile that makes the column-level axis visible by returning the *same
row* with a sensitive field readable for one role and masked for the other.

This environment already ships the worked example, in the `LaunchControl` solution:

- **`lc_task.lc_blockerreason`** is secured (`IsSecured = true`) with no masking
  rule. The **`lc Sensitive Readers`** profile grants `Read = Allowed` on it, so
  in-profile principals read the cleartext blocker and everyone else (non-admin,
  out of profile) gets the column omitted.
- **`lc_launch.lc_risksummary`** is secured and carries the custom
  **`lc_RiskSummaryMask`** rule (mask character `#`, regex `(?<=:.*).`, revealing
  only the leading severity word before the first colon). The profile grants
  `Read = Allowed` + `Read unmasked = All records`, so members see the mask on a
  plain read and cleartext on an `?UnMaskedData=true` read.

To build a slice from scratch the moves are the same: secure the column
(`IsSecured = true`), create a **column security profile** (`fieldsecurityprofile`),
grant the profile `Read = Allowed` on the column, and bind the cleared team to it.
Attach a **masking rule** (a regex + mask character on a Text/Number column, gated by
the **Read unmasked** permission and a Managed Environment) when you want a *partial*
reveal like `###-##-6789` instead of a full hide. Make the whole thing idempotent on
the profile name.

> **Gotcha, live in this environment: a secured column with no profile members is
> readable only by System Administrators.** When the `lc Sensitive Readers` profile
> has no users or teams assigned, only sysadmins can read `lc_blockerreason` at all.
> Assign the cleared persona (here the `lc Owner`, Vivian Sun) to the profile before
> you expect a non-admin to see the column.

**Test:** in the visualizer, a cleared persona shows the cleartext value; an
uncleared, non-admin persona shows the masked value on the very same row (the
column omitted for `lc_blockerreason`, a `High:#`-style reveal for
`lc_RiskSummaryMask` on `lc_risksummary`). Row access did not change; column access
did. **Mind the masking nuance:** a plain read returns the mask to *everyone*,
sysadmins included, so do not "test as admin and assume cleartext means no security."
Compare a plain `GET` (masked) against `?UnMaskedData=true` (cleartext, only for a
caller with Read unmasked). (This also holds through Episode 7's `search_data`: the
platform enforces masking on the read, not the tool, so a secured value never leaves
Dataverse for an uncleared caller, even out of an attached file.)

---

## Building it programmatically (verified against this environment)

Every step below was run live against `lc_task` and confirmed end to end.

**Custom role + privilege**
- `POST /roles` with `name` + `businessunitid@odata.bind` (root BU); a fresh role
  starts empty.
- Resolve privilege ids (`/privileges?$filter=name eq 'prvReadlc_task'`), then
  `POST /roles({id})/Microsoft.Dynamics.CRM.AddPrivilegesRole` with
  `{"Privileges":[{"PrivilegeId":"…","Depth":"Local"}]}` (Depth `Basic` / `Local` /
  `Deep` / `Global`). Verify the landed depth with
  `GET /RetrieveRolePrivilegesRole(RoleId={id})`.

**Custom masking rule**
- `POST /maskingrules` with `name`, `displayname`, `maskedcharacter` (e.g. `#`),
  `regularexpression`, and `testdata`. The platform computes `maskedtestdata`
  server-side as a built-in self-test (`PASSWORD42` + regex `.(?=.{2})` + `*`
  returned `********42`), so a 201 with the expected `maskedtestdata` proves the
  regex before you ever attach it.

**Secure a column + attach the rule**
- Set **`IsSecured: true`** directly in the `POST …/Attributes` create (no separate
  PATCH needed), then `POST /PublishXml` for the entity.
- Bind the rule: `POST /attributemaskingrules` with `uniquename`,
  `attributelogicalname`, `entityname`, and **`MaskingRuleId@odata.bind`**
  (PascalCase nav; the lowercase `maskingruleid@odata.bind` 400s).

**Column security profile + permission**
- `POST /fieldsecurityprofiles` (`name`), then `POST /fieldpermissions` with
  `fieldsecurityprofileid@odata.bind`, `entityname`, `attributelogicalname`, and the
  permission columns. Option values: read/create/update `0` Not allowed, `4` Allowed;
  `canreadunmasked` `0` / `1` / `3`.
- **Send `canread` and `canreadunmasked` in the *same* payload.** Patching
  `canreadunmasked` alone fails `0x80040203` ("CanReadUnMasked=3, but CanRead=null"):
  the validator reads the companion value from the request body, not the stored row.
- Assign principals with `…/systemuserprofiles_association/$ref` (users) or the team
  association.

**Testing each one (impersonation)**
- Impersonate any user by adding the **`MSCRMCallerID: {systemuserid}`** header
  (needs `prvActOnBehalfOfAnotherUser`; sysadmin has it). Give the impersonated user
  a role that grants row read first, or they see zero rows.
- Then read the secured column twice. Verified matrix on `lc_task`:

  | Caller | Profile / Read unmasked | Plain `GET` | `?UnMaskedData=true` |
  |---|---|---|---|
  | non-admin, role only | not in profile | `null` (omitted) | n/a |
  | non-admin | Read, unmasked = Not allowed | `********42` | `********42` |
  | non-admin | Read, unmasked = All records | `********42` | `PASSWORD42` |
  | System Administrator | not in profile (bypass) | `********42` | `PASSWORD42` |

---

## Confirmation gates

- Both tasks write. Confirm `DATAVERSE_URL` before each run.
- Configuring column security requires the **System Administrator** role.
- Securing a column affects every reader immediately and org-wide; call that out
  before Task 2. Model-driven app users may need a browser refresh to see it.

## Errors

| Error | Likely cause | Fix |
|---|---|---|
| Zero rows resolving `prvReadSystemUser` | Wrong privilege stem | Use the legacy `User` stem (`prvReadUser`) |
| 400 on the privilege lookup | OData URL too long | Batch names ~30 per `$filter` request |
| 401 adding a user to a team | Missing one side of the M:M append | Grant both `prvAppendToTeam` and `prvAppendUser` |
| Secured column still readable | Profile bound to the reader's team | Bind only the cleared team to the profile |
| Secured column omitted for a member | Profile not assigned, or reads a stale cache | Add the user/team to the profile; allow a few seconds for the security cache |
| Masked value won't reveal as cleartext | Plain `GET`, or missing Read unmasked | Add `?UnMaskedData=true` *and* grant `canreadunmasked` (1 or 3); a plain `GET` never unmasks |
| Sysadmin still sees the mask | Masking applies to every plain read | Expected; request `?UnMaskedData=true` (sysadmins are always unmask-cleared) |
| `0x80040203` "CanReadUnMasked=N, but CanRead=null" | PATCHed `canreadunmasked` alone | Send `canread` and `canreadunmasked` together in one payload |
| `400` on `maskingruleid@odata.bind` | Wrong nav casing | Use PascalCase `MaskingRuleId@odata.bind` on `attributemaskingrules` |
| `Enable column security` greyed out | Column isn't securable | Virtual / lookup / formula / primary-name / system columns can't be secured |
| Masked field looks empty in code | Outside-profile reads are omitted | Treat null/absent over the Web API as no-access; a masking rule returns the mask string, not null |

## Tone

Concise and technical. Explain the axis, then make the change, then point at the
local app to prove it.
