# Episode 13: Business Apps in Work IQ: Cowork

**Status:** Preview. Verify the current Cowork tools and Launch Control connection in the target tenant.
**Season:** Business Apps in Work IQ
**Hero surface:** Cowork
**Result target:** Map the available business-app capabilities, then demonstrate a bounded Launch Control task with an explicit approval boundary.

## The hook

> *"Before we delegate launch work, let's see what the assistant can actually reach, and what still needs a person."*

## Why this matters

An agent's tool list, a metadata description, and a successful business operation are different kinds of evidence. This episode starts with discovery and a metadata-only map. It then tests one read-only Launch Control task. Any proposed mutation is a separate, optional demonstration with an exact human-reviewed change set.

Scheduled work is also a separate capability. A schedule shown in a UI is not proof that it ran, assessed the intended data, or produced a safe result.

## Core demo

Show Cowork's actual Work IQ tools and the discovered Launch Control app using metadata only. Use a read-only task to summarize one approved launch and its open blockers. If demonstrating a write, show the exact proposed records and values first, obtain approval, and verify each saved result by reading it back.

## Prompt for a coding agent

> I want to understand what Cowork can actually access before we demo it. Can you inspect the tools and schemas available in this session, map the capabilities using metadata only, and then help me verify a read-only answer about the approved launch's status and blockers? Please stop if the source or target is unclear. Don't write, schedule, publish, or share anything; if we consider a write demo, show me the exact proposed changes and wait for approval.

## Developer flow

1. **Inspect repo state.** Run `git status --short`; read `AGENTS.md`, this README, the Launch Control data model, and the relevant skills. Preserve user changes.
2. **Check Cowork setup.** In the current Cowork UI, inspect which supported Business Apps or Work IQ capability is enabled. Do not infer that similarly named connectors are interchangeable.
3. **Build a metadata-only map.** Inspect the live tool catalog and schemas. Show only returned tools, apps, tables, and skills. Do not read business records or invoke write tools during this step.
4. **Discover the Launch Control source.** Use the documented discovery operation in the current host. Follow only returned paths and identifiers. Stop if discovery does not identify the approved demo app or a bounded read.
5. **Run one read-only task.** Ask for the approved launch's status and blockers. Compare the answer with the source records and keep any missing fields explicit.
6. **Gate optional writes separately.** Present exact targets, values, and effects. Wait for human approval. After execution, read each target back and check for duplicates. Stop on partial, denied, or ambiguous results.
7. **Treat automation and output sharing as separate gates.** A schedule requires a confirmed connector, owner, cadence, output, and observed run. Inspect generated file location and sharing behavior before capture.
8. **Document only observed behavior.** Label metadata, reads, writes, and schedules separately. Sanitize captures and note the tested product surface and limitations.

## Pre-record checklist

- [ ] Cowork's enabled capability and live tool catalog are confirmed.
- [ ] The metadata map contains only observed information.
- [ ] The read task uses an approved Launch Control demo record and matches its source.
- [ ] Any write has a separate exact proposal, human approval, and verified readback.
- [ ] Schedule execution is claimed only after an assessed run.
- [ ] Generated output and sharing state are checked before recording.

## Deferred storyline

The earlier Foundry IQ story remains in [DEFERRED-DRAFT.md](DEFERRED-DRAFT.md). It is not evidence for the Cowork integration.

## Voice-over

[LinkedIn video script](voiceover-script.md)

## Cross-references

- [Episode 12: Copilot Chat + Agent Builder](../ep-12-copilot-chat-agent-builder/README.md)
- [Episode 14: Copilot Studio](../ep-14-copilot-studio/README.md)
