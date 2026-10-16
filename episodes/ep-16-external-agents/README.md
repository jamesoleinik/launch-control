# Episode 16: Business Apps in Work IQ: External Agents

**Status:** Preview. No general external-agent connection is assumed.
**Season:** Business Apps in Work IQ
**Hero surface:** An approved external agent, such as ChatGPT, if a supported route is available
**Result target:** Verify one documented, permission-scoped, read-only path to Launch Control data and show its source evidence.

## The hook

> *"Can an agent outside the Microsoft experience use business context without weakening the identity and permission boundary?"*

## Why this matters

External-agent support depends on the exact product, tenant, connection method, identity, and data policy. A successful setup in one client does not prove that other agents can connect or reuse its sign-in. A Work IQ tool path is not automatically a public endpoint.

This episode is an evidence-led compatibility test. If the approved product documentation does not establish a supported connection, the correct result is a documented blocker. Do not build a proxy, share credentials, or simulate a successful connection.

## Core demo

Choose one approved external-agent product and version. Verify its documented Work IQ or business-app connection path, authentication, permissions, data handling, and audit behavior. If all gates pass, run one read-only Launch Control question and compare the response with its source.

## Prompt for a coding agent

> I want to check whether [external agent and version] can safely answer a read-only question using approved Launch Control data. Can you verify its documented connection method, identity, permissions, consent, data handling, and audit requirements before any configuration? If the supported route isn't documented or any requirement is unclear, tell me what's missing and stop. Don't invent endpoints or capabilities, share credentials, or build a proxy. If all the gates are confirmed, help me run one read-only test and compare the answer with its source.

## Developer flow

1. **Set scope.** Run `git status --short`; read `AGENTS.md`, this README, and the relevant Launch Control data and security guidance.
2. **Name the target.** Record the exact external product and version, approved tenant, intended user scenario, and data scope in a private test plan. Do not put tenant URLs, identities, or real records in the repository.
3. **Verify authoritative documentation.** Confirm the supported connection method, endpoint or protocol if documented, authentication, permissions, consent, data retention, and audit behavior. If any are unknown, stop.
4. **Discover the business capability.** In the approved Work IQ host, discover the Launch Control operation and inspect its returned schema. A host-specific operation does not prove external compatibility.
5. **Review security and approval.** Have the tenant owner approve the exact identity, scope, sample data, and client. Never copy a token or broaden access to make a demo work.
6. **Run one read-only test.** Use an approved demo record, compare every factual response with its source, and confirm no writes or external messages occurred.
7. **Document the result.** Capture sanitized evidence and label the exact product and configuration tested. Do not generalize to other agents or tenants.

## Stop conditions

- The exact external product, version, tenant, or intended identity is unclear.
- Official documentation does not describe the external caller path.
- Authentication, permissions, consent, data handling, or audit requirements are unresolved.
- The business-app operation or its read-only effect cannot be verified.
- The proposed workaround requires shared credentials, a guessed endpoint, or an unapproved write.

## Deferred storyline

The earlier Full Orchestra finale remains in [DEFERRED-DRAFT.md](DEFERRED-DRAFT.md). Its scripts do not verify external-agent compatibility.

## Voice-over

[LinkedIn video script](voiceover-script.md)

## Cross-references

- [Episode 15: Developer Tools](../ep-15-workiq-api-devtools/README.md)
- [Episode 12: Copilot Chat and Cowork](../ep-12-copilot-chat-agent-builder/README.md)
