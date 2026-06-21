# Episode 8 — Roles & Reach: security in a headless world

**Status:** ✅ Re-platformed to a new tenant/env (`org1077ae7c`, `agent365003`) · ✅ Cowork plugin rebuilt for the new env (`dataverse-launchcontrol-agent365`, v1.6.0) · ✅ Four roles + four teams live · ✅ Three demo personas assigned (Member / Owner / Viewer) · ✅ Column masking live + verified end to end (`lc_RiskSummaryMask` + `lc Sensitive Readers` profile, tested via impersonation) · ✅ Row + column smoke-test verified · ✅ Per-agent security verified (Cowork app user scoped down, intersection proven via client-credentials) · ✅ Cowork runtime sign-in identity ready (`eppc2026demo2`, Owner lens, in `lc Sensitive Readers`) · 🎬 Not yet recorded
**Features:** ⭐ **Two axes of security for agents:** row-level (four flat roles: Member / Owner / Viewer / Admin) **and** data masking (column-level / field security over sensitive `lc_*` columns) · ⭐ **Per-agent control:** the agent is its own application user, so field security binds to the Cowork connection independently of the human, and Dataverse enforces the intersection · ⭐ Coverage over Eps 1–7: `lc_*` tables, the `lc_githubissue` virtual entity, the `lc_CalculateLaunchReadiness` Custom API, the MCP connectors, and Ep 7's `search_data` over attached files · ⭐ Authored (and enforced) from any coding agent, now including **Cursor**
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
   hidden even on rows a caller is allowed to read. A column security profile plus
   a masking rule over `lc_task.lc_blockerreason` and `lc_launch.lc_risksummary`, so an
   unprivileged agent gets the column omitted and a cleared one gets a partial mask.

Together they are the toolset an agent developer needs over sensitive data: an
agent can be broadly useful and still never surface what it shouldn't. And every
bit of it is authored from a coding agent (now Cursor included) against a
one-line spec.

And there is a move most platforms can't make: because every agent connects as
its own **application user**, the same field security binds to the *agent's*
identity, not just the human's. You set the right access for every user **and**
every agent, and Dataverse enforces the **intersection**. That is Part 4.

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

Then the agent does the building, and it doesn't need a wall of instructions to
do it. We load one skill, [`dataverse-security`](SKILL.md), a generic skill that
teaches the agent the whole Dataverse security model: the two axes, depth levels,
the privilege-naming gotchas, field security, and how to keep every change
idempotent. The skill is environment- and episode-agnostic: each prompt passes in
the **security type** to build (`row-level`, `column-level`, or `per-agent`) plus
its targets, and the skill supplies the *how*. With that skill loaded, each ask is
one line. From those one-liners the agent drives the governed Dataverse APIs
(`dv-security`, `dv-metadata`) to author:

- two roles + their owner-teams to test row-level security (Part 2),
- the secured columns and the `lc Sensitive Readers` profile (plus the
  `lc_RiskSummaryMask` rule) to test data masking (Part 3),
- and a small **impersonation visualizer app**
  ([`apps/rbac-visualizer/`](../../apps/rbac-visualizer/)) so the whole model is
  something you can *see*, not just read about.

