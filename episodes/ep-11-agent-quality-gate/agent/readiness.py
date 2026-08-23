from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataverse import LaunchResearch
from .quality_check import QualityResult

FORMATTED = "@OData.Community.Display.V1.FormattedValue"


@dataclass(frozen=True)
class Finding:
    severity: str
    category: str
    summary: str
    detail: str
    penalty: int


@dataclass(frozen=True)
class ReadinessResult:
    outcome: str
    score: int
    feedback: str
    evidence: str
    findings: tuple[Finding, ...]


def formatted(row: dict[str, Any], field: str, default: str = "Unknown") -> str:
    return str(row.get(field + FORMATTED) or default)


def analyze_readiness(
    research: LaunchResearch,
    browser: QualityResult,
    evidence_dir: Path,
    *,
    now: datetime | None = None,
) -> ReadinessResult:
    now = now or datetime.now(timezone.utc)
    findings: list[Finding] = []
    launch = research.launch
    risk = str(launch.get("lc_risksummary") or "").strip()
    if risk.lower().startswith("high"):
        findings.append(Finding(
            "error",
            "Launch risk",
            "Launch risk summary is High",
            risk,
            10,
        ))
    elif risk.lower().startswith("medium"):
        findings.append(Finding(
            "warning",
            "Launch risk",
            "Launch risk summary is Medium",
            risk,
            5,
        ))

    milestone_status = Counter(
        formatted(row, "lc_milestonestatus")
        for row in research.milestones
    )
    for status, penalty, severity in (
        ("Blocked", 12, "error"),
        ("AtRisk", 7, "warning"),
    ):
        count = milestone_status.get(status, 0)
        if count:
            names = [
                str(row.get("lc_name") or "Unnamed milestone")
                for row in research.milestones
                if formatted(row, "lc_milestonestatus") == status
            ]
            findings.append(Finding(
                severity,
                "Milestones",
                f"{count} milestone(s) are {status}",
                ", ".join(names),
                penalty * count,
            ))

    overdue_milestones = [
        row for row in research.milestones
        if _overdue(row.get("lc_duedate"), now)
        and formatted(row, "lc_milestonestatus") != "Done"
    ]
    if overdue_milestones:
        findings.append(Finding(
            "warning",
            "Milestones",
            f"{len(overdue_milestones)} milestone(s) are overdue",
            ", ".join(str(row.get("lc_name")) for row in overdue_milestones),
            min(12, 4 * len(overdue_milestones)),
        ))

    blocked_tasks = [
        row for row in research.tasks if row.get("lc_isblocked") is True
    ]
    if blocked_tasks:
        findings.append(Finding(
            "error",
            "Execution",
            f"{len(blocked_tasks)} task(s) have active blockers",
            "; ".join(
                f"{row.get('lc_title')}: {row.get('lc_blockerreason')}"
                for row in blocked_tasks
            ),
            min(32, 8 * len(blocked_tasks)),
        ))

    overdue_tasks = [
        row for row in research.tasks
        if _overdue(row.get("lc_duedate"), now)
        and formatted(row, "lc_taskstatus") != "Done"
    ]
    if overdue_tasks:
        findings.append(Finding(
            "warning",
            "Execution",
            f"{len(overdue_tasks)} incomplete task(s) are overdue",
            ", ".join(str(row.get("lc_title")) for row in overdue_tasks),
            min(12, 2 * len(overdue_tasks)),
        ))

    if research.status_updates:
        latest = research.status_updates[0]
        health = formatted(latest, "lc_health")
        if health in {"Yellow", "Red"}:
            findings.append(Finding(
                "warning" if health == "Yellow" else "error",
                "Status signal",
                f"Latest launch health is {health}",
                str(latest.get("lc_summary") or ""),
                5 if health == "Yellow" else 20,
            ))
    else:
        findings.append(Finding(
            "warning",
            "Status signal",
            "No launch status update is available",
            "The agent could not find a current status signal.",
            5,
        ))

    if browser.outcome != "PASSED":
        findings.append(Finding(
            "warning" if browser.outcome == "NEEDS_REVIEW" else "error",
            "Release candidate",
            "Browser validation failed",
            browser.feedback,
            min(30, 100 - browser.score),
        ))

    score = max(0, 100 - sum(item.penalty for item in findings))
    has_blocker = any(
        item.severity == "error"
        and item.category in {"Milestones", "Execution", "Release candidate"}
        for item in findings
    )
    if has_blocker or score < 60:
        outcome = "FAILED"
    elif findings or score < 85:
        outcome = "NEEDS_REVIEW"
    else:
        outcome = "PASSED"

    headline = (
        f"Readiness {score}/100 ({outcome}). "
        f"Reviewed {len(research.milestones)} milestones, "
        f"{len(research.tasks)} tasks, "
        f"{len(research.status_updates)} status updates, and the release page."
    )
    top_findings = " ".join(
        f"{item.summary}: {item.detail}."
        for item in findings[:5]
    )
    feedback = (headline + " " + top_findings).strip()

    evidence_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    evidence_path = evidence_dir / f"readiness-{stamp}.json"
    evidence_path.write_text(
        json.dumps(
            {
                "generated_at": now.isoformat(),
                "outcome": outcome,
                "score": score,
                "launch": research.launch,
                "milestones": research.milestones,
                "tasks": research.tasks,
                "status_updates": research.status_updates,
                "browser": asdict(browser),
                "findings": [asdict(item) for item in findings],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return ReadinessResult(
        outcome=outcome,
        score=score,
        feedback=feedback[:10000],
        evidence=str(evidence_path),
        findings=tuple(findings),
    )


def _overdue(value: Any, now: datetime) -> bool:
    if not value:
        return False
    due = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return due < now
