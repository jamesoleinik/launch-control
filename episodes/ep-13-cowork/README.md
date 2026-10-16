# Episode 13: Business Applications in Work IQ: Declarative and Studio agents

> *I can already ask Copilot about the launch. Now I want a focused agent
> that makes the job repeatable, and a controlled way to extend it.*

**Status:** Planned combined agent episode. Historical Builder and Studio
rehearsals exist, but both configurations need fresh validation. No new
agent build, deployment, or recording is claimed by this revision.

**Season:** Business Apps in Work IQ

**Hero surfaces:** Microsoft 365 declarative-agent authoring and Copilot Studio.

**Result target:** Extend Episode 12's same launch scenario with a focused
declarative agent and a separately verified Studio flow.

The folder retains its former `ep-13-cowork` name for existing links.
Direct Cowork usage has moved into
[Episode 12](../ep-12-copilot-chat-agent-builder/README.md).

## The progression

| Experience | What this episode adds | What must be demonstrated |
|---|---|---|
| Episode 12 baseline | Direct Chat questions and a Cowork follow-up using the built-in Business apps (preview) plugin | Existing app evidence, separate access checks, source comparison |
| Declarative agent | A repeatable Launch Readiness Checker with purpose, instructions, starters, and scoped business-app knowledge | Actual selected source, fresh answer, honest missing-data behavior |
| Copilot Studio agent | An explicitly configured retrieval and follow-up experience with more control over the steps and integrations | Actual connection, operation scope, evidence-backed proposal, and stop before any unapproved action |

Reuse Launch Control Demo, Q3 Widget Launch, native forms/views, and glossary
from Episode 12. Do not rebuild or reseed the app to manufacture new footage.
The launch's risk and missing approval evidence remain facts, not problems to
hide by forcing a green result.

## 1. Build the focused declarative agent

Start with the existing unpublished **Launch Readiness Checker** draft and
the exact [natural-language instructions](natural-language-instructions.txt)
used in the prior successful rehearsal. The
[instruction template](launch-readiness-agent-instructions.md) is separate
reference material, not a claim that it was tested in place of that text.

The agent should resolve the named launch, retrieve current source evidence,
distinguish risk from an explicitly blocked task, identify missing information,
and return record links. It should not invent approval, change data, or use
unrelated sources to fill gaps. Instructions are not permission controls.

### Authoring options

- **Microsoft 365 Agent Builder:** Configure instructions and explicitly
  select Launch Control Demo under Dynamics 365 and Power Apps knowledge.
  This is the route used by the existing draft.
- **GitHub Copilot with Work IQ Dev Tools and the Dataverse coding plugin:**
  The coding plugin can guide app/data preparation; Work IQ Dev Tools can
  author and validate a declarative-agent package. It is not automatically
  equivalent to the selected-app knowledge configuration in Builder.

The prior read-only check found Work IQ Dev Tools 0.16.0 installed, without its
Copilot plugin. Its documented Dataverse configuration uses a generated
knowledge binding obtained through a Studio export. Support for reproducing
the tested selected-app/semantic-model route is still unverified. This is
an Episode 13 authoring question, no longer an Episode 12 recording blocker.
Do not invent identifiers or substitute generic MCP, App MCP, or a different
runtime and call it the same configuration.

If the developer path is verified, it can be the build demonstration with
Builder as the visual alternative. Otherwise keep the known Builder route
and obtain a scope decision before promising developer-path parity.
Provisioning, audience selection, publishing, and sharing need explicit approval.

## 2. Extend the scenario in Copilot Studio

Follow the [Studio build guide](studio-build.md). Inspect the supported
source connection, identity, operation schemas, and permission boundaries.
Do not assume Chat, Cowork, or Builder configuration transfers unchanged.

The proposed extension is a bounded sequence: retrieve the approved launch
and blocked tasks, summarize the evidence, then draft follow-up work for review.
Start read-only. A draft plan is not a created task or sent message.
Any later write requires exact target/value approval and readback; background
execution requires a real trigger and observed run history. Neither is
automatically in scope because Studio supports it.

## Shared test and comparison

Ask both configurations:

> What is the current status of Q3 Widget Launch, and what is blocking it?

Then inspect the underlying work:

> Use the Episode 12 Active Tasks view in Launch Control Demo to list the tasks
> for Q3 Widget Launch. Show each task's status, blocked flag, recorded blocker
> reason, assignee, and due date. Cite the source records and identify any
> fields you cannot retrieve.

For the Studio extension:

> Based on fresh Launch Control Demo records, draft a follow-up plan for the
> blocked work. Identify the recorded assignee and reason, cite the source
> records, and flag missing evidence. Do not save changes or send anything.

Use fresh conversations and compare with the source separately. Test a
nonexistent launch and an attempted source override. Do not label those
checks as row-level permission-denial tests. Preserve actual limitations
instead of treating one answer as a reliability guarantee.

## Pre-record checklist

- [ ] Intended environment, app, identity, and source access are verified.
- [ ] The declarative agent's actual knowledge configuration is confirmed.
- [ ] Any developer-path equivalence claim has its own evidence.
- [ ] Studio's actual connection and operation effects are verified.
- [ ] Both fresh answers match source records and handle missing data honestly.
- [ ] The follow-up is clearly a proposal unless separately approved and saved.
- [ ] Publication, writes, schedules, and sharing are separately gated.
- [ ] Neutral roles, recording surfaces, and per-run reset/readback are ready.

## Existing material

- [Declarative preparation and experiments](declarative-rehearsal.md).
- [Studio rehearsal provenance](studio-rehearsal.md), with original timed
  scripts and instructions. Preserve old media unchanged; it is not footage
  of direct Chat/Cowork or a completed new Episode 13.
- [Combined episode narration draft](voiceover-script.md) and
  [Studio segment reference](studio-voiceover.md).
- [Deferred Foundry IQ storyline](DEFERRED-DRAFT.md), not this build.

## Cross-references

- [Episode 12: Copilot Chat and Cowork](../ep-12-copilot-chat-agent-builder/README.md)
- [Episode 15: Work IQ API and Developer Tools](../ep-15-workiq-api-devtools/README.md)