That last one is the demo vehicle. The skill describes a tiny Flask app that lets
you pick a persona from a dropdown and runs the *same* launch query as that user,
with the real `MSCRMCallerID` impersonation header set under the hood. Two lenses
render side by side: a row-count panel (Part 2's row-level security) and a task
table whose secured columns show either cleartext or a red `████████` (Part 3's
masking). One screen, both axes, any persona.

### Prompt to Cursor: load the skill into the session, then build the test app

First, have Cursor pull the generic security skill into the session so the model
is resident before any building. This is a concrete Cursor action: reference the
skill by name and let Cursor load `SKILL.md` into context.

> _"Load the `dataverse-security` skill into this session. Confirm you have the
> Dataverse security model (row-level, column-level, per-agent) in context."_

With the skill resident, ask it to stand up the demo vehicle. Because the skill
carries the spec, the ask stays one line:

> _"Use the `dataverse-security` skill. Build the impersonation test app it
> describes at `apps/rbac-visualizer/`, then confirm the env from `.env` so we're
> ready to author the model."_

The skill carries the spec, so the ask stays short. Cursor writes the app once;
you run it after each part to *see* the change.

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

### Prompt to Cursor: build the row-level security

With the `dataverse-security` skill loaded, the ask names the security type and
its targets in one line:

> _"Use the `dataverse-security` skill. Implement **row-level security**: create
> two roles to test it, `lc Owner` (Business Unit depth) and `lc Member` (User
> depth), on the `lc_*` tables, each bound to its own owner-team."_

The skill knows the rest: `lc Owner` reads every row at Business Unit depth,
`lc Member` reads only its own at User depth, each bound to its own owner-team,
privilege names resolved and batched, idempotent with `--dry-run` / `--add-self`
/ `--remove-self`. Two roles are all you need to *see* the row-level contrast.

The shipped [`scripts/python/setup_simple_rbac.py`](../../scripts/python/setup_simple_rbac.py)
generalizes that same pattern to the full four-role matrix below (adding a
read-only `lc Viewer` and a user-management `lc Admin`), and does five things:

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
Env: https://org1077ae7c.crm.dynamics.com
Caller userid: e10742fd-1e6b-f111-ab0c-70a8a59bcaf0
Root BU:  Product Launch 2.0 (91634a81-6a55-f111-bec6-6045bd0a4d9d)
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
```

Then `scripts/python/seed_ep08_demo.py` assigns one demo persona per surface
(`Basic User` + the matching `lc` role + team membership) and reassigns a subset
of tasks so the Member's User-depth view is strictly smaller:

```
  lc Member  -> Walt Perry   [Basic User + lc Member + team lc Members]
  lc Owner   -> Vivian Sun   [Basic User + lc Owner  + team lc Owners]
  lc Viewer  -> Rick Brighenti [Basic User + lc Viewer + team lc Viewers]
  reassigned 4 task(s) to the Member persona (Owner/Viewer still see all 12)
```

That's the substrate Episode 8 demonstrates. Re-runs are no-ops on creation
and idempotently re-sync privileges.

---

### Proof: smoke-test by impersonation (same query, three lenses)

Same trick as the Episode 4 federation beat, except now we run **one** query
as **three personas** by switching the `MSCRMCallerID` header on the same HTTP
client. The shipped [`scripts/python/rbac_smoketest.py`](../../scripts/python/rbac_smoketest.py)
runs the `lc_task` query through each persona (a member of one of the `lc` teams)
and prints a row-count table:

```
=== Row-level: lc_task count per persona ===

Persona            visible lc_task
------------------------------------
Member (Walt)                    4
Owner (Vivian)                  12
Viewer (Rick)                   12
```

> `Member (Walt)` sees **4** tasks, not 12, because `User`-level depth on
> `lc_task` returns only records the calling user owns, not the 8 owned by
> the seed user. That's the bullseye demonstration of why depth matters.

The Owner and Viewer personas both see all 12 at Business-Unit depth; the
difference between them is write access, not reach. (`lc Admin` is a
user-management role with zero data privileges by design, so it's blank for the
data columns — Admin alongside Owner gives full data + team management.)

### Test it locally

The visualizer renders exactly this table, live. Run it and switch personas: the
row-count panel jumps from 4 (Member) to 12 (Owner/Viewer) to blank (Admin), the
same numbers the smoke-test prints, but in a UI you can flip in front of an
audience.

```powershell
python apps/rbac-visualizer/app.py        # or --mock for the seeded demo
# open http://127.0.0.1:5000
```

---

## Part 3 · Data masking: column-level security over sensitive fields

**Axis two: which sensitive fields stay hidden, even on rows you can read.**

Row-level security answers *which rows*. It does nothing about *which columns*.
An `lc Owner` who can read all 12 tasks also reads every sensitive column on those
rows: the `lc_task.lc_blockerreason` explaining why a task is stuck, or the
`lc_launch.lc_risksummary` the readiness prompt writes. In a headless world
that matters more, not less: the agent you just connected from Cursor inherits
exactly what its caller can see. Broad read access plus sensitive columns equals
a leak waiting to happen.

Dataverse's answer is **column-level security** (the API still calls it field
security). You flag a column as secured, then a **column security profile**
grants `Read` / `Read unmasked` / `Update` / `Create` on that column to specific
users or teams. A principal *outside* the profile gets the column back **omitted
(null)** over the Web API, even on a row they are fully allowed to read. A
principal *inside* the profile with `Read` sees the value, and a **masking rule**
(a regex plus a mask character) turns that into a *partial* reveal like
`###-##-6789`. It's [organization-wide and needs the System Administrator role to
configure](https://learn.microsoft.com/en-us/power-platform/admin/field-level-security).

> **One catch worth knowing on camera, and verified live: a masking rule masks a
> plain read for *everyone*, System Administrators included.** A sysadmin reading a
> masked column with a normal query still gets `###-##-6789`; the cleartext comes
> back only when the request adds `?UnMaskedData=true` (which the platform honors
> for a sysadmin, and for a non-admin only if their profile grants `Read unmasked`).
> What sysadmins *do* bypass is classic column *access*: on a secured column with no
> masking rule they always read cleartext. So the demo runs two reads side by side,
> not "admin equals no security."

The live environment now ships exactly this, in the `LaunchControl` solution:

| Secured column | Table | Masking rule | In the profile sees | Outside the profile sees |
|---|---|---|---|---|
| `lc_email` | `lc_teammember` | (none) | cleartext email (PII) | column omitted |
| `lc_blockerreason` | `lc_task` | (none) | cleartext blocker reason | column omitted |
| `lc_risksummary` | `lc_launch` | `lc_RiskSummaryMask` (mask `#`, severity-prefix reveal) | `High:#`-style mask; cleartext with `Read unmasked` | column omitted |

The `lc Sensitive Readers` profile is assigned to the `lc Owner` persona (Vivian
Sun); the `lc Member` persona (Walt Perry) is left out, so the impersonation test
shows the column withheld for outsiders.

### Prompt to Cursor: build the data masking

Skill loaded, the ask is again one line:

> _"Use the `dataverse-security` skill. Implement **column-level security (data
> masking)**: secure `lc_task.lc_blockerreason` and `lc_launch.lc_risksummary`,
> create the `lc Sensitive Readers` profile, and add the `lc_RiskSummaryMask` rule
> on the risk summary."_

