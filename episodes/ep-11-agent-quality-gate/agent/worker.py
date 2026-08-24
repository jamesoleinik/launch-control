from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from traceback import format_exc

from .config import Config
from .dataverse import Assignment, DataverseClient, LaunchResearch
from .identity import AgentTokenProvider
from .mailbox import MailboxClient
from .quality_check import run_quality_check
from .readiness import analyze_readiness, formatted
from .telemetry import assignment_span, configure_telemetry
from .teams import TeamsNotifier
from .trace_log import trace_event


def log_event(
    config: Config,
    status: str,
    title: str,
    detail: str = "",
    attachment: str = "",
) -> None:
    trace_event(
        config.evidence_dir,
        status=status,
        title=title,
        detail=detail,
        attachment=attachment,
    )


def trace_research(config: Config, research: LaunchResearch) -> None:
    launch = research.launch
    log_event(
        config,
        "running",
        "Reading Launch profile and risk summary",
        (
            f"{launch.get('lc_name')} | "
            f"Priority: {formatted(launch, 'lc_priority')} | "
            f"Target: {launch.get('lc_targetdate')} | "
            f"Risk: {launch.get('lc_risksummary') or 'None'}"
        ),
    )
    log_event(
        config,
        "running",
        f"Reviewing {len(research.milestones)} milestones",
        "Checking status, due dates, and delivery risk.",
    )
    for milestone in research.milestones:
        status = formatted(milestone, "lc_milestonestatus")
        log_event(
            config,
            (
                "error" if status == "Blocked"
                else "warning" if status == "AtRisk"
                else "running"
            ),
            f"Milestone: {milestone.get('lc_name')}",
            f"{status} | Due {milestone.get('lc_duedate')}",
        )
    blocked = [row for row in research.tasks if row.get("lc_isblocked")]
    log_event(
        config,
        "running",
        f"Reviewing {len(research.tasks)} execution tasks",
        f"{len(blocked)} active blocker(s) detected.",
    )
    for task in blocked:
        log_event(
            config,
            "error",
            f"Blocked task: {task.get('lc_title')}",
            str(task.get("lc_blockerreason") or "No blocker detail supplied"),
        )
    if research.status_updates:
        latest = research.status_updates[0]
        health = formatted(latest, "lc_health")
        log_event(
            config,
            "warning" if health == "Yellow" else "error" if health == "Red" else "pass",
            f"Latest status signal: {health}",
            str(latest.get("lc_summary") or ""),
        )
    else:
        log_event(
            config,
            "warning",
            "No status signal found",
            "The Launch has no related status updates.",
        )


def process_assignment(
    client: DataverseClient,
    config: Config,
    assignment: Assignment,
    teams: TeamsNotifier | None = None,
) -> None:
    if client.result_exists(assignment.assignment_key):
        log_event(
            config,
            "idle",
            "Existing result found",
            "No duplicate agent work was performed.",
        )
        client.complete_task(assignment)
        print(f"[skip] result already exists for {assignment.assignment_key}")
        return

    launch_name = client.verify_launch_access(assignment)
    log_event(
        config,
        "pass",
        "Assigned Launch access verified",
        launch_name,
    )
    print(f"[ok] assigned Launch access verified: {launch_name}")
    tracer = configure_telemetry()
    with assignment_span(tracer, assignment.assignment_key) as span:
        if not client.claim(assignment):
            log_event(
                config,
                "idle",
                "Assignment already claimed",
                assignment.assignment_key,
            )
            print(f"[skip] assignment already claimed: {assignment.assignment_key}")
            return
        log_event(
            config,
            "running",
            "Assignment claimed by Agent User",
            assignment.assignment_key,
        )
        try:
            research = client.research_launch(assignment)
            trace_research(config, research)
            log_event(
                config,
                "running",
                "Running Playwright quality checks",
                config.quality_gate_url,
            )
            browser_result = run_quality_check(config, assignment.launch_name)
            screenshot = Path(browser_result.evidence)
            playwright_trace = Path(browser_result.trace)
            if screenshot.is_file():
                log_event(
                    config,
                    "warning" if browser_result.outcome != "PASSED" else "pass",
                    "Playwright browser evidence captured",
                    browser_result.feedback,
                    screenshot.name,
                )
            if playwright_trace.is_file():
                log_event(
                    config,
                    "pass",
                    "Playwright trace captured",
                    "Trace includes browser snapshots, screenshots, and sources.",
                    playwright_trace.name,
                )
            result = analyze_readiness(
                research,
                browser_result,
                config.evidence_dir,
            )
        except Exception as exc:
            from .quality_check import QualityResult

            result = QualityResult(
                outcome="ERROR",
                score=0,
                feedback=f"Quality check failed: {type(exc).__name__}: {exc}",
                evidence=format_exc(limit=5)[-1000:],
            )
            log_event(
                config,
                "error",
                "Quality check returned an error",
                result.feedback,
            )
        else:
            for finding in result.findings:
                log_event(
                    config,
                    finding.severity,
                    finding.summary,
                    finding.detail,
                )
            log_event(
                config,
                "pass" if result.outcome == "PASSED" else "error",
                f"Readiness decision: {result.outcome}",
                f"Evidence-backed score: {result.score}/100",
            )
        screenshot = Path(browser_result.evidence) if "browser_result" in locals() else None
        playwright_trace = (
            Path(browser_result.trace)
            if "browser_result" in locals() and browser_result.trace
            else None
        )
        if (
            screenshot is not None
            and screenshot.is_file()
            and playwright_trace is not None
            and playwright_trace.is_file()
        ):
            client.publish_evidence(
                assignment,
                screenshot=screenshot,
                trace=playwright_trace,
            )
            log_event(
                config,
                "pass",
                "Browser evidence published to Launch",
                "Attached the screenshot and Playwright trace to the timeline.",
                screenshot.name,
            )
        if (
            result.outcome in {"FAILED", "NEEDS_REVIEW"}
            and screenshot is not None
            and screenshot.is_file()
        ):
            client.publish_remediation(
                assignment,
                feedback=result.feedback,
            )
            log_event(
                config,
                "warning",
                "Remediation published to Launch",
                "Created a blocked task and Yellow status update.",
            )
        result_id = client.create_result(
            assignment,
            outcome=result.outcome,
            score=result.score,
            feedback=result.feedback,
            evidence=result.evidence,
        )
        log_event(
            config,
            "pass",
            "Result written to Dataverse",
            f"Result ID: {result_id}",
        )
        if teams:
            notification = teams.send_completion(
                assignment,
                outcome=result.outcome,
                score=result.score,
            )
            log_event(
                config,
                "pass",
                "Completion shared in Teams",
                (
                    f"Message ID: {notification.message_id}. "
                    "The link opens the Launch and current BPF state."
                ),
            )
        client.complete_task(assignment)
        log_event(
            config,
            "pass",
            "Assignment complete",
            "Launch access revoked and BPF evaluated.",
        )
        span.set_attribute("launch_control.outcome", result.outcome)
        span.set_attribute("launch_control.score", result.score)
        span.set_attribute("launch_control.result_id", result_id)
        print(json.dumps(asdict(result), indent=2))
        print(f"[ok] Dataverse result: {result_id}")


