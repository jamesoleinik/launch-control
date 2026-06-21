---
name: dataverse-security
description: |
  Teaches the Dataverse security model and drives an agent to implement and test
  a specific slice of it against any Dataverse environment. The model has two
  independent axes plus a per-agent variant, and the calling prompt names which
  one to build and its targets.

  Use whenever the user asks to "explain the Dataverse security model" or to
  implement a named slice of it ("set up row-level security", "secure a column",
  "add data masking", "scope an application user / agent"). The prompt passes in
  the security TYPE to build and its TARGETS (tables, columns, role/profile
  names, personas or the application user). Supported types:
    - row-level     : security roles + owner-teams + business-unit depth, so the
                      same query returns different row counts per persona.
    - column-level  : secure columns + a field security profile (+ optional
      (data masking)  masking rule), so the same row returns cleartext for one
                      principal and a mask/omission for another.
    - per-agent     : assign a field security profile to an application user, so
                      effective column access is the intersection of the human's
                      profile and the agent's.
license: MIT
metadata:
  author: Launch Control
  version: "2.0"
---

# Skill: Dataverse security model (row-level, column-level, per-agent)

This skill explains how security works in Dataverse and then implements the
**specific slice** the calling prompt names. It is the knowledge layer, so the
prompts that use it can stay short: the *how* lives here, the *what* (the
security type plus its targets) comes in the prompt.

The whole point: connect any agent you like (Copilot, Claude, Cursor) to a
Dataverse environment, and what it can read is decided by the platform, not the
client. This skill makes that boundary something you can author and test, on
either axis, for a human or for an agent.

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
   difference between "I see only the rows I own" and "I see every row in the BU."

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

   Over the Web API the states are distinct, and were verified live (example
   secured column):

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
  eligibility flags are `CanBeSecuredForRead/Update/Create`. (So a virtual entity,
  for example, cannot be secured at the column level: govern it at the row level
  instead.)
- **Secure the calculated twin too.** If a calculated or composite column reads a
  secured column, secure that calculated/composite column as well, or the value
  leaks through it.
- **Agents are users; secure them per agent.** A connection authenticates as a real
  `systemuser`, a human or an **application user** (one with `applicationid` set,
  e.g. an MCP / Cowork connection). Field security binds to the agent's identity
  too, so assign profiles to application users for least privilege. Effective
  column access is the **intersection** of the human's profile and the agent's
  profile: the value returns only when both clear it. (A **delegated** OAuth
  connection runs *as the signed-in human*, so the human's clearance is what is
  enforced at runtime; the intersection applies when the agent reads under its own
  application-user identity, e.g. an S2S / client-credentials token.)

## Inputs: what the calling prompt must specify

This skill is environment-agnostic. The prompt that invokes it passes:

- **Security type**: `row-level`, `column-level` (data masking), or `per-agent`.
- **Targets**: the tables and columns to govern, the role / team / profile names
  to create, and the personas (or the application user) to assign.
- **Environment**: read the base URL from `.env` (`DATAVERSE_URL`) and reuse
  `scripts/auth.py` for the token. API base is `${DATAVERSE_URL}/api/data/v9.2`.

If the prompt names a security type but not the targets, ask for the missing
targets before writing. If it only asks to *explain* the model, answer from the
sections above and write nothing.

## Hard rules

1. **Confirm the environment first.** Print `DATAVERSE_URL` from `.env` and have
   the user confirm before any write. This skill makes real changes (roles,
   teams, secured columns, profiles).
2. **Idempotent by name.** Re-runs must be no-ops on creation and safely re-sync
   privileges. Never create a duplicate role/team/profile on a second run.
3. **One slice at a time.** Implement the requested security type, test it
   (impersonation or the local visualizer), then stop. If the prompt asks for
   several, do them in order and test each before the next.
4. **Python only**, consistent with the other episodes; reuse `scripts/auth.py`.

---

## Recipe: row-level security

Goal: make the row axis visible by returning *different* row counts for the same
query depending on the caller.

- Create the roles the prompt names, each granting `Read` (plus `Create`/`Write`
  as asked) on the target tables at the depth the prompt specifies. The classic
  contrast is one role at **Business Unit** depth (sees every row in the BU) and
  one at **User** depth (sees only the rows it owns).