The skill carries the verified recipe: secure the column (`IsSecured = true` at
create, then `PublishAllXml`), create a `fieldsecurityprofile` (here
`lc Sensitive Readers`), attach a masking rule via `attributemaskingrules`
(PascalCase `MaskingRuleId@odata.bind`, requires a Managed Environment and a
`uniquename`), and grant `canread` (`4` = Allowed) plus `canreadunmasked`
(`0`/`1`/`3`, **not** `4`) *in the same payload* (patching the unmask flag alone
fails `0x80040203`). Every one of those steps was run live against the secured
`lc_task` / `lc_launch` columns and confirmed end to end before this episode shipped.

The shipped script is
[`scripts/python/setup_field_security.py`](../../scripts/python/setup_field_security.py),
and the impersonation result it produces:

```
=== Column-level: secured fields per persona ===

Persona            blockerreason   risksummary (plain)   risksummary (unmasked)
-----------------  --------------  --------------------  ----------------------
Member (Walt)      <omitted>       <no row>              <no row>
Owner (Vivian)     cleartext       High:#                High: 4 blocked tasks...
Viewer (Rick)      <omitted>       <omitted>             <omitted>
```

(The Member sees no launch row at all at User depth; the Viewer reads the rows but
is outside the profile, so both secured columns are omitted.)

### Test it locally

Re-run the visualizer and flip between the `lc Owner` and `lc Member` personas.
The cleared persona sees the value; an uncleared, non-admin persona sees the mask
on the very same rows. Row access didn't change; column access did. (Compare a
plain read against an `?UnMaskedData=true` read rather than assuming "admin sees
cleartext" means no security: a masking rule masks the admin's plain read too.)

```powershell
python apps/rbac-visualizer/app.py        # or --mock for the seeded demo
# open http://127.0.0.1:5000
```

### The Episode 7 callback: masking holds even through `search_data`

