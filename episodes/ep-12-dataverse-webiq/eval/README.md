Ep 12: Live evaluation harness

Purpose

This folder contains a live evaluation set and a small harness to exercise the Episode 12 outside-in agent logic end-to-end using the Web IQ MCP server and (optionally) Dataverse.

Files

- eval_set.jsonl: 20 test cases (one JSON object per line). Mix of live Dataverse-driven cases and sample-only cases.
- run_eval.py: Simple harness that loads each case, reads live blockers from Dataverse when requested, queries Web IQ (web/news), and applies a lightweight heuristic to synthesize a recommendation. The harness compares the heuristic output to the expected recommendation in the eval case and reports pass/fail.

Usage

1. Ensure episodes/ep-12-dataverse-webiq/.env exists and contains WEBIQ_API_KEY, DATAVERSE_URL, TENANT_ID. Select the env with LC_ENV=ep-12-dataverse-webiq.
2. Run: $env:LC_ENV='ep-12-dataverse-webiq'; $env:PYTHONIOENCODING='utf-8'; python .\episodes\ep-12-dataverse-webiq\eval\run_eval.py

Notes & guardrails

- This harness is designed for live testing. It will fail if WEBIQ_API_KEY is not set or the Dataverse env is unreachable.
- The heuristic used in the harness is intentionally simple (keyword-based) and is a sanity check for the agent's data flows; it is not a replacement for human review or a model-based evaluation.
- Do not commit secrets. The .env file is gitignored.
