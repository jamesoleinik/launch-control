# Episode 13: Business Applications in Work IQ: Declarative and Studio agents

> *I can already ask Copilot about the launch. Now I want a focused agent
> that makes the review repeatable, and a supported way to extend it to one
> reviewed update.*

## The hook

In [Episode 12](../ep-12-business-apps-work-iq/README.md), I brought my
business app into Copilot and delegated a reviewed update to Cowork.
People still ask me the same launch question every week, so I give that
review to a focused agent built on the app my team already runs.

Microsoft 365 Agent Builder gives the review a purpose and one selected
business-app source. Copilot Studio extends the experience through the Work
IQ (preview) tool, reuses the same app, and saves one change only after I
review the exact text. The app remains the system of record.

> **Preview note:** Business Applications in Work IQ and Work IQ in Copilot
> Studio are preview capabilities. Work IQ in Studio runs on the GitHub
> Copilot harness and uses Copilot Credits. Verify availability, licensing,
> billing, permissions, and the supported connection before using them.

## The walkthrough: four sections

```text
Section 1  Agent Builder  -> Give the review a purpose and one source
Section 2  Builder answer -> Check the answer against the app
Section 3  Copilot Studio -> Extend the experience with Work IQ (preview)
Section 4  Reviewed write -> Save one approved risk summary and verify it
```

The evidence task remains blocked. The saved risk summary records the risk;
it does not resolve it. Neither agent was published or shared.

## 1. Give the review a purpose

Start with the unpublished **Launch Readiness Checker** draft in Agent
Builder and the [natural-language instructions](natural-language-instructions.txt).
Select **Launch Control Demo** under Dynamics 365 and Power Apps knowledge
and leave the other sources off. The
[instruction template](launch-readiness-agent-instructions.md) is reference
material, not the tested text.

The agent should resolve the named launch, separate risk from an explicitly
blocked task, say what evidence is missing, and cite the records. Instructions
are guidance, not permission controls.

## 2. Make the answer easier to trust

Ask in a fresh Builder preview:

> What is the current status of Q3 Widget Launch, and what is blocking it?

Then open the cited records in the app. The demonstrated answer named the
blocked partner security evidence task and the at-risk certification
milestone, and did not treat missing evidence as approval. A second starter
inspects the underlying work:

> Use the Launch Control Active Tasks view in Launch Control Demo to list the
> tasks for Q3 Widget Launch. Show each task's status, blocked flag, recorded
> blocker reason, assignee, and due date. Cite the source records and identify
> any fields you cannot retrieve.

## 3. Extend the experience in Copilot Studio

Follow the [Studio build guide](studio-build.md). Build a separate agent and
add **Work IQ (preview)** from the MCP tools; do not substitute the legacy
workload tools. Inspect the actual connection, source, and operations. The
selected operations include a write-capable action, so read-only instructions
are not technical enforcement. Configuration from Builder does not carry over.

Ask the same launch question in a new Studio preview chat. The agent
discovered the existing app and answered from fresh records without any
rebuild or reseed.

## 4. Turn evidence into one reviewed update

With the presenter's approval, the Studio instructions allowed exactly one
update: the launch's **Recorded launch risks** field. The agent proposed new
text, showed the current value beside it, and traced each clause to a record.
Work IQ prepares an update and then needs a second confirmation to submit it.
After that confirmation, the agent read the saved text back, and the launch
form showed the new value. The status stayed At risk. A separate read-back
found only the launch row modified, with record counts and the other tables
unchanged.

After recording, the field and the Studio instructions were restored and read
back. The Studio agent remains an unpublished draft.

## Recording notes

The edited walkthrough runs about **2:51**, with four app-first sections
and three takeaways over a moving view of the Work IQ in Copilot Studio
documentation. Waits for agent answers are shortened and labelled on screen;
it is not a response-performance test. Record owner names are blurred. All
data is fictional. Production scripts, trackers, and narration drafts are not
part of this public guide.

### Rehearse and verify

Verify Builder and Studio separately against native app records, not against
each other's answers. Before any write, back up the exact field, approve the
exact target and text, and confirm only that change. Afterwards, verify the
saved value and unchanged record counts, then restore and read back the
baseline. Publication, sharing, connections, schedules, and messages are
separately gated and were not used.

## Existing material

- [Declarative preparation and experiments](declarative-rehearsal.md).
- [Studio rehearsal provenance](studio-rehearsal.md). Historical rehearsals
  are not footage or evidence of this episode.
- [Deferred Foundry IQ storyline](DEFERRED-DRAFT.md), not this build.

The folder keeps its former `ep-13-cowork` name for existing links.

## Cross-references

- [Episode 12: Business Applications in Work IQ](../ep-12-business-apps-work-iq/README.md)
- [Episode 15: Work IQ API and Developer Tools](../ep-15-workiq-api-devtools/README.md)

## Reference documentation

- [Add knowledge to an agent in Agent Builder](https://learn.microsoft.com/microsoft-365/copilot/extensibility/agent-builder-add-knowledge)
- [Work IQ in Copilot Studio (preview)](https://learn.microsoft.com/microsoft-copilot-studio/agents-experience/add-work-iq)
- [Business Applications in Work IQ](https://learn.microsoft.com/power-apps/maker/data-platform/business-applications-work-iq)
