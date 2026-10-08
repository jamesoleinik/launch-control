# Episode 12: Business Apps in Work IQ: Enablement + Declarative Agent

> *Our launch data already lives in a business app. How do I make it useful
> in Microsoft 365 Copilot without building a separate agent runtime?*

**Status:** Tenant audience, environment enablement, and the published app
are verified. The approved app setting is saved as On, and its M365 search
model is now active. Agent Builder still does not discover the app.
The semantic model reports failed generation for `lc_launch`; a supported
regeneration has been started. A successful generation, declarative-agent
answer, and replacement recording remain unverified.
**Season:** Business Apps in Work IQ
**Hero surfaces:** Microsoft 365 admin center, Power Platform admin center,
Launch Control, and Agent Builder in Microsoft 365 Copilot.
**Result target:** Enable the environment and app indexing, select the app
as business knowledge, and ask a focused declarative agent for launch evidence.

## The arc

```text
Enable the pilot and environment
  -> Enable app indexing and select the app as knowledge
  -> Configure a declarative agent in Microsoft 365 Copilot
  -> Ask one launch question and compare the source
  -> Explain when to choose Copilot Studio in Episode 14
```

This is an agent episode, not a workflow episode. The core demonstration is
read-only. No follow-up writes, schedules, custom MCP tools, or Studio build
are needed. Keep the social video under two minutes by showing one question,
not by speeding up its response.

## Declarative agent now, Copilot Studio later

| Question | Episode 12 | Episode 14 |
|---|---|---|
| What do we build? | A focused declarative agent in Agent Builder | A Studio agent with an explicitly verified source/tool configuration |
| Who handles orchestration here? | Microsoft 365 Copilot's orchestrator, models, and services | The configured Studio experience, verified separately |
| Why choose it? | Repeatable business questions inside Microsoft 365 Copilot | More control over integrations, multi-step logic, deployment, and lifecycle |
| What does this episode prove? | Selected business-app knowledge and a source-matched answer | Studio-specific connection and behavior, not inherited proof from Episode 12 |

These are experience and configuration choices, not a claim that a portal
name alone determines agent type. Declarative agents can have capabilities
beyond this episode's knowledge-only configuration. Studio can also support
simple Q&A. Additional controls and deployment options are reasons to choose
Studio, not behaviors demonstrated merely by opening its editor.

See Microsoft's [Agent Builder and Copilot Studio comparison](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/copilot-studio-experience).

## 1. Enable Business Applications in Work IQ

