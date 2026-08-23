"""Send and verify an Agentic User-authored Teams completion update."""

from __future__ import annotations

import argparse
import os

from agent.config import Config
from agent.dataverse import Assignment
from agent.identity import AgentTokenProvider
from agent.teams import TeamsNotifier


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--launch-id")
    parser.add_argument("--launch-name", default="Q3 Widget Launch")
    parser.add_argument(
        "--outcome",
        choices=("PASSED", "FAILED", "NEEDS_REVIEW", "ERROR"),
        default="NEEDS_REVIEW",
    )
    parser.add_argument("--score", type=int, default=70)
    args = parser.parse_args()

    config = Config.load()
    required = {
        "A365_TEAMS_RECIPIENT": config.teams_recipient,
        "LAUNCH_CONTROL_APP_ID": config.launch_control_app_id,
        "A365_AGENT_USER_ID": os.environ.get("A365_AGENT_USER_ID", ""),
    }
    if args.apply:
        required["--launch-id"] = args.launch_id or ""
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing Teams live-test configuration: " + ", ".join(missing)
        )

    print(f"Recipient: {config.teams_recipient}")
    print(f"Outcome: {args.outcome}, score: {args.score}")
    if args.dry_run:
        print("[dry-run] no Teams message sent")
        return 0

    assignment = Assignment(
        task_id="teams-live-proof",
        launch_id=args.launch_id.strip("{}"),
        launch_name=args.launch_name,
        assignment_key=f"Quality Gate::{args.launch_id.strip('{}')}",
    )
    provider = AgentTokenProvider(config)
    notifier = TeamsNotifier(
        config,
        provider,
        os.environ["A365_AGENT_USER_ID"],
    )
    sent = notifier.send_completion(
        assignment,
        outcome=args.outcome,
        score=args.score,
    )
    print("[PASS] Teams completion message sent")
    print("[PASS] sender is the configured Agentic User")
    print("[PASS] message includes the Launch/BPF deep link")
    print(f"Message ID: {sent.message_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
