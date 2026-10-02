# Episode 12: Business Apps in Work IQ: Copilot Chat + Agent Builder

> *The launch data is already governed. Can people reach it where they ask
> questions, and can they shape a focused agent around the same approved
> source?*

**Preview:** Verify the Launch Control route in the target tenant before
recording. Copilot Chat and Agent Builder are separate checks. Success in one
surface does not prove access in the other.

## The build: three sections

Each section verifies one part of the experience. Start with product discovery,
confirm the source and permissions, then test a bounded read against its
evidence. Do not claim a route that has not been observed in the target tenant.

```text
Section 1  Product route  -> Confirm the current Chat and Agent Builder surfaces
Section 2  Source access  -> Discover the approved business app and inspect its contract
Section 3  Live proof     -> Compare a bounded answer with source evidence
```

## Section 1: Confirm the product route

Inspect the current Copilot Chat and Agent Builder surfaces in the approved
tenant. Record the visible connection options, identity, audience, and consent
requirements. Treat these as browser-gated checks; a route in another client
does not prove availability here.

### Prompt

> *Inspect the current Copilot Chat and Agent Builder surfaces in the approved
> Launch Control tenant. Identify the visible business-app connection, its
> identity and consent requirements, and any blockers. Verify each surface
> independently. Do not assume a connector or route exists.*

### Result

- The current supported connection options are documented for each surface.
- Identity, permission, and consent boundaries are clear.
- Unsupported, unavailable, or unverified routes are reported as unknown.

### Run it

> *Verify the Chat and Agent Builder connection options in the target tenant.
> Stop and report the blocker if the Launch Control source is not explicitly
> available.*

## Section 2: Verify the business source

Use the current documented Work IQ discovery tool in its authorized host. Begin
with a read-oriented Launch Control status lookup. Inspect the returned
operation schema and confirm its inputs, effects, permissions, and evidence
before calling it.

### Prompt

> *Discover the approved Launch Control business-app route using the documented
> Work IQ discovery operation. Inspect the returned schema and confirm that the
> status lookup is read-only and authorized. Use only returned paths and
> identifiers. Do not invent connectors, API paths, credentials, or business
> facts.*

### Result

- The approved source and a bounded read operation are identified from live
  discovery.
- The operation contract and effects are understood before use.
- If discovery does not return a matching source or the effect is unclear, stop.

### Run it

> *Inspect the live discovery results and operation schema only. Do not invoke
> an operation until its target, permissions, and read-only effect are clear.*

## Section 3: Run the bounded proof

Ask one question about an approved demo launch, such as its current status and
blocking work. Compare each factual answer with the returned source evidence.
Then inspect whether the supported Agent Builder route can use the same
approved source and preserve the read-only boundary.

### Prompt

> *Using only the confirmed read-only source, answer one bounded question about
> the approved demo launch's status and blockers. Show the source evidence for
> each fact. Preview the corresponding Agent Builder experience only if its
> route and permissions were independently confirmed. Do not publish an agent
> or execute a write.*

### Result

- The answer matches the source records, with missing data stated as unknown.
- Agent Builder is evaluated independently and uses only confirmed sources
  and operations.
- No agent is published and no business data is changed.

### Run it

> *Compare the bounded answer with its source records, capture only sanitized
> evidence, and report any mismatch or missing source as a blocker.*

## Pre-record checklist

- [ ] The approved demo environment and account are confirmed.
- [ ] The exact business-app route and operation schema are documented.
- [ ] Copilot Chat and Agent Builder are checked independently.
- [ ] The answer matches source evidence and missing data is labeled.
- [ ] Captures contain no credentials, personal data, or environment identifiers.
- [ ] Publication and all writes remain behind separate approval.

## Supporting material

- [LinkedIn video script](voiceover-script.md)
- [Deferred Web IQ storyline](DEFERRED-DRAFT.md), not part of this episode's
  active demo.
- [Episode 11: Agent Quality Gate](../ep-11-agent-quality-gate/README.md)
- [Episode 13: Cowork](../ep-13-cowork/README.md)