- Create one **owner team** per role and bind the role via `teamroles_association`.
- Resolve privilege names first, apply with `AddPrivilegesRole`, and keep it
  idempotent with `--dry-run`, `--add-self`, `--remove-self` so the author can
  join a team and impersonate it.

**Test:** run the same table query as each persona (the `MSCRMCallerID` header or
the visualizer). The BU-depth role returns every row; the User-depth role returns
only the rows it owns. Same query, different lenses.

## Recipe: column-level security (data masking)

Goal: make the column axis visible by returning the *same row* with a sensitive
field readable for one principal and masked or omitted for another.

- **Secure** each target column (`IsSecured = true` at create, then `PublishXml`).
- Create a **column security profile** (`fieldsecurityprofile`), grant it
  `Read = Allowed` on the secured column(s), and bind the cleared team or users.
- A principal **outside** the profile gets the column **omitted (null)**, a full
  hide. A principal **inside** with `Read` sees cleartext.
- For a **partial** reveal (`###-##-6789`-style), attach a **masking rule** (regex
  + mask character, Text/Number columns, Managed Environment required) and grant
  `Read unmasked` (`1`/`3`). Then a plain `GET` returns the mask and
  `?UnMaskedData=true` returns cleartext for the unmasked-cleared.

**Test:** read the same row as a cleared vs. an uncleared (non-admin) principal.
Cleared sees the value; uncleared sees the column omitted (no rule) or the mask
(with a rule). Row access did not change; column access did. **Mind the nuance:** a
masking rule masks a plain read for *everyone*, sysadmins included, so compare a
plain `GET` (masked) against `?UnMaskedData=true` (cleartext, only for a caller
with Read unmasked) rather than testing as admin and assuming cleartext means no
security. (This holds through tools like semantic `search_data` too: the platform
enforces masking on the read, not the tool, so a secured value never leaves
Dataverse for an uncleared caller, even out of an attached file.)

> **Gotcha: a secured column with no profile members is readable only by System
> Administrators.** Until you assign a user or team to the profile, only sysadmins
> can read the secured column at all. Assign the cleared persona to the profile
> before you expect a non-admin to see it.

## Recipe: per-agent security

Goal: govern what the *agent* can read independently of the human, and prove the
intersection.

- The agent is an **application user** (a `systemuser` with `applicationid` set).
  Scope it like any user: remove over-broad roles (e.g. System Administrator),
  grant exactly the roles it needs, and place it **in or out** of the relevant
  column security profile.
- Read back **as the agent** with a client-credentials (S2S) token to prove the
  effective access. The secured column returns omitted/masked unless the agent's
  own identity is in the profile, even where the human is cleared. Effective
  column access is the **intersection** of the two profiles.
- Caveat: a **delegated** connection (OAuth, the user signs in as themselves) runs
  as the human, so at runtime it is the *human's* clearance that is enforced. The
  per-agent intersection applies when the agent reads under its own identity.

**Test:** run the same read as the agent vs. as the human; show the secured column
omitted for the agent even where the human can read it. Toggle the agent's profile
membership and re-read to show the intersection move (allow a few seconds for the
security cache).

---

## Building it programmatically (verified API patterns)

Every step below was run live and confirmed end to end; substitute your own
`<table>` / `<column>` / role / profile names for the placeholders.

**Custom role + privilege**
- `POST /roles` with `name` + `businessunitid@odata.bind` (root BU); a fresh role
  starts empty.
- Resolve privilege ids (`/privileges?$filter=name eq 'prvRead<table>'`), then
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
- Then read the secured column twice. Verified matrix (example column):

  | Caller | Profile / Read unmasked | Plain `GET` | `?UnMaskedData=true` |
  |---|---|---|---|
  | non-admin, role only | not in profile | `null` (omitted) | n/a |
  | non-admin | Read, unmasked = Not allowed | `********42` | `********42` |
  | non-admin | Read, unmasked = All records | `********42` | `PASSWORD42` |
  | System Administrator | not in profile (bypass) | `********42` | `PASSWORD42` |

---

## Confirmation gates

- Both recipes write. Confirm `DATAVERSE_URL` before each run.
- Configuring column security requires the **System Administrator** role.
- Securing a column affects every reader immediately and org-wide; call that out
  before column-level work. Model-driven app users may need a browser refresh.

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
