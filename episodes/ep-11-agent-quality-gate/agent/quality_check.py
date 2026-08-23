from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import ConsoleMessage, Page, sync_playwright

from .config import Config


@dataclass(frozen=True)
class QualityResult:
    outcome: str
    score: int
    feedback: str
    evidence: str


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "launch"


def install_demo_overlay(page: Page, launch_name: str) -> None:
    page.evaluate(
        """
        ({ launchName, steps }) => {
          const host = document.createElement("aside");
          host.id = "launch-control-quality-gate";
          host.innerHTML = `
            <style>
              #launch-control-quality-gate {
                position: fixed; z-index: 2147483647; top: 24px; right: 24px;
                width: 380px; padding: 22px; border-radius: 18px;
                color: #f8fafc; background: rgba(15, 23, 42, .96);
                border: 1px solid rgba(148, 163, 184, .35);
                box-shadow: 0 24px 70px rgba(15, 23, 42, .45);
                font: 14px/1.4 "Segoe UI", sans-serif;
              }
              #launch-control-quality-gate * { box-sizing: border-box; }
              #launch-control-quality-gate h2 {
                margin: 0 0 4px; font-size: 20px; color: #fff;
              }
              #launch-control-quality-gate .launch {
                margin-bottom: 16px; color: #93c5fd; font-weight: 600;
              }
              #launch-control-quality-gate .step {
                display: grid; grid-template-columns: 22px 1fr;
                gap: 10px; padding: 9px 0; color: #cbd5e1;
              }
              #launch-control-quality-gate .icon {
                display: grid; place-items: center; width: 20px; height: 20px;
                border-radius: 50%; background: #334155; color: #94a3b8;
                font-size: 12px; font-weight: 700;
              }
              #launch-control-quality-gate .step.running .icon {
                background: #1d4ed8; color: white;
              }
              #launch-control-quality-gate .step.pass .icon {
                background: #16a34a; color: white;
              }
              #launch-control-quality-gate .step.fail .icon {
                background: #dc2626; color: white;
              }
              #launch-control-quality-gate .detail {
                display: block; color: #94a3b8; font-size: 12px;
              }
              #launch-control-quality-gate .summary {
                margin-top: 16px; padding: 12px; border-radius: 10px;
                background: #1e293b; color: #cbd5e1; font-weight: 600;
              }
              #launch-control-quality-gate .summary.pass {
                background: #14532d; color: #dcfce7;
              }
              #launch-control-quality-gate .summary.fail {
                background: #7f1d1d; color: #fee2e2;
              }
            </style>
            <h2>Agent Quality Gate</h2>
            <div class="launch"></div>
            <div class="steps"></div>
            <div class="summary">Preparing checks...</div>`;
          host.querySelector(".launch").textContent = launchName;
          const list = host.querySelector(".steps");
          for (const step of steps) {
            const row = document.createElement("div");
            row.className = "step";
            row.dataset.step = step.key;
            row.innerHTML = `<span class="icon">-</span><span>
              <strong></strong><small class="detail"></small></span>`;
            row.querySelector("strong").textContent = step.label;
            list.appendChild(row);
          }
          document.body.appendChild(host);
        }
        """,
        {
            "launchName": launch_name,
            "steps": [
                {"key": "response", "label": "HTTP response"},
                {"key": "title", "label": "Page title"},
                {"key": "content", "label": "Required content"},
                {"key": "workflow", "label": "Critical workflow"},
                {"key": "console", "label": "Browser console"},
                {"key": "evidence", "label": "Evidence capture"},
            ],
        },
    )


def update_demo(
    page: Page,
    config: Config,
    step: str,
    status: str,
    detail: str,
) -> None:
    if not config.demo_mode:
        return
    page.evaluate(
        """
        ({ step, status, detail }) => {
          const host = document.querySelector("#launch-control-quality-gate");
          const row = host?.querySelector(`[data-step="${step}"]`);
          if (!row) return;
          row.className = `step ${status}`;
          row.querySelector(".icon").textContent =
            status === "pass" ? "✓" : status === "fail" ? "!" : "•";
          row.querySelector(".detail").textContent = detail;
        }
        """,
        {"step": step, "status": status, "detail": detail},
    )
    page.wait_for_timeout(config.demo_step_seconds * 1000)


