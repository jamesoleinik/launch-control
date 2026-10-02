# Episode 15 voiceover: Work IQ API + Developer Tools

**Estimated duration:** About 90 seconds
**Spoken word count:** 182

| Shot | Spoken copy |
|---|---|
| Open on current Work IQ developer documentation, then a coding-agent terminal. | A confident answer can still be wrong. Episode fifteen asks two questions: is there a documented Work IQ API for this use case, and can developer tools test a Launch Control assistant with the same questions and evidence? |
| Show an API verification gate, followed by the tool catalog. | We verify the current API contract first. If it is not documented, we do not invent an endpoint. Then we inspect the actual tools in this coding-agent host and confirm the evaluator supports the chosen agent and data path. |
| Show sanitized baseline cases and source evidence. | We run a fixed set of read-only questions and preserve each answer with its source evidence. When a case fails, we identify the cause: routing, tool access, missing evidence, or the answer itself. |
| Show a one-line reviewed change, then rerun the same tests. | If the evidence points to a behavior defect, we propose one small change, review it, and rerun the same suite under comparable conditions. If the environment or evaluator changed, we call the result inconclusive. |
| End on per-case results, not a large score. | We report the cases, the denominator, and any regressions. No cherry-picked score, no claim of automatic learning, and no comparison across different conditions. The developer workflow is useful because it makes uncertainty and change visible. |
