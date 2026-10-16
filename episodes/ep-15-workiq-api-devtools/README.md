# Episode 15: Business Apps in Work IQ: Work IQ API + Developer Tools

**Status:** Preview. Verify the current Work IQ developer tools and evaluator support before running an experiment.
**Season:** Business Apps in Work IQ
**Hero surface:** Work IQ API discovery, coding-agent tools, and repeatable evaluation
**Result target:** Verify the supported developer access contract, then measure a fixed set of Launch Control questions and compare a reviewed change under stable conditions.

## The hook

> *"One good answer is a demo. A repeatable evaluation helps us understand whether the next change actually helped."*

## Why this matters

Developer tools can make agent behavior easier to inspect and evaluate, but a tool catalog is not proof of a supported public API or SDK. This episode verifies whether a documented Work IQ API exists for the selected scenario, then checks the tools available in the chosen coding-agent host and whether its evaluator supports the exact agent and business-data path.

The experiment must keep the target, data, instructions, evaluator, rubric, and concurrency stable. A changed environment, client, or evidence set invalidates a direct comparison. Do not make a quality-improvement claim from an unpaired or unstable run.

## Core demo

Run a fixed, sanitized test set against a Launch Control assistant. Save a private baseline, categorize failures, propose one minimal change for a verified behavior defect, and rerun the same tests under comparable conditions. Report per-case outcomes and limitations, not just a headline score.

## Prompt for a coding agent

> I want to know whether a documented Work IQ API supports our scenario and whether this coding-agent evaluator can test the selected agent and business-data path. Can you verify those contracts and compatibility first? If supported, help me run a fixed baseline of approved read-only questions, keep the per-case results private, and identify a behavior defect only when the evidence supports one. Show me the smallest proposed change and wait for approval before applying it. Then rerun the same tests under comparable conditions, and don't claim improvement unless the comparison is controlled.

## Developer flow

1. **Inspect repository and host.** Run `git status --short`; read `AGENTS.md`, this README, and current product and evaluation documentation. Inspect the actual installed tool catalog instead of assuming a command or plugin is available.
2. **Verify API status.** Confirm from current authoritative documentation whether a supported Work IQ API exists for this use case. Record its documented host, version, authentication, and operation only when confirmed. If the API is not documented or accessible, stop that integration path without inventing an endpoint.
3. **Confirm evaluator compatibility.** Verify the evaluator supports the chosen agent, client, model, business-data source, and result format. Stop if the contract or data access is unclear.
4. **Define the test set.** Use a small, approved set of read-only Launch Control questions with expected source evidence. Keep private records and responses out of committed fixtures.
5. **Freeze the baseline.** Record the agent version, instructions, tools, data snapshot, evaluator, rubric, and concurrency in an approved private location. Preserve each response and its evidence.
6. **Classify failures.** Separate routing, tool, evaluator, citation, and answer-quality issues. Do not treat a test harness artifact as an agent defect.
7. **Review one change.** Propose the smallest instruction or configuration change supported by a specific failure. Obtain approval and verify the saved version. Make no change if the root cause is not clear.
8. **Run a paired comparison.** Rerun the same tests with all other conditions held constant. Compare per-case responses, evidence, scores, and regressions.
9. **Report accurately.** State the denominator, run conditions, and limitations. If conditions drift or results vary, report the experiment as inconclusive.

## Pre-record checklist

- [ ] The existence and contract of any Work IQ API are confirmed or the API path is explicitly marked unavailable.
- [ ] Tool and evaluator instructions are current and available in the chosen host.
- [ ] Compatibility with the selected agent and business-data path is confirmed.
- [ ] Test cases use approved, sanitized data and explicit expected evidence.
- [ ] Baseline and rerun use the same target, rubric, evaluator, and conditions.
- [ ] Any change is reviewed, isolated, and verified.
- [ ] Results are reported per case, with no unsupported improvement claim.

## Deferred storyline

The earlier Agentic Administration story and its scripts remain in [DEFERRED-DRAFT.md](DEFERRED-DRAFT.md). They are separate from this evaluation episode.

## Voice-over

[LinkedIn video script](voiceover-script.md)

## Cross-references

- [Episode 13: Declarative and Studio agents](../ep-13-cowork/README.md)
- [Episode 16: External Agents](../ep-16-external-agents/README.md)