Follow the [pilot quickstart](https://learn.microsoft.com/en-us/power-platform/admin/business-applications-work-iq/quickstart).
Confirm the pilot account, model-driven app, appropriate administrative roles,
licensing, consent, and any usage-based billing before changing settings.
Use the isolated demo environment, not a production environment.

1. In **Microsoft 365 admin center > Copilot > Settings**, open
   **Business Applications in Work IQ available to Copilot**. Confirm that
   the intended pilot users are included. Do not broaden the audience for
   filming. Save only approved changes.
2. In **Power Platform admin center > Manage**, select the environment,
   then **Settings > Product > Features**. Turn on **Work IQ** if needed.
   The earlier sandbox UI labeled it **Turn on Business Applications in
   Work IQ**. Save only if changed.
3. If already enabled, show and explain the existing setting. Do not turn
   it off and back on to manufacture enablement footage.

The environment was already enabled with the user's approval. The current
tenant audience includes All users; leave that existing scope unchanged.
Neither setting proves the declarative agent can discover this app. Recheck
the intended user's access in the new rehearsal.

## 2. Enable the app and include it as knowledge

The app in this episode is **Launch Control Demo**, with the fictional
**Q3 Widget Launch** identified by `EP12-DEMO-01`. The model-driven app spec
is [`launch-control-app.json`](launch-control-app.json).

Verify the published app, its Launch form and view, and the pilot user's
access. The app's table component must resolve to `lc_launch`, not the generic
`entity` component. That mapping was repaired and verified previously.
The custom PCF **Activity** view shows saved status updates; the standard
Dataverse timeline is not a substitute for those records.

Before selecting knowledge, follow the supported
[app-level M365 Copilot setting](https://learn.microsoft.com/en-us/power-apps/maker/model-driven-apps/add-microsoft-365-copilot#enable-microsoft-365-copilot-in-a-single-model-driven-app):

1. Open **Launch Control Demo** for editing in Power Apps.
2. Open **Settings > Features > Enable M365 Copilot in model-driven apps**.
   The live setting explains that enabling it supplies in-app chat and starts
   indexing app data for queries from Microsoft 365 Copilot experiences.
3. After approval, set this app to **On**, save the setting, and save/publish
   the app. Do not enable every app or change unrelated settings.
4. Reopen the setting and verify persistence, then check discovery in Agent
   Builder. Saving the app is not proof that indexing or discovery is ready.

The app was previously set to **Default**, with an inactive
`M365_Primary_model` search definition. After the approved change and
publication, the setting persists as **On** and the model is **Active**.
This fixed model activation, but did not immediately fix app discovery.
Use the supported setting rather than directly activating a search-model row.

If discovery still fails, inspect **Power Apps > Semantic models (preview)**
and open the model associated with the app. Its **Configuration** page must
contain the intended table, not the generic Entity table. In this rehearsal,
`lc_launch` is present but reports that semantic data could not be generated.
The supported [Regenerate command](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/regenerate-semantic-model)
starts a queued job; it does not establish successful generation. Note that
this command runs across semantic models in the environment, not just the
model being viewed. Confirm the scope before using it, do not repeatedly
submit while it is running, and verify the updated timestamp and generated
content afterward. Microsoft documents initial generation as taking up to
two hours and incremental changes as typically taking up to 30 minutes in
the [semantic model overview](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/semantic-model-overview).
Those are generation timings, not a guarantee of Agent Builder discovery.

In Agent Builder, include the intended app in **Dynamics 365 and Power Apps
data** knowledge. This selection is separate from enabling app indexing.
Microsoft documents that omitting an explicit app selection queries all apps
the user can access. Do not leave that broad default in this demo.

App selection is not a new permission grant. Dataverse security still governs
access. The current app spec includes only `lc_launch`; rendering related data
in a PCF does not prove the agent can retrieve those related tables.
Verify milestone, task, and update access through the selected knowledge route
before promising a blocker summary. If required records are unavailable,
stop and review the app's data scope rather than silently querying every app.

### Not the same as App MCP

Power Apps also documents a separate [App MCP and generated declarative-agent package](https://learn.microsoft.com/en-us/power-apps/maker/model-driven-apps/enable-your-app-copilot)
route: **App MCP > Set up MCP**, save/publish the app, download the generated
package, and deploy it through Teams or Microsoft 365 administration.
It can expose interactive grids and forms, including write-capable forms.

That route is **not required for this episode's Agent Builder knowledge
configuration**. Do not describe it as the Work IQ MCP server or silently
substitute it for the chosen route. Using it would require a separately
reviewed configuration, deployment, and demo scope. The M365 Copilot app
setting above also enables embedded chat, but merely opening that chat pane
does not configure or verify the declarative agent.

## 3. Configure the declarative agent

Use the documented [Agent Builder knowledge route](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/agent-builder-add-knowledge#dynamics-365-and-power-apps-data).
The product documentation confirms this capability; it does not prove that
the target tenant has the same UI or that this app is discoverable there.

1. In **Microsoft 365 Copilot**, choose **New agent**, then
   **Skip to configure**. Name it **Launch Readiness Checker**.
2. Add the relevant Dynamics 365 and Power Apps knowledge and explicitly
   select **Launch Control Demo**. Verify the selected app in **Knowledge**.
   If the option or app is absent, capture the blocker and stop.
3. Use [`launch-readiness-agent-instructions.md`](launch-readiness-agent-instructions.md).
   These instructions use business knowledge, not Studio MCP tool names,
   SQL snippets, or fixed environment identifiers.
4. Exclude unrelated web, file, email, Teams, and people sources. Turn on
   **Only use specified sources** if available. This prioritizes configured
   sources; it does not block all general AI knowledge or enforce row security.
5. Test on **Try it**. Keep sharing and publication separate. If showing a
   saved agent outside Try it, first confirm and approve its intended
   audience, save it, reopen it, and repeat the test in that exact surface.

Microsoft documents Dataverse **knowledge** as read access without create,
update, or delete capabilities. This is different from the old Studio
rehearsal's `do_action` tool, which could also invoke mutations. Do not copy
that MCP tool configuration into this episode or claim instructions enforce
a technical read-only policy.

## 4. Rehearse and record the result

Start with the app and a fresh declarative-agent conversation. Ask:

> What's the current status, and what is blocking it?

The instructions identify the prepared launch. Use the broader catch-up and
readiness questions as off-camera checks, not extra mandatory video beats:

- "Catch me up on the Q3 Widget Launch."
- "Is the Q3 Widget Launch ready to launch?"

Compare the answer with current source records. An empty gate verdict means
**no recorded verdict**, not approval and not proof that a review never ran.
Do not paste the expected answer or old Studio transcript into the agent.
Test a missing-record question and verify that it does not invent evidence.

Close with the same source record and a brief comparison: this declarative
agent extends Microsoft 365 Copilot; Episode 14 explores Studio's additional
configuration and control. Do not present a second Studio build here.

Use [`demo-arc.md`](demo-arc.md) for the shot list, acceptance criteria, and
capture boundaries. The [narration](voiceover-script.md) and
[LinkedIn script](linkedin-voiceover-script.md) are provisional until new
footage supplies measured cue times.

## Developer setup

For a new authorized sandbox, review the target in the ignored root `.env`.
Preview each change before applying it. Existing prepared environments do not
need to be rebuilt or reseeded for a read-only take.

```powershell
$env:PYTHONIOENCODING = "utf-8"
npm run build --prefix apps\launch-readiness-control
python scripts\build_launchcontrol_schema.py --scope unified --with-lookups --dry-run
python scripts\python\seed_ep12_demo.py --dry-run
python .github\skills\dataverse-model-driven-app-builder\scripts\model_app_builder.py `
  --spec episodes\ep-12-copilot-chat-agent-builder\launch-control-app.json --dry-run
```

After approval, the schema command without `--dry-run`, seed `--apply`, and
app builder `--apply` provision the reviewed changes. Use the
`dataverse-model-driven-app-builder` and `dataverse-pcf-deployer` skills for
app/form deployment. Do not use broad seed or cleanup scripts. These helpers
do not enable Work IQ or create a Microsoft 365 declarative agent.

### Prompt for a coding agent

> Prepare Episode 12 around Business Applications in Work IQ enablement and
> a declarative Launch Readiness Checker in Microsoft 365 Copilot. Inspect the
> existing app and scoped demo data. Verify the pilot and environment settings
> without toggling already-enabled settings. Verify the app's M365 Copilot
> indexing setting; obtain approval before changing and publishing it.
> In Agent Builder, use Dynamics
> 365 and Power Apps knowledge with the intended app selected explicitly.
> Test one read-only answer and a missing-data case against source records.
> Report unavailable options or related tables instead of substituting Studio,
> a workflow, direct Dataverse MCP, or App MCP. Keep publication and sharing
> separately approved. Record only the experience actually verified.

## Existing footage and series links

The existing **6:06 full recording** and **1:37 excerpt** show an unpublished
Copilot Studio draft using Work IQ MCP. They are **superseded for Episode 12**,
not declarative-agent evidence. Their original private videos, subtitles,
and Library ZIP remain unchanged. Their
[provenance and timed scripts](../ep-14-copilot-studio/studio-rehearsal.md)
are retained as Episode 14 reference material, not a completed Episode 14.

- [Episode 11: Agent Quality Gate](../ep-11-agent-quality-gate/README.md)
- [Episode 13: Cowork](../ep-13-cowork/README.md)
- [Episode 14: Copilot Studio](../ep-14-copilot-studio/README.md)
- [Deferred Web IQ storyline](DEFERRED-DRAFT.md), not the active build.
