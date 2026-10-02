# Episode 14: Business Apps in Work IQ: Copilot Studio

**Status:** Preview. The Studio connection and behavior must be verified in the target Launch Control environment.
**Season:** Business Apps in Work IQ
**Hero surface:** Copilot Studio
**Result target:** Create a focused assistant that answers a read-only launch question from an approved business-app source, with evidence and limitations visible.

## The hook

> *"A useful business assistant should show where its answer came from, and stop when the evidence runs out."*

## Why this matters

Copilot Studio is a distinct authoring and runtime surface. A connection available in Chat, Cowork, a coding-agent host, or another tenant does not prove Studio has the same tools, identity, permissions, or behavior.

This episode validates the smallest useful Studio experience first: a bounded read against an approved Launch Control record. Background triggers, schedules, writes, and publication each require separate verification and authorization.

## Core demo

Build or configure a Studio assistant for one approved Launch Control read. Show the source connection, the returned evidence, and an answer that distinguishes a recommendation from a stored business decision. If the source route cannot be verified, present the blocker rather than a simulated answer.

## Prompt for a coding agent

> I want to see whether Copilot Studio can answer a read-only question about an approved Launch Control record. Can you verify the Studio connection in the target tenant, inspect the documented discovery results and operation schema, then compare one answer with its source and check how missing data is handled? If the route isn't confirmed, report the blocker instead of simulating an answer. Keep browser and admin configuration human-gated; don't publish, write, or claim background execution without separate evidence and approval.

## Developer flow

1. **Review the workspace.** Run `git status --short`; read `AGENTS.md`, this README, relevant business-skill instructions, and Launch Control table definitions.
2. **Confirm the source.** A maker verifies current Studio documentation and tenant UI for the supported Work IQ Business Apps connection, identity, permissions, licensing, and consent. Stop if any requirement is unclear.
3. **Discover and inspect.** In the approved Work IQ host, discover the Launch Control app and intended operation. Inspect the exact returned schema and effect. Do not guess a URL, path, or input.
4. **Build the minimal preview.** Use the verified connection and a narrow read-only instruction. Keep credentials out of prompts and committed configuration.
5. **Validate the answer.** Ask one bounded launch question. Compare its facts with source evidence; test missing or denied data and ensure the assistant reports uncertainty honestly.
6. **Gate additional behavior.** Background execution requires a real trigger, run history, and output. A write requires a separately reviewed exact proposal, explicit human approval, per-operation readback, and duplicate checks. Publication requires its own approval.
7. **Capture and document.** Record only observed setup steps and sanitized results. Do not imply another Copilot surface or tenant was tested.

## Pre-record checklist

- [ ] Current Studio connection route, identity, and required permissions are confirmed.
- [ ] The operation schema and read-only effect are verified.
- [ ] The answer matches the source, including an honest missing-data result.
- [ ] Background behavior, writes, and publication are either separately verified or clearly excluded.
- [ ] Captures are sanitized and use approved demo data.

## Deferred storyline

The earlier Convergence story remains preserved in [DEFERRED-DRAFT.md](DEFERRED-DRAFT.md). Its material does not establish this Studio integration.

## Voice-over

[LinkedIn video script](voiceover-script.md)

## Cross-references

- [Episode 13: Cowork](../ep-13-cowork/README.md)
- [Episode 15: Developer Tools](../ep-15-workiq-api-devtools/README.md)