This is the beat that makes the point. Episode 7's `search_data` does semantic
search across rows **and the content inside attached files**. The obvious worry:
does an agentic search tool route around column security and hand the agent the
secured value anyway, or surface it out of an attached PDF?

It doesn't. Field security is enforced by the platform on the *read*, not by
each tool. Run the same `lc_task` search as a `lc Member`-only caller and the
`lc_blockerreason` field comes back `********`; run it as an `lc Owner` in the
profile and the cleartext returns. Same query, same agent, same client: the
column the caller isn't cleared for never leaves Dataverse, no matter which
tool asked for it.

```
=== search_data: 'export blocker on Q3', two lenses ===

Caller            lc_task match   lc_blockerreason returned
--------------    -------------   -------------------------
member-only               ✓        ********
owner + profile           ✓        "Customs paperwork rejected; legal hold on EU SKU"
```

> That is the whole thesis in one table: the agent stays useful (it still finds
> the right task), and the platform still refuses to leak the sensitive field.

> **Masking rules for a partial reveal (now live in this environment).** Securing a
> column with no profile access hides it entirely (the column is omitted). To show
> *part* of a value instead, Dataverse [masking rules](https://learn.microsoft.com/en-us/power-platform/admin/create-manage-masking-rules)
> apply a regular expression plus a mask character, so a value reads `###-##-6789`.
> They work on Text and Number columns and require a Managed Environment. The
> cleartext behind the mask comes back only on a request that adds
> `?UnMaskedData=true` *and* whose profile grants `Read unmasked` (`One record` or
> `All records`). This is how `lc_RiskSummaryMask` masks `lc_launch.lc_risksummary`
> today: a plain read returns `High:#` and the cleartext returns only with
> `?UnMaskedData=true`.

---

## Part 4 · Per-agent security: the agent is its own user

Everything so far secured *people*. But in a headless world the thing actually
holding the connection is an **agent**, and on most platforms an agent is a
shared API key with one blunt scope: it sees whatever the integration was wired
to see. There is no "this agent, specifically" to govern.

Dataverse models it differently. The Cowork connection from Part 1 isn't a key;
it's a real **application user** in the same `systemuser` table as every human,
with its own roles and its own field security. It's already in this environment:

```
# the Cowork agent's identity, created in Part 1 (Entra app -> Dataverse app user)
fullname:   LaunchControl-Cowork-MCP-agent365
type:       application user (applicationid set, S2S auth)
```

Because the agent is a first-class user, **field security binds to the agent**,
not just to the person. So you get two independent dials over every sensitive
column:

- the **human's** field security profile (what *Priya* may read), and
- the **agent's** field security profile (what *Cowork* may read),

and the value only returns when **both** clear it. Effective column access is the
**intersection** of the two. Lock a column down on the agent and it stays masked
through Cowork even for a human who could read it directly in a model-driven app,
because the request also carries the agent's identity.

### Prompt to Cursor: secure the agent, not just the user

```text
Use the dataverse-security skill. Implement per-agent security: the Cowork
application user (LaunchControl-Cowork-MCP-agent365) currently inherits System
Administrator. Scope the application user down (remove System Administrator, leave
it out of the lc Sensitive Readers profile) so it has Read only on the lc_*
columns Cowork legitimately needs and is withheld Read on lc_blockerreason and
lc_risksummary. Then prove the intersection: run the same lc_task read as the
Cowork app user vs. as me, and show that the secured columns come back omitted for
the agent even where the human is cleared.
```

### The intersection, made concrete

Same launch, same secured `lc_blockerreason` column, two identities on the call:

| Human's profile | Agent's (Cowork) profile | What Cowork returns |
| --- | --- | --- |
| in profile (cleared) | in profile (cleared) | cleartext |
| in profile (cleared) | **not** in profile | `████████` (agent blocks it) |
| not in profile | in profile (cleared) | `████████` (human blocks it) |
| not in profile | not in profile | `████████` |

The human can read it in the app, but the agent cannot read it *for* them. That
is per-agent least privilege: you scope each agent to exactly the columns its job
needs, independent of how privileged its operators are.

The shipped
[`scripts/python/setup_agent_security.py`](../../scripts/python/setup_agent_security.py)
scopes the Cowork app user down (removes System Administrator, ensures
`Basic User + lc Owner`, leaves it out of the profile) and reads back **as the
agent** with a client-credentials token. The live result:

```
[1] Scope the agent down to least privilege
  removed role: System Administrator
  ensured role: Basic User
  ensured role: lc Owner

[2] Read AS the agent (client-credentials token)
  [agent / least-privilege] tasks=12  blockerreason=<omitted>  risk(plain)=<omitted>  risk(unmasked)=<omitted>
  [agent / IN profile]       tasks=12  blockerreason='Pen-test escalation...'  risk(unmasked)='High: 4 blocked tasks...'
```

The agent still reads all 12 task rows (it stays useful), but the two secured
columns come back omitted until the agent itself is placed in the profile. That is
the intersection, enforced on the agent identity. (Field-security membership
changes propagate with a short cache delay, so allow a few seconds between a
profile toggle and the read.)

### Showcase it live in Cowork: runtime enforcement, not building

This is the payoff beat, and it isn't about authoring anything. It's watching
Dataverse enforce the model you already built, **at runtime**, through Cowork.

The plugin authenticates with `OAuthPluginVault`, so **each person signs in with
their own Dataverse identity** and every read Cowork makes runs *as that user*.
For the demo we sign in as a purpose-built launch-owner account:

> **Cowork sign-in identity: `eppc2026demo2@agent365003.onmicrosoft.com`**
> Scoped to the **Owner lens**: `Basic User` + `lc Owner` + the `lc Owners` team,
> placed **in** the `lc Sensitive Readers` profile, with **System Administrator
> removed** so the security model actually applies to it. It owns 8 of the 12
> tasks and reads the other 4 at BU depth, so it sees the whole launch.

The sharpest version of this beat is PII. Ask Cowork for the launch team's contact
details, a question whose answer is plain personal data:

> _"Who is on the Q3 Widget Launch team? List each member with their email address."_

Run it twice, starting **out** of the profile. **Out** of `lc Sensitive Readers`,
Cowork comes back blind: it can name the four team members but every email is
**omitted**, so it renders each one as _"Not on file."_ That is the platform
hiding the column on the live read, not the agent choosing to be coy. (Cowork
receives `null` for a withheld column and can't tell "secured" from "empty," so
narrate "Not on file" as *the platform withheld it*.) Now swap the flag, add
`eppc2026demo2` to the profile, and ask the *same* question: the four real
addresses come back in cleartext. Same agent, same prompt, same human, only the
runtime clearance changed.

The toggle is one command (the same one Cursor runs in the demo):

```powershell
python scripts/python/toggle_sensitive_readers.py --in    # reveal (cleartext)
python scripts/python/toggle_sensitive_readers.py --out   # hide (omitted)
python scripts/python/toggle_sensitive_readers.py --status
```

> **Why email uses full field security, not a masking rule.** Cowork's MCP read is
> a plain `GET` with no `?UnMaskedData=true`, and a masking-rule column **always**
> returns the mask on a plain read, even to an unmasked-cleared caller. So a masked
> column reads the *same* in Cowork whether or not the human is cleared (this is
> exactly why `lc_risksummary` shows `High:#` in Cowork even for a profile member).
> The only model that flips to genuine **cleartext** through Cowork is full field
> security (`canread` in/out): in the profile the value returns, out of it the
> column is omitted. That is why the email reveal uses `canread` membership, not a
> mask. Reserve masking rules for the impersonation/visualizer path that *can* send
> `?UnMaskedData=true`.

The readiness question works the same way over `lc_task.lc_blockerreason` and the
masked `lc_launch.lc_risksummary`: _"Is the Q3 Widget Launch ready to ship? List
every blocked task with its blocker reason, and give me the risk summary."_ In the
profile the blocker reasons are cleartext and the risk summary returns masked
(`High:#`); out of it the blocker reasoning is omitted and Cowork can only answer
from what it is cleared to see. Same agent, same prompt, same human, only the
runtime clearance changed, and the platform enforced it on the live read.

> **Which identity is enforced.** Interactive Cowork runs **delegated**, so what
> you see on screen is Dataverse enforcing the *signed-in user's* clearance
> (`eppc2026demo2`) at runtime. The per-agent **intersection** above (the agent's
> own application-user profile, independent of the human) is the same idea one
> layer deeper, proven headlessly by `setup_agent_security.py` reading as the
> Cowork app user over a client-credentials (S2S) token.

> **Good luck doing this on another platform.** Per-user *and* per-agent field
> security, enforced as an intersection on every read, falls out of one fact:
> agents and people share the same identity model. There's no second
> authorization system to wire up, and no shared key to over-scope.

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
4. **Field security is a second axis, not a stronger role.** A secured column is
   governed by its profile regardless of how powerful the caller's role is, and a
   masking rule masks even a System Administrator's plain read (cleartext needs
   `?UnMaskedData=true`). Row access and column access are evaluated independently.
