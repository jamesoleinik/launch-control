# AGENTS.md

Portable guidance for coding agents (Cursor, Copilot, Claude Code, and any MCP
client) working in this repository. Cursor users also get
`.cursor/rules/dataverse-security.mdc`, which mirrors the Episode 8 section below.

## Repository shape

This repo is the "Launch Control" series: each `episodes/ep-NN-*/` folder is a
self-contained chapter with its own `README.md` (and often a `SKILL.md`). Shared
Python lives in `scripts/python/`, authenticated through `scripts/auth.py`, which
reads the target environment from a `.env` at the repo root. The RBAC visualizer app
is at `apps/rbac-visualizer/`.

## Global conventions

- **Never hardcode secrets or environment identifiers** (environment URLs, tenant
  ids, application ids, user ids, UPNs) in committed code or docs. Resolve them from
  `.env` or by query at runtime. Use placeholders in prose.
- **No em-dashes** (the `—` character) in committed prose or comments. Use a period,
  comma, colon, semicolon, or parentheses.
- **Idempotent scripts, dry-run first.** Setup and teardown scripts must be safe to
  re-run and should support `--dry-run`. Preview before applying.
- PowerShell: set `$env:PYTHONIOENCODING="utf-8"` before running Python.

## Episode 8: Dataverse security model

For any work on row-level, column-level, or per-agent security, the ordered rebuild
plan is `episodes/ep-08-security/REBUILD.md` and the model lives in the
`dataverse-security` skill (`episodes/ep-08-security/SKILL.md`). Load the skill, then
follow the runbook step order: teardown (Step 0), build the visualizer (Step 1),
row-level roles and teams (Step 2), persona assignment (Step 3), column-level
security (Step 4), per-agent security (Step 5).

Key invariants (full detail in the `.cursor` rule and the runbook):

- Roles `lc Member` / `lc Owner` / `lc Viewer` / `lc Admin`; owner-teams
  `lc <role>s`; profile `lc Sensitive Readers`; masking rule `lc_EmailMask`. Layer on
  top of `Basic User`.
- Column security covers **only** the two `lc_teammember` PII columns: `lc_email`
  (secured and masked) and `lc_fullname` (secured, hidden via a revoked read grant).
  Do **not** secure task or launch columns, and do **not** field-secure the primary
  `lc_name` (it is a non-PII ID; real names live in `lc_fullname`).
- A System Administrator bypasses column-level security but a masking rule masks even
  a sysadmin's plain read; the visualizer therefore reads the PII table as a non-admin
  profile member so the live policy is visible.
- Reset with `python scripts/python/teardown_security.py --confirm`.
- `scripts/python/seed_ep08_demo.py` is gitignored (real persona UPNs); keep it
  local-only.
