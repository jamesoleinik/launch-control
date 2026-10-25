"""Bounded issue-completion reconciliation. Preview by default; no Work IQ writes."""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID


NOT_STARTED = 10600301
IN_PROGRESS = 10600302
DONE = 10600304


class BoundaryError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise BoundaryError(message)


def guid(value):
    return str(UUID(value))


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise BoundaryError("GitHub redirected the request; verify the configured repository")


@dataclass(frozen=True)
class Mapping:
    repository: str
    issue: int
    environment_url: str
    organization_id: str
    task_id: str
    launch_id: str

    @classmethod
    def load(cls, raw):
        data = json.loads(raw)
        mapping = cls(**data)
        require(
            re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", mapping.repository),
            "Invalid configured repository",
        )
        require(type(mapping.issue) is int and mapping.issue > 0, "Invalid issue number")
        require(
            re.fullmatch(r"https://[a-zA-Z0-9-]+\.crm[0-9]*\.dynamics\.com", mapping.environment_url),
            "Expected an explicit public-cloud Dataverse organization URL",
        )
        for field in ("organization_id", "task_id", "launch_id"):
            require(getattr(mapping, field) == guid(getattr(mapping, field)), f"Noncanonical {field}")
        return mapping


class GitHub:
    def __init__(self, token):
        require(bool(token), "GITHUB_TOKEN is required")
        self.token = token

    def issue(self, mapping):
        request = Request(
            f"https://api.github.com/repos/{mapping.repository}/issues/{mapping.issue}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with build_opener(RejectRedirects()).open(request, timeout=30) as response:
            return json.load(response)


class Dataverse:
    """Use managed CLI for conditional PATCH, unavailable in SDK records.update."""

    def __init__(self, mapping):
        self.mapping = mapping
        self.executable = shutil.which("dataverse.cmd") or shutil.which("dataverse")
        require(self.executable is not None, "Install the official @microsoft/dataverse CLI")

    def request(self, path, *, changes=None, etag=None):
        args = [
            self.executable, "--log-file", "api", "request", "--target", "dataverse",
            "--environment", self.mapping.environment_url,
            # On Linux the CLI treats a leading slash as an absolute file URI.
            "--path", f"{self.mapping.environment_url}/api/data/v9.2/{path}",
        ]
        if changes is not None:
            require(etag is not None, "Refusing an unconditional update")
            args.extend([
                "--method", "PATCH", "--header", f"If-Match:{etag}",
                "--body", json.dumps(changes, separators=(",", ":")),
            ])
        # The CLI's default console logger mixes headless auth warnings into stdout.
        # File logging keeps the HTTP body separate, without stripping arbitrary text.
        with tempfile.TemporaryDirectory(prefix="lc-cli-") as folder:
            result = subprocess.run(
                args, capture_output=True, text=True, check=False, timeout=120,
                env={**os.environ, "TMP": folder, "TEMP": folder, "TMPDIR": folder},
            )
        require(
            result.returncode == 0,
            f"Dataverse {'PATCH' if changes is not None else 'GET'} failed. "
            "Inspect the CLI error locally; do not retry an uncertain write without readback. "
            f"{result.stderr.strip()}",
        )
        try:
            payload = json.loads(result.stdout) if result.stdout.strip() else None
        except json.JSONDecodeError as error:
            raise BoundaryError(
                f"Dataverse {'PATCH' if changes is not None else 'GET'} returned non-JSON "
                f"stdout (line {error.lineno}, column {error.colno}); no retry was attempted."
            ) from None
        require(not isinstance(payload, dict) or "error" not in payload,
                "Dataverse returned an error envelope. Inspect before retrying.")
        if changes is None:
            require(isinstance(payload, dict), "Dataverse GET did not return a JSON object")
            return payload
        require(payload is None or isinstance(payload, dict),
                "Dataverse PATCH returned an unexpected response body; inspect before retrying.")
        return None

    def identity(self):
        return self.request("WhoAmI")

    def task(self):
        return self.request(
            f"lc_tasks({self.mapping.task_id})?"
            "$select=lc_taskid,_lc_launchid_value,lc_taskstatus,lc_isblocked,lc_blockerreason,statecode"
        )

    def launch(self):
        return self.request(
            f"lc_launchs({self.mapping.launch_id})?"
            "$select=lc_launchid,lc_risksummary,lc_launchstatus"
        )

    def complete_task(self, etag):
        self.request(
            f"lc_tasks({self.mapping.task_id})", changes={"lc_taskstatus": DONE}, etag=etag,
        )


def validate_event(mapping, event, repository):
    require(repository == mapping.repository, "Runner repository differs from allowlist")
    require(event.get("repository", {}).get("full_name") == mapping.repository,
            "Event repository differs from allowlist")
    require(event.get("action") == "closed", "Only issue-close events are accepted")
    issue = event.get("issue", {})
    require(type(issue.get("number")) is int and issue["number"] == mapping.issue,
            "Event issue differs from allowlist")
    require("pull_request" not in issue, "Pull requests are not accepted")


def validate_issue(mapping, issue):
    require(type(issue.get("number")) is int and issue["number"] == mapping.issue,
            "GitHub returned an unexpected issue")
    require(issue.get("url") ==
            f"https://api.github.com/repos/{mapping.repository}/issues/{mapping.issue}",
            "GitHub returned an unexpected issue URL")
    require("pull_request" not in issue, "Pull requests are not accepted")
    require(issue.get("state") == "closed" and issue.get("state_reason") == "completed",
            "Current issue is not closed as completed (unknown reason is not completion)")


def validate_task(mapping, task):
    require(task.get("lc_taskid") == mapping.task_id, "Task identity mismatch")
    require(task.get("_lc_launchid_value") == mapping.launch_id, "Task parent mismatch")
    require(task.get("statecode") == 0, "Task must be active")
    require(task.get("lc_isblocked") is False, "Task blocked flag must explicitly be false")
    require("lc_blockerreason" in task and
            (task["lc_blockerreason"] is None or
             isinstance(task["lc_blockerreason"], str) and not task["lc_blockerreason"].strip()),
            "Task blocker reason is set or unavailable")
    require(task.get("lc_taskstatus") in (NOT_STARTED, IN_PROGRESS, DONE),
            "Task status is not eligible for completion")
    require(re.fullmatch(r'W/"[0-9]+"', task.get("@odata.etag", "")),
            "A real task ETag is required")


def inspect_current(mapping, github, dataverse):
    require(dataverse.identity().get("OrganizationId") == mapping.organization_id,
            "Dataverse organization differs from pinned organization")
    validate_issue(mapping, github.issue(mapping))
    task = dataverse.task()
    validate_task(mapping, task)
    launch = dataverse.launch()
    require(launch.get("lc_launchid") == mapping.launch_id, "Launch identity mismatch")
    require(all(field in launch for field in ("lc_risksummary", "lc_launchstatus")),
            "Launch risk/status evidence unavailable")
    return task, launch


def reconcile(mapping, event, repository, github, dataverse, *, apply=False):
    validate_event(mapping, event, repository)
    task, launch = inspect_current(mapping, github, dataverse)
    receipt = {
        "repository": mapping.repository, "issue": mapping.issue,
        "task_id": mapping.task_id, "launch_id": mapping.launch_id,
        "prior_task_status": task["lc_taskstatus"],
        "launch_write": False,
    }
    if task["lc_taskstatus"] == DONE:
        return {**receipt, "outcome": "already_done"}
    if not apply:
        return {**receipt, "outcome": "dry_run", "proposed_task_status": DONE}

    # Recheck source immediately before the conditional write. The two systems
    # do not share a transaction; a later GitHub reopen is not handled here.
    validate_issue(mapping, github.issue(mapping))
    dataverse.complete_task(task["@odata.etag"])
    saved = dataverse.task()
    validate_task(mapping, saved)
    require(saved["lc_taskstatus"] == DONE,
            "Write returned but completed task state was not verified")
    current_launch = dataverse.launch()
    require(current_launch.get("lc_launchid") == mapping.launch_id and
            all(field in current_launch and current_launch[field] == launch[field]
                for field in ("lc_risksummary", "lc_launchstatus")),
            "Launch risk/status changed during reconciliation. Inspect before any retry.")
    return {**receipt, "outcome": "updated", "task_status": DONE}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Perform the conditional status update")
    mode.add_argument("--dry-run", action="store_true", help="Read-only preview (default)")
    mode.add_argument("--inspect", action="store_true", help="Read current records without an event or write")
    args = parser.parse_args()
    mapping = Mapping.load(os.environ["LC_FIXER_CONFIG"])
    require(os.environ["GITHUB_REPOSITORY"] == mapping.repository,
            "Runner repository differs from allowlist")
    if args.inspect:
        task, launch = inspect_current(
            mapping, GitHub(os.environ["GITHUB_TOKEN"]), Dataverse(mapping),
        )
        print(json.dumps({
            "outcome": "inspection_only", "task_status": task["lc_taskstatus"],
            "task_etag": task["@odata.etag"], "launch_status": launch["lc_launchstatus"],
            "launch_risks": launch["lc_risksummary"], "launch_write": False,
        }, sort_keys=True))
        return
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    # Validate before constructing authenticated adapters.
    validate_event(mapping, event, os.environ["GITHUB_REPOSITORY"])
    result = reconcile(
        mapping, event, os.environ["GITHUB_REPOSITORY"],
        GitHub(os.environ["GITHUB_TOKEN"]), Dataverse(mapping), apply=args.apply,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (BoundaryError, KeyError, ValueError, TypeError, OSError, subprocess.SubprocessError) as error:
        print(f"Reconciliation failed: {error}", file=sys.stderr)
        sys.exit(1)
