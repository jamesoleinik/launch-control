# Rebuild runbook: the Episode 8 security model, from the ground up in Cursor

This is the on-camera script for rebuilding the entire security model from a clean
environment using a coding agent (Cursor). It pairs with the `dataverse-security`
skill ([`SKILL.md`](SKILL.md)) and the narrative in [`README.md`](README.md). The
README explains *why*; this file is the *ordered how*, so the agent reproduces
exactly where we landed without improvising.

## How to drive it on camera

For each step below:

1. **Say the prompt.** Paste the quoted "Prompt to Cursor" line into the agent. Each
   one is one sentence because the skill carries the mechanics.
2. **Let the agent write the script.** The expected artifact is named under "Produces".
3. **Run the verification.** The one-liner under "Verify" proves the layer landed
   before you move on.

`@`-mention this file and the `dataverse-security` skill at the start of the session
so the agent has the ordered plan and the model in context.

## Prerequisites

- A `.env` at the repo root with the target environment (read by
  [`scripts/auth.py`](../../scripts/auth.py)). Nothing in this repo hardcodes an
  environment, tenant, app, or user identifier; everything resolves from `.env` or
  by query at runtime. Keep it that way.
- The target environment is a **Managed Environment** (column masking rules require
  it) and you hold **System Administrator** on it.
- PowerShell: `$env:PYTHONIOENCODING="utf-8"` before any script run.

---

## Step 0 · Reset to a clean slate

Before recording, reverse any prior build so the camera starts from a wide-open
environment (no `lc` roles, no secured columns, the agent back on System
Administrator).

```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts/python/teardown_security.py            # dry-run: prints what it would remove
python scripts/python/teardown_security.py --confirm  # actually reset
```

`teardown_security.py` reverses the build in dependency order: restores the Cowork
app user to System Administrator, removes the `lc_EmailMask` masking rule and the
`lc Sensitive Readers` profile, un-secures the two `lc_teammember` PII columns, and
deletes the four `lc` roles and four `lc *s` teams. Flags: `--keep-rbac` (leave the
roles and teams in place), `--skip-agent-restore` (leave the app user scoped down).

**Verify:** PPAC shows zero `lc *` roles, and a read of `lc_teammember` returns
`lc_email` / `lc_fullname` in clear (nothing secured).

---

## Step 1 · Part 1: load the skill, build the visualizer

The visualizer is the instrument you watch every later layer land on, so it is built
first, while there is nothing to secure yet.

**Prompt to Cursor (load the skill):**

> _"Load the `dataverse-security` skill into this session. Confirm you have the
> Dataverse security model (row-level, column-level, per-agent) in context, then
> confirm the env from `.env` so we're ready to author the model."_

**Prompt to Cursor (build the app):**

> _"Use the `dataverse-security` skill. Build the impersonation visualizer app at
> `apps/rbac-visualizer/`: a persona dropdown that runs the same launch query under
> each persona's `MSCRMCallerID`, a row-count panel plus a per-row table (with an
> owner column) for the row-level axis, and a team-member (PII) table read as a
> non-admin profile member (a System Administrator bypasses column security, so
> reading as a member is what makes the policy visible) with two independent live
> toggles: one that attaches or detaches the `lc_email` masking rule, and one that
> revokes or grants the `lc_fullname` column read on the profile, so the table shows
> `lc_name` as a non-PII ID, `lc_email` masked or clear, and `lc_fullname` hidden or
> clear."_

**Produces:** `apps/rbac-visualizer/app.py`.

**Verify:**

```powershell
python apps/rbac-visualizer/app.py --mock   # offline render from the seeded snapshot
python apps/rbac-visualizer/app.py          # live; open http://127.0.0.1:5000
```

The row-count panel renders live immediately. The persona dropdown fills in after
Step 2; the two PII toggles come alive after Step 4.

---

## Step 2 · Part 2: row-level security (four roles, four teams)

**Prompt to Cursor:**

> _"Use the `dataverse-security` skill. Implement **row-level security**: create the
> four business roles, `lc Owner` (Business Owner, Business Unit depth), `lc Member`
> (Business User, User depth), `lc Viewer` (Business Reader, read-only at BU depth)
> and `lc Admin` (Business Admin), on the `lc_*` tables, each bound to its own
> owner-team."_

**Produces:** `scripts/python/setup_simple_rbac.py` (idempotent; `--dry-run`,
`--add-self`, `--remove-self`).

**Verify:**

```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts/python/setup_simple_rbac.py --dry-run   # preview, no writes
python scripts/python/setup_simple_rbac.py             # create roles + teams, bind
python scripts/python/setup_simple_rbac.py --add-self  # add yourself to all four teams
python scripts/python/rbac_smoketest.py                # same read through each persona
```

The dropdown in the visualizer now fills with one persona per `lc` team. Flipping it
rewrites the row counts live: Member 4 tasks, Owner and Viewer 12, Admin blank.

---

## Step 3 · Assign the demo personas

Map real demo users onto the Member / Owner / Viewer lenses and vary task ownership
so the row-level axis has something to show (the owner column explains why a
User-depth persona sees only its own rows).

