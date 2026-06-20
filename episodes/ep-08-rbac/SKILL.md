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
  version: "1.0"
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

   | Permission | Effect |
   |---|---|
   | **Read** | Can view the column. With a masking rule applied, a masked value is shown. |
   | **Read unmasked** | Can request the unmasked value (only meaningful when a masking rule is set). Default: not allowed. |
   | **Update** | Can change the column value. |
   | **Create** | Can set the column value on insert. |

   Anyone outside the profile gets the column **masked** even on a row they are
   fully allowed to read. With no masking rule the value is withheld entirely and
   the UI shows a lock + `********`; with a **masking rule** (a regular expression
   plus a mask character) you can instead show a *portion* of the value, e.g.
   `###-##-6789`. Masking rules work on Text and Number columns and require a
   **Managed Environment**; the **Read unmasked** permission lets a cleared user
   pull the full value one record at a time. Over the Web API the secured field
   comes back **null or omitted** for principals outside the profile (the
   `********` is a UI affordance), so treat absent as masked in code.

   Column security is **organization-wide** and applies to every data access
   request. Configuring it requires the **System Administrator** role.

These axes are evaluated **independently**. Field security is not a stronger
role; a secured column is masked for everyone outside its profile no matter how
powerful their role is.

> **Critical for testing: System Administrator is never masked.** Column security
> does not apply to users with the System Administrator role; data is never
> hidden from them. So you must verify masking with a **non-admin** account. In
> the visualizer, impersonate the `lc Member` (non-admin) persona, not "me"
> (the admin caller), or the mask will never appear.

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

## This environment

- Tables: the `lc_*` model (`lc_launch`, `lc_milestone`, `lc_task`,
  `lc_statusupdate`, `lc_teammember`, plus the `lc_githubissue` virtual entity).
- Secured columns are live in this environment now, shipped in the `LaunchControl`
  solution:
  - **`lc_teammember.lc_email`** (`IsSecured = true`), masked by the built-in
    **`Email_HideName`** rule and governed by the **`Custom Column security`**
    column security profile.
  - **`lc_launch.lc_description`** (`IsSecured = true`), masked by the custom
    **`lc_SSNcustomrule`** rule: mask character `#` plus a regex that reveals only
    the last four characters (the SSN `###-##-6789` shape from the masking-rules doc).
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
personas. `lc Owner` returns all 61 tasks; `lc Member` returns only the 4 it
owns. Same query, two lenses.

## Task 2: A data masking role to test column-level security

Goal: a profile that makes the column-level axis visible by returning the *same
row* with a sensitive field readable for one role and masked for the other.

This environment already ships the worked example, in the `LaunchControl` solution:

- **`lc_teammember.lc_email`** is secured (`IsSecured = true`) and carries the
  built-in **`Email_HideName`** masking rule. The **`Custom Column security`**
  profile grants `Read = Allowed`, `Create = Allowed`, `Update = Not allowed`, and
  `Read unmasked = One record` on it.
- **`lc_launch.lc_description`** is secured and carries the custom
  **`lc_SSNcustomrule`** rule (mask character `#`, a regex that reveals only the
  last four characters).

To build a slice from scratch the moves are the same: secure the column
(`IsSecured = true`), create a **column security profile** (`fieldsecurityprofile`),
grant the profile `Read = Allowed` on the column, and bind the cleared team to it.
Attach a **masking rule** (a regex + mask character on a Text/Number column, gated by
the **Read unmasked** permission and a Managed Environment) when you want a *partial*
reveal like `###-##-6789` instead of a full hide. Make the whole thing idempotent on
the profile name.

> **Gotcha, live in this environment: a secured column with no profile members is
> readable only by System Administrators.** The `Custom Column security` profile
> currently has no users or teams assigned, so today only sysadmins can read
> `lc_email` at all. Assign the cleared team to the profile before you expect a
> non-admin persona to see the column.

**Test:** in the visualizer, a cleared persona shows the cleartext value; an
uncleared, non-admin persona shows the masked value on the very same row (a hidden
local-part for the `Email_HideName` rule on `lc_email`, a `#####6789`-style reveal
for `lc_SSNcustomrule` on `lc_description`). Row access did not change; column access
did. **Test as a non-admin:** masking never applies to a System Administrator, so
impersonate `lc Member`, not the "me" / admin caller, or nothing will look masked.
(This also holds through Episode 7's `search_data`: the platform enforces masking on
the read, not the tool, so a secured value never leaves Dataverse for an uncleared
caller, even out of an attached file.)

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
| Secured column never looks masked | Testing as a System Administrator | Masking never applies to sysadmins; impersonate a non-admin persona |
| `Enable column security` greyed out | Column isn't securable | Virtual / lookup / formula / primary-name / system columns can't be secured |
| Masked field looks empty in code | `********` is UI-only | Treat null/absent over the Web API as masked |

## Tone

Concise and technical. Explain the axis, then make the change, then point at the
local app to prove it.