5. **The agent is a user, so secure it like one.** Every connection authenticates
   as a real `systemuser` (a human or an application user). Field security binds to
   the agent's identity too, so effective column access is the intersection of the
   human's profile and the agent's profile. Scope each agent to least privilege;
   don't lean on a shared key.

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
3. **Load one skill.** In Cursor (or Claude Code, any MCP client) load the
   `dataverse-security` skill. From here every ask is one line, because the
   skill carries the model. First ask: _"build the test app it describes."_ The
   agent writes the `apps/rbac-visualizer/` Flask app.
4. **Two roles to test.** _"Create the two roles to test row-level security."_ The
   agent writes `setup_simple_rbac.py`. `--dry-run` prints the plan; the real run
   prints `created`, `applied N privileges`, `team created, role bound`.
5. Real run: `created`, `applied N privileges`, `team created, role bound`
   for every role. Self-add: four `✅` lines.
6. PPAC → Security → Roles **after**: four new roles. Click `lc Viewer`:
   only the `lc_*` tables have check marks, all Read.
7. PPAC → Security → Teams → `lc Owners` → Members tab: the caller appears.
8. **The visualizer, axis one.** Open `apps/rbac-visualizer/` in the browser and
   flip the persona dropdown. The row-count panel rewrites live: Member shows 4
   tasks, Owner and Viewer show 12, Admin shows blanks. Same query, three lenses,
   one screen, real `MSCRMCallerID` impersonation underneath.