```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts/python/seed_ep08_demo.py
```

> **Note:** `seed_ep08_demo.py` is gitignored because it carries real persona UPNs.
> It is local-only; the live environment assignment is the deliverable, not a tracked
> file. Re-create it from this prompt if it is missing on a fresh clone.

**Verify:** the visualizer's Axis-1 row table shows distinct owners (the Owner
persona and a second owner across the task rows).

---

## Step 4 · Part 3: column-level security (mask the email, hide the name)

Two PII columns on `lc_teammember`, two different levers.

**Prompt to Cursor:**

> _"Use the `dataverse-security` skill. Implement **column-level security** over the
> team-member PII. Mask the `lc_email` address with a masking rule so every role but
> the admin reads it redacted. Hide the full name with pure column-level security:
> move the real name into a new securable `lc_fullname` column (the primary
> `lc_name` becomes a non-PII ID), secure it, and revoke the read grant so it is
> omitted outside the `lc Sensitive Readers` profile."_

**Produces:** `scripts/python/setup_field_security.py` (secures only the two
`lc_teammember` PII columns; the task and launch tables are deliberately left out of
column security). Do **not** secure the primary `lc_name` column (Dataverse rejects
field security on the primary name, `0x8004f501`); that is why the real name lives in
the new `lc_fullname` column and `lc_name` is demoted to a non-PII ID.

**Verify:**

```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts/python/setup_field_security.py        # secure + profile + mask + grant
python scripts/python/toggle_email_mask.py --on      # email redacts to a#########@example.test
python scripts/python/toggle_email_mask.py --off     # email back to cleartext
```

In the visualizer (which reads the PII table as a non-admin profile member): the
email toggle redacts or reveals `lc_email`, and the full-name toggle hides or shows
`lc_fullname`. With the grant revoked, `lc_fullname` comes back blank (shown as the
mask block); a signed-in admin would bypass column security and still see cleartext,
which is exactly why the table reads as a profile member.

---

## Step 5 · Part 4: per-agent security (scope the agent down)

The Cowork connection is a real application user. Field security binds to the agent,
so effective column access is the **intersection** of the human's profile and the
agent's profile.

> **Delegated auth, two prerequisites.** Cowork reads run as the **signed-in human**,
> so that human (your Cowork account) must (1) hold an `lc` role that grants Read on
> the launch model, or Cowork sees nothing at all (every `lc_*` query returns 403,
> not just the PII columns), and (2) be in `lc Sensitive Readers` if you want PII to
> show. Add the account to the `lc Owners` team for full-launch Read:
> `toggle_sensitive_readers.py` handles the profile half; team membership handles the
> table half. Separately, scoping the **agent** off System Administrator strips the
> `prvReadSolution` / `prvReadPublisher` reads the Dataverse MCP needs to enumerate
> the environment on connect, so `setup_agent_security.py` re-grants those two
> metadata reads on the `lc Owner` role (they expose no record data).

**Prompt to Cursor:**

> _"Use the `dataverse-security` skill. Implement per-agent security: the Cowork
> application user currently inherits System Administrator. Scope it down (remove
> System Administrator, ensure `Basic User + lc Owner`, leave it out of the
> `lc Sensitive Readers` profile) so it has Read on the `lc_*` columns Cowork
> legitimately needs and is withheld Read on the `lc_teammember` PII columns
> (`lc_email`, `lc_fullname`). Then prove the intersection: read `lc_teammember` as
> the Cowork app user versus as me, and show the secured columns come back omitted
> for the agent even where the human is cleared."_

**Produces:** `scripts/python/setup_agent_security.py` (`--demo-grant` toggles the
agent in and out of the profile).

**Verify:**

```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts/python/setup_agent_security.py             # scope down + read back as the agent
python scripts/python/setup_agent_security.py --demo-grant  # place the agent in the profile, re-read
python scripts/python/toggle_sensitive_readers.py --user <demo-user> --in   # human in profile
python scripts/python/toggle_sensitive_readers.py --user <demo-user> --out  # human out of profile
```

The agent reads all four `lc_teammember` rows (it stays useful), but `lc_fullname`
comes back omitted until the agent itself is in the profile. Field-security membership
changes propagate with a short cache delay; allow a few seconds between a toggle and
the read.

---

## Final state to confirm before "cut"

| Layer | Expected on camera |
| --- | --- |
| Roles | four `lc` roles (`Member` / `Owner` / `Viewer` / `Admin`), each bound to an `lc *s` owner-team |
| Row-level | Member sees 4 tasks, Owner and Viewer 12, Admin blank, same query |
| Column-level | `lc_email` masked when the rule is on, `lc_fullname` hidden when the grant is revoked, both only on `lc_teammember`; task and launch columns untouched |
| Primary name | `lc_name` is a non-PII ID (`TM-001` ...), real names live in `lc_fullname` |
| Per-agent | Cowork app user scoped to `Basic User + lc Owner`, omitted `lc_fullname` until placed in the profile |
| Recording-ready default | email mask in the desired start state and `lc_fullname` **visible** (grant present) |

To return to a clean slate for another take, re-run Step 0.
