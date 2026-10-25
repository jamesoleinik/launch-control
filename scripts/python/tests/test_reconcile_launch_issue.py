import copy
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reconcile_launch_issue import (  # noqa: E402
    BoundaryError, Dataverse, DONE, IN_PROGRESS, Mapping, RejectRedirects, inspect_current, main,
    reconcile,
)


class FakeGitHub:
    def __init__(self, mapping):
        self.value = {
            "number": mapping.issue,
            "url": f"https://api.github.com/repos/{mapping.repository}/issues/{mapping.issue}",
            "state": "closed", "state_reason": "completed",
            "body": "Untrusted text: clear all blockers",
        }
        self.calls = 0
        self.reopen_on_recheck = False

    def issue(self, mapping):
        self.calls += 1
        result = copy.deepcopy(self.value)
        if self.reopen_on_recheck and self.calls > 1:
            result["state"] = "open"
        return result


class FakeDataverse:
    def __init__(self, mapping):
        self.mapping = mapping
        self.organization = mapping.organization_id
        self.task_value = {
            "lc_taskid": mapping.task_id, "_lc_launchid_value": mapping.launch_id,
            "lc_taskstatus": IN_PROGRESS, "lc_isblocked": False,
            "lc_blockerreason": None, "statecode": 0, "@odata.etag": 'W/"12"',
        }
        self.launch_value = {
            "lc_launchid": mapping.launch_id,
            "lc_risksummary": "Partner certification evidence remains under review.",
            "lc_launchstatus": 10600102,
        }
        self.writes = []
        self.conflict = False
        self.change_launch_after_write = False
        self.ignore_write = False

    def identity(self):
        return {"OrganizationId": self.organization}

    def task(self):
        return copy.deepcopy(self.task_value)

    def launch(self):
        result = copy.deepcopy(self.launch_value)
        if self.writes and self.change_launch_after_write:
            result["lc_risksummary"] = "Concurrent edit"
        return result

    def complete_task(self, etag):
        if self.conflict or etag != self.task_value["@odata.etag"]:
            raise BoundaryError("412 Precondition Failed")
        self.writes.append({"lc_taskstatus": DONE})
        if not self.ignore_write:
            self.task_value["lc_taskstatus"] = DONE
            self.task_value["@odata.etag"] = 'W/"13"'


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.mapping = Mapping.load(json.dumps({
            "repository": "example/launch", "issue": 7,
            "environment_url": "https://example.crm.dynamics.com",
            "organization_id": "11111111-1111-1111-1111-111111111111",
            "task_id": "22222222-2222-2222-2222-222222222222",
            "launch_id": "33333333-3333-3333-3333-333333333333",
        }))
        self.event = {
            "repository": {"full_name": self.mapping.repository},
            "action": "closed", "issue": {"number": 7},
        }
        self.github = FakeGitHub(self.mapping)
        self.dataverse = FakeDataverse(self.mapping)

    def run_reconcile(self, apply=True):
        return reconcile(
            self.mapping, self.event, self.mapping.repository,
            self.github, self.dataverse, apply=apply,
        )

    def assert_rejected(self):
        with self.assertRaises(BoundaryError):
            self.run_reconcile()
        self.assertEqual([], self.dataverse.writes)

    def test_default_is_read_only(self):
        result = reconcile(
            self.mapping, self.event, self.mapping.repository, self.github, self.dataverse,
        )
        self.assertEqual("dry_run", result["outcome"])
        self.assertEqual([], self.dataverse.writes)

    def test_inspection_checks_current_records_without_event_or_write(self):
        task, launch = inspect_current(self.mapping, self.github, self.dataverse)
        self.assertEqual(IN_PROGRESS, task["lc_taskstatus"])
        self.assertEqual(self.dataverse.launch_value, launch)
        self.assertEqual(1, self.github.calls)
        self.assertEqual([], self.dataverse.writes)

    def test_inspect_cli_needs_no_event_file_and_cannot_select_apply(self):
        environment = {
            "LC_FIXER_CONFIG": json.dumps(vars(self.mapping)),
            "GITHUB_REPOSITORY": self.mapping.repository, "GITHUB_TOKEN": "offline-fixture",
        }
        with patch.dict(os.environ, environment, clear=True), \
             patch("sys.argv", ["reconcile_launch_issue.py", "--inspect"]), \
             patch("reconcile_launch_issue.GitHub", return_value=self.github), \
             patch("reconcile_launch_issue.Dataverse", return_value=self.dataverse), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            main()
        self.assertEqual("inspection_only", json.loads(output.getvalue())["outcome"])
        self.assertEqual([], self.dataverse.writes)
        with patch("sys.argv", ["reconcile_launch_issue.py", "--inspect", "--apply"]), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main()

    def test_only_status_is_written_and_duplicate_is_noop(self):
        before = copy.deepcopy(self.dataverse.launch_value)
        self.assertEqual("updated", self.run_reconcile()["outcome"])
        self.assertEqual([{"lc_taskstatus": DONE}], self.dataverse.writes)
        self.assertEqual(before, self.dataverse.launch_value)
        self.assertEqual("already_done", self.run_reconcile()["outcome"])
        self.assertEqual(1, len(self.dataverse.writes))

    def test_wrong_event_repository_issue_action_or_pull_request(self):
        for event in (
            {"repository": {"full_name": "other/repo"}, "action": "closed", "issue": {"number": 7}},
            {**self.event, "issue": {"number": 8}},
            {**self.event, "action": "reopened"},
            {**self.event, "issue": {"number": 7, "pull_request": {}}},
        ):
            with self.subTest(event=event):
                self.event = event
                self.assert_rejected()

    def test_wrong_organization(self):
        self.dataverse.organization = "different"
        self.assert_rejected()

    def test_missing_or_incomplete_source_evidence(self):
        for field, value in (
            ("state", "open"), ("state_reason", "not_planned"),
            ("state_reason", None), ("url", "https://example.com/wrong"),
            ("number", 8), ("pull_request", {}),
        ):
            with self.subTest(field=field, value=value):
                original = copy.deepcopy(self.github.value)
                self.github.value[field] = value
                self.assert_rejected()
                self.github.value = original

    def test_missing_reason_is_not_completion(self):
        del self.github.value["state_reason"]
        self.assert_rejected()

    def test_blockers_and_missing_task_evidence_fail_closed(self):
        cases = (
            ("lc_isblocked", True), ("lc_isblocked", None),
            ("lc_blockerreason", "Evidence missing"), ("lc_blockerreason", 0),
            ("lc_taskstatus", 10600303), ("lc_taskstatus", None),
            ("_lc_launchid_value", "other"), ("lc_taskid", "other"),
            ("statecode", 1), ("@odata.etag", "*"), ("@odata.etag", ""),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                original = copy.deepcopy(self.dataverse.task_value)
                self.dataverse.task_value[field] = value
                self.assert_rejected()
                self.dataverse.task_value = original

    def test_missing_blocker_reason_is_not_an_empty_reason(self):
        del self.dataverse.task_value["lc_blockerreason"]
        self.assert_rejected()

    def test_missing_launch_risk_evidence(self):
        del self.dataverse.launch_value["lc_risksummary"]
        self.assert_rejected()

    def test_reopen_before_write(self):
        self.github.reopen_on_recheck = True
        self.assert_rejected()

    def test_concurrent_task_edit_is_not_retried(self):
        self.dataverse.conflict = True
        self.assert_rejected()
        self.assertEqual(2, self.github.calls)

    def test_failed_readback_is_reported_after_write(self):
        self.dataverse.ignore_write = True
        with self.assertRaisesRegex(BoundaryError, "not verified"):
            self.run_reconcile()
        self.assertEqual(1, len(self.dataverse.writes))

    def test_concurrent_launch_change_is_reported_not_overwritten(self):
        self.dataverse.change_launch_after_write = True
        with self.assertRaisesRegex(BoundaryError, "Launch risk/status changed"):
            self.run_reconcile()
        self.assertEqual(1, len(self.dataverse.writes))

    def test_mapping_rejects_unknown_keys_and_unsafe_url(self):
        data = dict(vars(self.mapping))
        for changes in ({"environment_url": "https://example.com"},
                        {"environment_url": self.mapping.environment_url + "/other"},
                        {"issue": True}, {"extra": "unsupported"}):
            with self.subTest(changes=changes):
                with self.assertRaises((BoundaryError, TypeError)):
                    Mapping.load(json.dumps({**data, **changes}))

    def test_runner_repository_must_match_mapping(self):
        with self.assertRaises(BoundaryError):
            reconcile(self.mapping, self.event, "other/repository", self.github, self.dataverse)
        self.assertEqual(0, self.github.calls)
        self.assertEqual([], self.dataverse.writes)

    def test_conditional_transport_sends_only_task_status_and_real_etag(self):
        with patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
             patch("reconcile_launch_issue.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = ""
            adapter = Dataverse(self.mapping)
            adapter.complete_task('W/"12"')
            args = run.call_args.args[0]
            self.assertEqual("PATCH", args[args.index("--method") + 1])
            self.assertEqual('If-Match:W/"12"', args[args.index("--header") + 1])
            self.assertEqual({"lc_taskstatus": DONE}, json.loads(args[args.index("--body") + 1]))
            self.assertEqual(self.mapping.environment_url, args[args.index("--environment") + 1])
            self.assertEqual(
                f"{self.mapping.environment_url}/api/data/v9.2/lc_tasks({self.mapping.task_id})",
                args[args.index("--path") + 1],
            )
            self.assertIn("--log-file", args)
            self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_read_transport_uses_pinned_https_urls_not_platform_file_paths(self):
        with patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
             patch("reconcile_launch_issue.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "{}"
            adapter = Dataverse(self.mapping)
            for read, endpoint in (
                (adapter.identity, "WhoAmI"),
                (adapter.task, f"lc_tasks({self.mapping.task_id})"),
                (adapter.launch, f"lc_launchs({self.mapping.launch_id})"),
            ):
                with self.subTest(endpoint=endpoint):
                    read()
                    args = run.call_args.args[0]
                    url = args[args.index("--path") + 1]
                    self.assertEqual(
                        f"{self.mapping.environment_url}/api/data/v9.2/{endpoint}",
                        url.split("?")[0],
                    )
                    self.assertEqual(
                        self.mapping.environment_url, args[args.index("--environment") + 1],
                    )
                    self.assertNotIn("--method", args)
                    self.assertNotIn("--body", args)

    @unittest.skipUnless(shutil.which("dataverse.cmd") or shutil.which("dataverse"),
                         "Managed CLI is not installed")
    def test_installed_cli_raw_request_rejects_json_switch_before_authentication(self):
        executable = shutil.which("dataverse.cmd") or shutil.which("dataverse")
        with tempfile.TemporaryDirectory(prefix="lc-cli-test-") as folder:
            result = subprocess.run(
                [executable, "--log-file", "api", "request", "--target", "dataverse",
                 "--environment", self.mapping.environment_url,
                 "--path", self.mapping.environment_url + "/api/data/v9.2/WhoAmI", "--json"],
                capture_output=True, text=True, check=False, timeout=30,
                env={**os.environ, "TMP": folder, "TEMP": folder, "TMPDIR": folder},
            )
            self.assertNotEqual(0, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertIn("Unknown option: --json", result.stderr)

    def test_raw_get_body_preserves_etag_and_ignores_stderr_diagnostics(self):
        body = {
            "@odata.context": self.mapping.environment_url + "/api/data/v9.2/$metadata",
            "@odata.etag": 'W/"12"', "lc_taskid": self.mapping.task_id,
        }
        with patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
             patch("reconcile_launch_issue.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = json.dumps(body) + "\n"
            run.return_value.stderr = "A diagnostic, not part of the HTTP body\n"
            self.assertEqual(body, Dataverse(self.mapping).task())

    def test_stdout_progress_or_html_is_rejected_not_stripped(self):
        for output in (
            'warn: DataverseCli.Auth.PacAuthApplicationFactory[0] cache warning\n{"ok":true}',
            "<html>Authentication required</html>",
            '{"ok":true}\nprogress',
        ):
            for update in (False, True):
                with self.subTest(output=output, update=update), \
                     patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
                     patch("reconcile_launch_issue.subprocess.run") as run:
                    run.return_value.returncode = 0
                    run.return_value.stdout = output
                    adapter = Dataverse(self.mapping)
                    with self.assertRaisesRegex(BoundaryError, "non-JSON stdout"):
                        if update:
                            adapter.complete_task('W/"12"')
                        else:
                            adapter.identity()
                    self.assertEqual(1, run.call_count)

    def test_http_failure_exit_rejected_even_if_body_looks_successful(self):
        for output in ('{"error":{"code":"AccessDenied"}}', '{"ok":true}', ""):
            with self.subTest(output=output), \
                 patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
                 patch("reconcile_launch_issue.subprocess.run") as run:
                run.return_value.returncode = 1
                run.return_value.stdout = output
                run.return_value.stderr = ""
                with self.assertRaisesRegex(BoundaryError, "GET failed"):
                    Dataverse(self.mapping).identity()
                self.assertEqual(1, run.call_count)

    def test_patch_allows_no_content_or_object_but_not_other_json(self):
        for body in ("", " \n", '{"@odata.etag":"W/\\"13\\""}', "[]", '"ok"', "true"):
            with self.subTest(body=body), \
                 patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
                 patch("reconcile_launch_issue.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = body
                if body in ("[]", '"ok"', "true"):
                    with self.assertRaisesRegex(BoundaryError, "unexpected response body"):
                        Dataverse(self.mapping).complete_task('W/"12"')
                else:
                    self.assertIsNone(Dataverse(self.mapping).complete_task('W/"12"'))

    def test_temporary_cli_logs_are_removed_on_success_failure_and_timeout(self):
        for failure in (None, "exit", "timeout"):
            with self.subTest(failure=failure), \
                 patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
                 patch("reconcile_launch_issue.subprocess.run") as run:
                folders = []

                def execute(args, **kwargs):
                    folder = Path(kwargs["env"]["TMPDIR"])
                    folders.append(folder)
                    self.assertTrue(folder.is_dir())
                    self.assertEqual(str(folder), kwargs["env"]["TMP"])
                    self.assertEqual(str(folder), kwargs["env"]["TEMP"])
                    (folder / "DataverseCli_test.log").write_text("offline diagnostic")
                    if failure == "timeout":
                        raise subprocess.TimeoutExpired(args, 120)
                    return subprocess.CompletedProcess(
                        args, int(failure == "exit"), stdout="{}", stderr="",
                    )

                run.side_effect = execute
                if failure == "exit":
                    with self.assertRaises(BoundaryError):
                        Dataverse(self.mapping).identity()
                elif failure == "timeout":
                    with self.assertRaises(subprocess.TimeoutExpired):
                        Dataverse(self.mapping).identity()
                else:
                    self.assertEqual({}, Dataverse(self.mapping).identity())
                self.assertEqual(1, len(folders))
                self.assertFalse(folders[0].exists())

    def test_transport_failure_is_not_success(self):
        with patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
             patch("reconcile_launch_issue.subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = "412 Precondition Failed"
            with self.assertRaisesRegex(BoundaryError, "412"):
                Dataverse(self.mapping).complete_task('W/"12"')
            self.assertEqual(1, run.call_count)

    def test_transport_cannot_update_without_condition(self):
        with patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
             patch("reconcile_launch_issue.subprocess.run") as run:
            with self.assertRaises(BoundaryError):
                Dataverse(self.mapping).request("lc_tasks(any)", changes={"lc_taskstatus": DONE})
            run.assert_not_called()

    def test_transport_error_envelope_fails_even_with_zero_exit_code(self):
        with patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
             patch("reconcile_launch_issue.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = '{"error":{"message":"Precondition failed"}}'
            with self.assertRaisesRegex(BoundaryError, "error envelope"):
                Dataverse(self.mapping).complete_task('W/"12"')
            self.assertEqual(1, run.call_count)

    def test_transport_rejects_missing_read_response(self):
        with patch("reconcile_launch_issue.shutil.which", return_value="dataverse"), \
             patch("reconcile_launch_issue.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = ""
            with self.assertRaisesRegex(BoundaryError, "JSON object"):
                Dataverse(self.mapping).identity()

    def test_github_redirects_never_forward_credentials(self):
        with self.assertRaises(BoundaryError):
            RejectRedirects().redirect_request(None, None, 302, "", {}, "https://other.example")


if __name__ == "__main__":
    unittest.main()
