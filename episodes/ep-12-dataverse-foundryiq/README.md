# Episode 12: Dataverse + Foundry IQ (structured state meets federated knowledge)

**Status:** ✍️ Draft · 🎬 Not yet recorded
**Season:** 2 (Dataverse, Better Together)
**Features:** ⭐ Foundry IQ (managed knowledge grounding over Azure AI Search) · ⭐ Dataverse MCP Server (transactional state) · ⭐ Code-first Python agent (Microsoft Agent Framework) · ⭐ Federated, permission-trimmed retrieval without a hand-built RAG pipeline
**Layer:** 🔵 Layer 2 (skills portability) over a federated knowledge foundation
**Coding agent:** the agent we build IS the artifact (Python)
**Runtime:** Code-first Python agent + Dataverse MCP + Foundry IQ
**Runtime showcased:** the **code-first** pattern (reuses the Season 1 build, archived at `episodes/archive/ep-11-code-first-agent/` and the code at `agents/launch-coordinator-py/`)

---

## The hook

> *"Dataverse holds the facts of this launch. Foundry IQ holds everything written
> about how we launch: the playbooks, the postmortems, the specs, the standards.
> This agent grounds a decision in both, from a few hundred lines of Python."*

The Fabric IQ episode reasoned over the **semantic shape** of structured data.
This one reaches the **unstructured corpus**: the long-form documents that no one
would ever model as rows. Foundry IQ is the managed knowledge system (built on
Azure AI Search) that federates many sources, enforces permissions, and serves
grounded retrieval to an agent through one API. It solves the hardest agent
problem (accurate, permission-aware retrieval) without a hand-rolled RAG pipeline.

## Why this is a complement, not a duplicate (the design rule)

The boundary test, applied to knowledge: *would this content naturally be a row I
query, relate, secure, or transact?*

- **Yes -> Dataverse.** Launch rows, the readiness score, and short codified rules
  (the escalation thresholds). Ground on it with the Dataverse MCP server.
- **No, it is sprawling unstructured prose -> Foundry IQ.** Full PRDs and
  architecture RFCs, the security-review standard, vendor SLA PDFs, long-form
  postmortem narratives, SharePoint document libraries. You retrieve passages, not
  rows.

This is the key distinction from the Season 1 in-Dataverse Knowledge index: that
held a handful of curated articles as Dataverse rows. Foundry IQ is for the corpus
that should **not** be rows. If a document belongs in Dataverse, use Dataverse AI
Search over it; Foundry IQ is for everything that does not.

## The agent: a code-first coordinator that cites its sources

A natural fit for the **code-first** runtime, where the grounding wiring is
explicit and inspectable.

- **Dataverse MCP** supplies the structured facts and the codified rule (a
  >1-week slip needs VP signoff).
- **Foundry IQ** supplies the unstructured evidence behind the judgment: the
  security-review standard that defines a "P1 security blocker," the vendor SLA
  document behind the CDN blocker, the full postmortem write-up.
- The Python agent fuses them and returns a recommendation that cites a Dataverse
  row **and** a Foundry IQ document.

### The headline result

> *"Should we slip Q3 Widget, and what is the precedent?"*

1. **Dataverse** returns live state plus the codified rule: NO-GO, score 38.8, two
   P1 blockers; policy requires VP signoff for a >1-week slip.
2. **Foundry IQ** retrieves the *documents* behind the judgment: the security
   standard defining the P1 severity, and the vendor SLA clause for the CDN
   appliance.
3. **The agent synthesizes:** "NO-GO. Per the Escalation Policy this is a >1-week
   slip requiring VP signoff. The security blocker meets the P1 bar defined in the
   Security Review Standard (cited), and the CDN dependency is governed by the
   vendor SLA (cited). Recommend escalation."

Structured facts and rules from Dataverse; deep reference material from Foundry
IQ. Neither answers well alone, and nothing lives in both places.

## Build steps (outline)

1. Reuse the Python agent shell from `agents/launch-coordinator-py/` (Agent
   Framework, Dataverse MCP over stdio, skills hydrated from Dataverse).
2. Add a Foundry IQ knowledge connection as a tool the agent can retrieve from.
3. Stand up a Foundry IQ knowledge base over a few representative unstructured
   sources (security standard, a vendor SLA PDF, a postmortem doc).
4. Require source citations for every external claim in the agent's output.

## Open questions to resolve before building

- **Access.** Confirm an Azure AI Foundry project with Foundry IQ available, and
  permission to index the sample documents.
- **Attachment path.** How Foundry IQ knowledge bases attach to the agent
  (Agent Framework tool, Azure AI Search connection) at record time.
- **Source set.** Which unstructured documents make the cleanest, least-sensitive
  on-camera corpus (use synthetic/sanitized docs, no real internal material).

## Cross-references

- **`episodes/archive/ep-11-code-first-agent/`** and
  `agents/launch-coordinator-py/`: the code-first runtime this episode reuses.
- **Ep 10:** the Fabric IQ agent (semantic structured data); this is the
  unstructured-knowledge counterpart.
- **Ep 13** (convergence): the Foundry IQ agent runs alongside Web IQ and Fabric
  IQ, with native Copilot, on one launch.
