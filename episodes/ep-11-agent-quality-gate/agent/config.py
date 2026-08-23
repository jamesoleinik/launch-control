from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

EPISODE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EPISODE_ROOT.parents[1]


@dataclass(frozen=True)
class Config:
    dataverse_url: str
    tenant_id: str
    agent_systemuser_id: str
    agent_mailbox: str
    teams_recipient: str
    launch_control_app_id: str
    quality_gate_url: str
    required_text: str
    poll_seconds: int
    headless: bool
    demo_mode: bool
    demo_step_seconds: float
    demo_hold_seconds: float
    evidence_dir: Path

    @classmethod
    def load(cls, *, require_agent_user: bool = True) -> "Config":
        load_dotenv(REPO_ROOT / ".env")
        load_dotenv(EPISODE_ROOT / ".env", override=True)
        required = {
            "DATAVERSE_URL": os.environ.get("DATAVERSE_URL"),
            "TENANT_ID": os.environ.get("TENANT_ID"),
        }
        agent_user = os.environ.get("QUALITY_GATE_AGENT_SYSTEMUSER_ID", "")
        if require_agent_user:
            required["QUALITY_GATE_AGENT_SYSTEMUSER_ID"] = agent_user
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(missing)
            )
        evidence = Path(
            os.environ.get(
                "QUALITY_GATE_EVIDENCE_DIR", ".artifacts/quality-gate"
            )
        )
        if not evidence.is_absolute():
            evidence = REPO_ROOT / evidence
        return cls(
            dataverse_url=required["DATAVERSE_URL"].rstrip("/"),
            tenant_id=required["TENANT_ID"],
            agent_systemuser_id=agent_user.strip("{}"),
            agent_mailbox=os.environ.get("A365_AGENT_MAILBOX", "").strip(),
            teams_recipient=os.environ.get(
                "A365_TEAMS_RECIPIENT", ""
            ).strip(),
            launch_control_app_id=os.environ.get(
                "LAUNCH_CONTROL_APP_ID", ""
            ).strip("{}"),
            quality_gate_url=os.environ.get(
                "QUALITY_GATE_URL", "http://127.0.0.1:8000"
            ),
            required_text=os.environ.get(
                "QUALITY_GATE_REQUIRED_TEXT", "Launch Control"
            ),
            poll_seconds=int(os.environ.get("QUALITY_GATE_POLL_SECONDS", "300")),
            headless=os.environ.get(
                "QUALITY_GATE_HEADLESS", "true"
            ).lower() not in {"0", "false", "no"},
            demo_mode=os.environ.get(
                "QUALITY_GATE_DEMO_MODE", "false"
            ).lower() in {"1", "true", "yes"},
            demo_step_seconds=max(
                0.0,
                float(os.environ.get("QUALITY_GATE_DEMO_STEP_SECONDS", "1.2")),
            ),
            demo_hold_seconds=max(
                0.0,
                float(os.environ.get("QUALITY_GATE_DEMO_HOLD_SECONDS", "8")),
            ),
            evidence_dir=evidence,
        )