9. **Axis two, masking.** Third ask: _"add the data masking role."_ The agent
   secures the sensitive columns, creates the `lc Sensitive Readers` profile, and
   attaches the `lc_RiskSummaryMask` rule. Back in the visualizer, an uncleared persona's task
   table shows the column omitted or masked where the sensitive value should be; a
   cleared persona shows it (and the cleartext only on an `?UnMaskedData=true` read).
   The row was readable; the column still wasn't.
10. **The Episode 7 callback.** Re-run Ep 7's `search_data` for the Q3 export
    blocker as a Viewer-only caller and as an Owner-in-profile. Same agent, same
    query: the Viewer gets `████████`, the Owner gets the sentence, even though
    the match came from inside an attached PDF.
11. **Runtime enforcement in Cowork (the showcase).** Sign into Cowork as
    `eppc2026demo2` (the Owner-lens identity, in the `lc Sensitive Readers`
    profile) and ask the readiness question. Cowork returns the whole launch with
    the blocker reasons cleared and the risk summary masked, all enforced live on
    the delegated read. Pull `eppc2026demo2` out of the profile and ask again: the
    blocker reasoning is gone. Same agent, same prompt, same human, only the
    runtime clearance changed. Nothing was built on screen; the platform enforced
    what it already knew.
12. **The punchline:**
    > _"Two axes, one platform. Row security decides which rows come back; field
    > security decides which columns. The data didn't change; the platform's
    > willingness to return it did. Connect any agent you like, from any client,
    > now including Cursor. The answer is still the same."_

---

## Files in this episode

