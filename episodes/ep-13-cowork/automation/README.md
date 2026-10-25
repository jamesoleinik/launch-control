# Issue-completion backend

This is a separate deterministic GitHub Actions backend, not an unattended
Work IQ form save or evidence that the Studio agent ran. A disabled deployment
has been published. The first event-driven attempt authenticated through
federation but failed on its initial CLI request, before any business update.
The separately approved path correction was published; its single retry passed
URL validation but rejected non-JSON CLI stdout before any business update.
A local logging-channel correction awaits publication and a separately approved
read-only verification. Successful task reconciliation has not been demonstrated.
The existing Studio draft remains preparation-only.

Issue-driven writes are off unless repository variable `LC_FIXER_ENABLED` is
exactly `true`. The workflow also supports a manual, read-only inspection
with that flag left false. It handles issue-close events on the repository
default branch. It does not close issues,
publish an agent, add a Studio trigger, or write to GitHub.

## Boundary

The runner accepts one exact repository, issue, task, launch and Dataverse
organization mapping. It fetches the current issue through the GitHub API;
event text and issue descriptions cannot supply record IDs or update fields.
Only `state=closed` with `state_reason=completed` qualifies. Missing completion
evidence fails closed.

It checks the task's parent, active state, explicit nonblocked flag, empty
blocker reason and eligible status. The only write is `lc_taskstatus=Done`,
with the task's actual ETag in `If-Match`. A concurrent task edit fails rather
than being overwritten. A task already Done is a no-op, not exactly-once
delivery. Source completion is rechecked immediately before the write.

Launch risk summary and status are read before and after, never rewritten.
Existing partner blockers and unrelated risks are not removed. This deliberately
avoids generating a new narrative risk summary or claiming a safe launch from
one completed checklist. A changed launch or failed postwrite verification
reports failure; it does not silently roll back or retry a possibly saved write.

GitHub and Dataverse do not share a transaction. A reopen after the final source
read remains possible. Reopen/reversal handling is not implemented. Dataverse
plug-ins may have additional side effects; verify those during the approved
runtime test. Offline tests do not prove the identity's deployed permission
boundary, CLI response shape or the live ETag contract.

## Configuration and deployment gate

Do not enable or push this workflow before approving the actual target,
identity permissions, mapping, test effects and rollback.

Use a dedicated Entra application and a Dataverse application user, not the
presenter's account. Configure GitHub federation for exactly this repository
and the `launch-reconciliation` environment. No stored client secret is used.
The job can request an OIDC token; GitHub permissions are contents-read and
issues-read only.

Define `LC_FIXER_CONFIG` as one JSON object in that GitHub environment:

```json
{
  "repository": "<owner>/<repo>",
  "issue": 7,
  "environment_url": "https://<organization>.crm.dynamics.com",
  "organization_id": "<organization-guid>",
  "task_id": "<task-guid>",
  "launch_id": "<launch-guid>"
}
```

Define `LC_FIXER_CLIENT_ID` and `LC_FIXER_TENANT_ID` there too. Keep actual
identifiers in local evidence and deployment configuration, not committed files.
Only trusted repository maintainers may change workflow code or mapping.

The dedicated application user needs read access to the mapped task and launch,
and write access to the mapped task. Prefer a dedicated owner team and
record-sharing to constrain record scope. Do not give System Administrator or
organization-wide task write access. Dataverse roles do not limit a grant to
one status column; the runner enforces the field allowlist. That distinction
must be disclosed before approving the identity. Verify the effective access
against unrelated records before enabling the job. If exact record scope
cannot be enforced, stop deployment rather than broadening access.

GitHub environment required-reviewer protection would make each job
human-approved. Do not configure that and call the result autonomous. The
one-time deployment approval is separate from runtime execution. If tenant
policy requires per-run approval, report that restriction.

The workflow installs the official `@microsoft/dataverse` CLI at version
`1.0.81` (the locally inspected CLI version). Conditional PATCH uses its managed
`api request` surface because the
installed Python SDK's `records.update` and changeset helpers do not expose
per-request `If-Match`.

Requests use an explicit HTTPS URL constructed from the validated, pinned
environment origin. A slash-prefixed path was interpreted as an absolute file
URI by the Linux CLI, although the Windows preflight accepted it. The CLI
checks the absolute request host against the supplied environment host.

The installed CLI's `api request` command writes the raw HTTP body to stdout
and returns a nonzero exit code for HTTP failure. It does not accept `--json`.
Its default console logger also writes headless authentication warnings to
stdout, so automation uses the supported global `--log-file` option with an
isolated temporary directory, removed after each call. It never strips progress
text from a response to find a plausible JSON object. A GET must return one JSON
object; a successful PATCH may return no content or one JSON object. Non-JSON
output, error envelopes and nonzero exits fail explicitly without retry.

The Linux runner explicitly permits a cleartext CLI authentication cache in its
ephemeral filesystem and removes that named profile during cleanup. No cache is
uploaded. This must be included in deployment approval; do not reuse the workflow
on a persistent self-hosted runner without a different credential-storage policy.

## Local checks and preview

```powershell
$env:PYTHONIOENCODING = "utf-8"
python -m unittest discover -s scripts\python\tests -p test_reconcile_launch_issue.py
```

The runner defaults to `--dry-run`, but that still performs authenticated live
reads and requires a separately authorized inspection. Supply the mapping,
`GITHUB_REPOSITORY`, a real `GITHUB_EVENT_PATH`, a GitHub read token and a
configured CLI identity. `--apply` is a live conditional write.

The manual workflow-dispatch route runs only `--inspect`, not `--apply`.
It reads the current issue, organization, task and launch using the same
federated identity and transport, without manufacturing an issue-close event.
The issue must currently be closed as completed and the normal record
boundaries still apply. Its receipt says `inspection_only`; it is not
evidence of an autonomous write. Approve workflow publication, temporary
enablement and that read-only run separately. Leave the issue-write flag false.

## Runtime gate and rollback

Before the first run, save an independent task/launch/blocker snapshot and the
issue's current state. Approve closing only the mapped issue as completed.
Observe the actual Actions run, check the completion reason, then independently
verify the task in the native app and confirm launch risks and the partner
blocker remain unchanged. A successful local test or job configuration is not
runtime evidence.

To stop future runs, set `LC_FIXER_ENABLED` to `false` and disable the workflow.
Disabling does not cancel an in-flight job; inspect it and cancel that specific
run if needed before restoring records. Remove the dedicated application user's
grants and federation only after approved cleanup. Reopen the mapped issue and
restore only the task's captured status with a fresh conditional write if that
reset is separately approved. Never restore a stale whole-record snapshot over
concurrent work. Keep the workflow disabled until reset and readback finish.