def run_once(
    client: DataverseClient,
    config: Config,
    mailbox: MailboxClient | None = None,
    teams: TeamsNotifier | None = None,
    *,
    log_idle: bool = True,
) -> int:
    assignments = client.pending_assignments()
    if not assignments:
        if log_idle:
            log_event(
                config,
                "idle",
                "No pending Quality Gate assignments",
                "Agent User cannot access an unassigned Launch.",
            )
            print("[idle] no pending Quality Gate assignments")
        return 0
    notifications = mailbox.pending_notifications() if mailbox else []
    message_by_task = {
        notification.task_id: notification.message_id
        for notification in notifications
    }
    assignments.sort(
        key=lambda assignment: assignment.task_id.lower() not in message_by_task
    )
    for assignment in assignments:
        process_assignment(client, config, assignment, teams)
        message_id = message_by_task.get(assignment.task_id.lower())
        if message_id and mailbox:
            mailbox.mark_read(message_id)
    return len(assignments)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument(
        "--wait-once",
        action="store_true",
        help="Wait for one assignment, process it, then exit.",
    )
    parser.add_argument(
        "--wait-timeout-seconds",
        type=int,
        default=900,
        help="Maximum wait for --wait-once before exiting with status 2.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without Dataverse or browser mutations.",
    )
    args = parser.parse_args()

    config = Config.load(require_agent_user=not args.dry_run)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dataverse_url": config.dataverse_url,
                    "agent_systemuser_configured": bool(
                        config.agent_systemuser_id
                    ),
                    "agent_mailbox_configured": bool(config.agent_mailbox),
                    "quality_gate_url": config.quality_gate_url,
                    "poll_seconds": config.poll_seconds,
                    "headless": config.headless,
                    "demo_mode": config.demo_mode,
                },
                indent=2,
            )
        )
        return 0

    token_provider = AgentTokenProvider(config)
    print(f"Identity mode: {token_provider.mode}")
    client = DataverseClient(config, token_provider)
    mailbox = (
        MailboxClient(config.agent_mailbox, token_provider)
        if config.agent_mailbox
        else None
    )
    teams = (
        TeamsNotifier(
            config,
            token_provider,
            os.environ.get("A365_AGENT_USER_ID", ""),
        )
        if config.teams_recipient and config.launch_control_app_id
        else None
    )
    if args.once:
        run_once(client, config, mailbox, teams)
        return 0
    if args.wait_once:
        if args.wait_timeout_seconds <= 0:
            parser.error("--wait-timeout-seconds must be positive")
        deadline = time.monotonic() + args.wait_timeout_seconds
        print(
            "[wait] waiting for one Quality Gate assignment "
            f"(timeout {args.wait_timeout_seconds}s)"
        )
        while time.monotonic() < deadline:
            if run_once(
                client,
                config,
                mailbox,
                teams,
                log_idle=False,
            ):
                return 0
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(config.poll_seconds, remaining))
        print("[timeout] no Quality Gate assignment received")
        return 2

    while True:
        run_once(client, config, mailbox, teams)
        time.sleep(config.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
