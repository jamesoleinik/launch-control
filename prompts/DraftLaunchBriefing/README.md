# lc_DraftLaunchBriefing

The non-deterministic surface from Episode 5, Part 4. A Dataverse AI Prompt
that reads the milestone narrative for a launch and writes a three-sentence
GO / HOLD / NO-GO recommendation in the executive sponsor's voice.

## Files

| File | What it is |
|---|---|
| `prompt.json` | The `msdyn_customconfiguration` payload — prompt body, grounded tables, model + temperature. Source of truth. |

## Shape on Dataverse

An "AI Prompt" in Dataverse is two linked records:

| Table | Role |
|---|---|
| `msdyn_aimodel` | Identity — name, template binding (`GptPowerPrompt`), pointer to the active run configuration. This is the row that gets added to the solution. |
| `msdyn_aiconfiguration` | The prompt body (`msdyn_customconfiguration`), model parameters, output schema. Linked back to the aimodel via `_msdyn_aimodelid_value`. The model has both a Training row (type `190690000`) and an active Run row (type `190690001`). |

Re-running `scripts/register_ai_prompt.py` is idempotent — it upserts the
aimodel by `msdyn_name`, calls the unbound `AIModelPublish` action with
`Source="AIBuilder"` (which is what flips `statecode=1` AND sets
`msdyn_activerunconfigurationid` in one shot), and tags the model into
the `LaunchControl` solution via the `MSCRM.SolutionUniqueName` request
header.

## Grounding model

This prompt **does not declare runtime input parameters** in
`definitions.inputs`. The `GptDynamicPrompt-2` template in our environment
treats inputs as a maker-time-only construct — supplying them prevents the
publish action from flipping the model to Published. Instead, the prompt is
grounded on two tables and lets the calling surface inject the launch
context:

| Grounded table | Why |
|---|---|
| `lc_launch` | Source of the launch name + sponsor field. The prompt reasons over `lc_name` to pick which launch to brief. |
| `lc_milestone` | Source of the narrative. The prompt filters milestones to the launch under review and pulls the GO/HOLD/NO-GO signal from `lc_status` + `lc_narrative`. |

The maker portal's "Test prompt" surface filters these tables for you;
Power Automate's "Create text with GPT using a prompt" action lets the
caller pass a row reference or a pre-filtered table.

## Invocation surfaces

This is the most important architectural shift in Part 4: **AI Prompts are
not invoked via the bound `Predict` action over raw REST.** That path
exists in `$metadata` but requires AI Builder capacity context that the
first-party surfaces inject for you. The supported invocation paths are:

| Surface | How it calls the prompt |
|---|---|
| Power Apps Maker Portal | "Test prompt" button on the AI Hub > Prompts > `lc_DraftLaunchBriefing` page. This is the smoke test. |
| Power Automate flow | "Create text with GPT using a prompt" action — pick `lc_DraftLaunchBriefing` from the dropdown. |
| Copilot Studio | Add as a prompt skill / topic action. |
| Power Fx | `Prompt('lc_DraftLaunchBriefing'.Predict, ...)` — the Power Fx runtime wraps the AI Builder capacity handshake. |

For the test-harness flow in Part 5, the appropriate action is **Create
text with GPT using a prompt** (AI Builder connector) — not an HTTP call to
the bound `Predict` action.

## Iteration notes

- **Three sentences** is a hard constraint in the prompt body — if the
  model drifts, tighten with "Exactly three sentences. No more, no less."
- **Temperature 0.3** keeps the wording stable enough to demo while
  still showing run-to-run variation (vs the deterministic Custom APIs).
- Both `lc_launch` and `lc_milestone` are grounded — the prompt reads the
  launch name from `lc_launch.lc_name` and the milestone narrative from
  `lc_milestone.lc_narrative`. Filtering ("focus on the launch under
  review") is done in the prompt text itself.
- Model `gpt-41-mini` is licensed by default in most AI-Builder-enabled
  environments. If the call returns "no AI Builder capacity", swap to a
  smaller / cheaper model in `prompt.json` and re-register.