| File | Role |
|---|---|
| [`SKILL.md`](SKILL.md) | The generic `dataverse-security` skill: teaches the two-axis Dataverse security model (plus the per-agent variant) and drives a named slice passed in by each prompt (security type + targets). The knowledge layer behind every prompt below. |
| [`scripts/python/setup_simple_rbac.py`](../../scripts/python/setup_simple_rbac.py) | Creates four roles + four owner-teams in the root BU; applies the privilege matrix; binds role↔team. Idempotent. `--dry-run`, `--add-self`, `--remove-self`. |
| [`scripts/python/seed_ep08_demo.py`](../../scripts/python/seed_ep08_demo.py) | Assigns three demo personas (Member / Owner / Viewer) to the `lc` roles + teams, reassigns a task subset to the Member, and seeds the sensitive columns (`lc_blockerreason`, `lc_risksummary`). Idempotent. |
| [`scripts/python/setup_field_security.py`](../../scripts/python/setup_field_security.py) | Secures `lc_task.lc_blockerreason` + `lc_launch.lc_risksummary`, creates the `lc Sensitive Readers` profile, creates + binds the `lc_RiskSummaryMask` masking rule, and grants `canread` (+ `canreadunmasked`) on the profile. Idempotent. |
| [`scripts/python/rbac_validate.py`](../../scripts/python/rbac_validate.py) | End-to-end probe of every RBAC primitive used here: test BU, owner team, role clone via `CloneAsRole`, role bind, `MSCRMCallerID` impersonation, cleanup. Run once per env to confirm plumbing. |
| [`scripts/python/rbac_smoketest.py`](../../scripts/python/rbac_smoketest.py) | Runs the row-level count and the column-level visibility checks across the three personas by switching `MSCRMCallerID`, and prints both tables. |
| [`scripts/python/setup_agent_security.py`](../../scripts/python/setup_agent_security.py) | Part 4: scopes the Cowork application user down from System Administrator, reads back as the agent via client-credentials, and proves the per-agent intersection (`--demo-grant` toggles the profile). Idempotent. |
| [`apps/rbac-visualizer/`](../../apps/rbac-visualizer/) | The persona impersonation visualizer Cursor builds in Part 1. Flask app, `--mock` (seeded snapshot) and live modes; real `MSCRMCallerID` impersonation; renders row counts (axis one) and masked secured columns (axis two) side by side. |
| [`datamodel/security/role-matrix.md`](../../datamodel/security/role-matrix.md) | _(planned)_ Human-readable rendering of the privilege matrix and the secured-column profile, kept in sync with the scripts as documentation. |
| [`episodes/ep-08-rbac/preflight.py`](preflight.py) | _(planned)_ Read-only check: are the four roles + four teams present, are the sensitive columns secured with the profile bound, is the caller a member of any team, are the `lc_*` tables resolved. |

---

## Run it yourself

```powershell
# from launch-control/
$env:PYTHONIOENCODING='utf-8'

# 0. Ensure the env is reachable (this episode runs on the agent365003 tenant)
az login --tenant 01eed126-9f96-4d2d-a127-dc2e786a898b --scope "https://org1077ae7c.crm.dynamics.com/.default"

# 1. Preview the role + team plan
python scripts/python/setup_simple_rbac.py --dry-run

# 2. Create roles + privileges + teams + bindings
python scripts/python/setup_simple_rbac.py

# 3. Assign the three demo personas + seed the sensitive columns
python scripts/python/seed_ep08_demo.py

# 4. Secure the sensitive columns + masking rule + field security profile
#    (requires a Managed Environment — enable with:
#     pac admin set-governance-config --environment <url> --protection-level Standard)
python scripts/python/setup_field_security.py

# 5. (Optional) End-to-end primitives validation, then cleanup
python scripts/python/rbac_validate.py

# 6. Run the same query through each persona + check masked fields
python scripts/python/rbac_smoketest.py

# 7. Part 4: scope the Cowork agent down + prove the per-agent intersection
python scripts/python/setup_agent_security.py --demo-grant

# 7b. Cowork runtime showcase: the demo signs into Cowork as
#     eppc2026demo2@agent365003.onmicrosoft.com, scoped to the Owner lens
#     (Basic User + lc Owner + lc Owners team, IN the lc Sensitive Readers
#     profile, System Administrator removed) — same shape as the Vivian persona.
#     Mid-demo, remove it from the profile to show the masked read change live.

# 8. See it: the impersonation visualizer (offline demo, then live)
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
