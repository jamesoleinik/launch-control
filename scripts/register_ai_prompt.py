"""Register (idempotently) a Dataverse AI Prompt from a JSON definition.

A Dataverse "AI Prompt" is two linked rows -- msdyn_aimodel (identity) and
msdyn_aiconfiguration (the prompt body). The maker portal stitches them
together via the unbound action `AIModelPublish`, which is what this script
uses. With Source="AIBuilder" the action both creates the run config AND
flips msdyn_activerunconfigurationid on the model + sets statecode=1 (the
combination that makes the prompt Published and callable at runtime).

After publish:
  - The prompt shows up under Power Apps > AI Hub > Prompts.
  - It can be invoked from the maker portal's "Test prompt" button, from
    a Power Automate "Create text with GPT using a prompt" action, or from
    Copilot Studio as a prompt skill -- the same first-party surfaces every
    other AI Builder prompt uses. Runtime REST invocation (`Predict` bound
    action) requires AI Builder capacity context that the maker-portal
    surfaces inject for you; this script does not attempt that path.

Usage:
    python scripts/register_ai_prompt.py prompts/DraftLaunchBriefing
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import requests
from auth import get_token

# The built-in 'GptPowerPrompt' template every AI Builder prompt is grounded in.
GPT_POWER_PROMPT_TEMPLATE_ID = "edfdb190-3791-45d8-9a6c-8f90a37c278a"
SOLUTION_NAME = "LaunchControl"
SMOKE_TEST_LAUNCH = "Q3 Widget Launch"


def api(base: str, token: str) -> dict:
    return {
        "url": base.rstrip("/") + "/api/data/v9.2",
        "headers": {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Content-Type": "application/json",
        },
    }


def find_aimodel(ctx: dict, name: str) -> str | None:
    r = requests.get(
        f"{ctx['url']}/msdyn_aimodels",
        headers=ctx["headers"],
        params={"$filter": f"msdyn_name eq '{name}'", "$select": "msdyn_aimodelid"},
    )
    r.raise_for_status()
    vals = r.json().get("value", [])
    return vals[0]["msdyn_aimodelid"] if vals else None


def publish_prompt(ctx: dict, model_id: str, run_config_id: str, model_name: str, custom_config: dict) -> dict:
    """Single unbound action that creates/updates aimodel + aiconfiguration and
    flips msdyn_activerunconfigurationid in one shot."""
    config_str = json.dumps(custom_config, separators=(",", ":"))
    body = {
        "ModelId": model_id,
        "ModelName": model_name,
        "TemplateId": GPT_POWER_PROMPT_TEMPLATE_ID,
        "RunConfigurationId": run_config_id,
        "CustomConfiguration": config_str,
        "RunConfiguration": config_str,
        # Source="AIBuilder" is what flips statecode=1 AND sets
        # msdyn_activerunconfigurationid on the model in one shot. With
        # Source="PowerPlatform" the model stays Draft and Predict refuses
        # to run with "UnPublishedModel".
        "Source": "AIBuilder",
    }
    headers = dict(ctx["headers"])
    headers["MSCRM.SolutionUniqueName"] = SOLUTION_NAME
    r = requests.post(f"{ctx['url']}/AIModelPublish", headers=headers, json=body)
    if not r.ok:
        raise RuntimeError(f"AIModelPublish failed: {r.status_code} {r.text}")
    return r.json()


def add_to_solution(ctx: dict, aimodel_id: str) -> None:
    """No-op placeholder. AIModelPublish honours the MSCRM.SolutionUniqueName
    request header and places the aimodel + aiconfiguration rows into that
    solution itself, so an explicit AddSolutionComponent call is unnecessary
    (and the ComponentType code for AI Model is not publicly documented --
    422 / 9603 both return 'Invalid component type')."""
    return


def smoke_test(ctx: dict, aimodel_id: str, launch_name: str) -> None:
    """Print the maker-portal Test URL.

    Runtime REST invocation (the bound `Predict` action on msdyn_aimodel)
    requires AI Builder capacity context that we have not been able to
    reproduce outside the first-party surfaces (maker portal / Power
    Automate prompt action / Copilot Studio prompt skill). Predict over
    raw REST returns 'Source is null' even on prompts known-good in the
    portal. Treat the maker portal Test button as the smoke test.
    """
    base = ctx["url"].rsplit("/api/", 1)[0]
    print(f"  Smoke test (manual): open the prompt in Power Apps Maker Portal")
    print(f"    https://make.powerapps.com  ->  ... AI Hub  ->  Prompts  ->  lc_DraftLaunchBriefing")
    print(f'    Click "Test prompt", set LaunchName = "{launch_name}", and verify the GO/HOLD/NO-GO output.')


def main(prompt_dir: Path) -> int:
    base = os.environ["DATAVERSE_URL"]
    token = get_token()
    ctx = api(base, token)

    prompt_json = json.loads((prompt_dir / "prompt.json").read_text(encoding="utf-8"))
    prompt_name = prompt_dir.name  # "DraftLaunchBriefing"
    aimodel_name = f"lc_{prompt_name}"

    print(f"=== Registering AI Prompt: {aimodel_name} ===")
    print(f"  Env:      {base}")
    print(f"  Solution: {SOLUTION_NAME}")

    existing_id = find_aimodel(ctx, aimodel_name)
    model_id = existing_id or str(uuid.uuid4())
    run_config_id = str(uuid.uuid4())  # new run config every publish

    if existing_id:
        print(f"  Found existing aimodel: {model_id} -- publishing new run config")
    else:
        print(f"  Allocating new aimodel id: {model_id}")

    print("  Calling AIModelPublish ...")
    publish_prompt(ctx, model_id, run_config_id, aimodel_name, prompt_json)
    print(f"  Published. RunConfigurationId={run_config_id}")

    print(f"  Adding aimodel to '{SOLUTION_NAME}' solution ...")
    add_to_solution(ctx, model_id)

    print()
    print(f"=== Smoke test for LaunchName='{SMOKE_TEST_LAUNCH}' ===")
    smoke_test(ctx, model_id, SMOKE_TEST_LAUNCH)

    print()
    print("=== Done ===")
    print(f"  aimodelid: {model_id}")
    print(f"  state:     published (statecode=1), active run config set")
    print(f"  solution:  {SOLUTION_NAME}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/register_ai_prompt.py <prompt-folder>")
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1])))