def finish_demo(page: Page, config: Config, passed: bool) -> None:
    if not config.demo_mode:
        return
    page.evaluate(
        """
        ({ passed }) => {
          const summary = document.querySelector(
            "#launch-control-quality-gate .summary"
          );
          summary.className = `summary ${passed ? "pass" : "fail"}`;
          summary.textContent = passed
            ? "Checks passed. Returning result to Dataverse..."
            : "Checks failed. Returning findings to Dataverse...";
        }
        """,
        {"passed": passed},
    )
    page.wait_for_timeout(config.demo_hold_seconds * 1000)


def run_quality_check(config: Config, launch_name: str) -> QualityResult:
    config.evidence_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    screenshot = config.evidence_dir / f"{safe_name(launch_name)}-{stamp}.png"
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False if config.demo_mode else config.headless,
            slow_mo=200 if config.demo_mode else 0,
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        def capture_console(message: ConsoleMessage) -> None:
            if message.type == "error":
                console_errors.append(message.text)

        page.on("console", capture_console)
        response = page.goto(
            config.quality_gate_url, wait_until="networkidle", timeout=60_000
        )
        body = page.locator("body").inner_text()
        title = page.title().strip()
        if config.demo_mode:
            install_demo_overlay(page, launch_name)

        failures: list[str] = []
        response_ok = response is not None and response.status < 400
        update_demo(
            page,
            config,
            "response",
            "pass" if response_ok else "fail",
            f"HTTP {response.status}" if response else "No response",
        )
        if not response_ok:
            failures.append(
            "Page did not return a successful HTTP response"
            if response is None
            else f"Page returned HTTP {response.status}"
        )
        update_demo(
            page,
            config,
            "title",
            "pass" if title else "fail",
            title or "Title is empty",
        )
        if not title:
            failures.append("Page title is empty")
        content_ok = not config.required_text or config.required_text in body
        update_demo(
            page,
            config,
            "content",
            "pass" if content_ok else "fail",
            (
                f"Found {config.required_text!r}"
                if content_ok and config.required_text
                else "No required text configured"
                if content_ok
                else f"Missing {config.required_text!r}"
            ),
        )
        if not content_ok:
            failures.append(
                f"Required text was not found: {config.required_text!r}"
            )
        workflow_button = page.locator("#validate-release")
        workflow_ok = False
        workflow_detail = "Critical workflow control was not found"
        if workflow_button.count():
            workflow_button.click()
            page.locator("#validation-result").wait_for(
                state="visible",
                timeout=10_000,
            )
            page.wait_for_function(
                """
                () => document.querySelector("#validation-result")
                    ?.dataset.state !== "waiting"
                """,
                timeout=10_000,
            )
            workflow_result = page.locator("#validation-result")
            workflow_ok = workflow_result.get_attribute("data-state") == "passed"
            workflow_detail = workflow_result.inner_text().strip()
        update_demo(
            page,
            config,
            "workflow",
            "pass" if workflow_ok else "fail",
            workflow_detail,
        )
        if not workflow_ok:
            failures.append(f"Critical workflow failed: {workflow_detail}")
        page.wait_for_timeout(500)
        update_demo(
            page,
            config,
            "console",
            "fail" if console_errors else "pass",
            (
                f"{len(console_errors)} error(s)"
                if console_errors
                else "No console errors"
            ),
        )
        if console_errors:
            failures.append(
                f"{len(console_errors)} browser console error(s): "
                + "; ".join(console_errors[:3])
            )
        update_demo(
            page,
            config,
            "evidence",
            "pass",
            screenshot.name,
        )
        finish_demo(page, config, not failures)
        page.screenshot(path=str(screenshot), full_page=True)
        browser.close()

    if failures:
        return QualityResult(
            outcome="NEEDS_REVIEW",
            score=max(0, 100 - 25 * len(failures)),
            feedback="; ".join(failures),
            evidence=str(screenshot),
        )
    return QualityResult(
        outcome="PASSED",
        score=100,
        feedback=(
            f"HTTP response, page title, required text, and browser console "
            f"checks passed for {config.quality_gate_url}."
        ),
        evidence=str(screenshot),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-name", default="Quality Gate Test")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = Config.load(require_agent_user=False)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "url": config.quality_gate_url,
                    "required_text": config.required_text,
                    "headless": config.headless,
                    "demo_mode": config.demo_mode,
                    "demo_step_seconds": config.demo_step_seconds,
                    "demo_hold_seconds": config.demo_hold_seconds,
                    "evidence_dir": str(config.evidence_dir),
                },
                indent=2,
            )
        )
        return 0
    result = run_quality_check(config, args.launch_name)
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.outcome == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
