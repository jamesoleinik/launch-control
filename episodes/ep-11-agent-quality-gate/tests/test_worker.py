from __future__ import annotations

import json
import sys
import tempfile
import unittest
from base64 import b64decode
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

EPISODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EPISODE_ROOT))

from agent.dataverse import (  # noqa: E402
    Assignment,
    DataverseClient,
    LaunchResearch,
)
from agent.identity import AgentTokenProvider  # noqa: E402
from agent.mailbox import MailboxClient  # noqa: E402
from agent.teams import TeamsNotifier  # noqa: E402
from agent.worker import process_assignment, run_once  # noqa: E402


class FakeResponse:
    def __init__(
        self,
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
        status_code: int = 200,
    ) -> None:
        self.payload = payload or {}
        self.headers = headers or {}
        self.status_code = status_code
        self.text = ""

    def json(self) -> dict:
        return self.payload


class FakeConfig:
    dataverse_url = "https://example.invalid"
    tenant_id = "00000000-0000-0000-0000-000000000000"
    agent_systemuser_id = "00000000-0000-0000-0000-000000000001"
    agent_mailbox = ""
    teams_recipient = ""
    launch_control_app_id = ""


class FakeClient(DataverseClient):
    def __init__(self, responses: list[FakeResponse]) -> None:
        super().__init__(FakeConfig(), lambda: "token")
        self.responses = responses
        self.calls: list[tuple[str, str, dict | None]] = []

    def _request(
        self, method: str, path: str, body=None, **_kwargs
    ) -> FakeResponse:
        self.calls.append((method, path, body))
        return self.responses.pop(0)


class DataverseClientTests(unittest.TestCase):
    def test_pending_assignment_parses_launch_context(self) -> None:
        launch_id = "00000000-0000-0000-0000-000000000002"
        client = FakeClient([
            FakeResponse({
                "value": [{
                    "activityid": "task-id",
                    "subject": f"Quality Gate::{launch_id}",
                    "@odata.etag": 'W/"123"',
                    "description": json.dumps({
                        "launch_id": launch_id,
                        "launch_name": "Test Launch",
                    }),
                }]
            })
        ])
        assignment = client.pending_assignments()[0]
        self.assertEqual(
            assignment,
            Assignment(
                task_id="task-id",
                launch_id=launch_id,
                launch_name="Test Launch",
                assignment_key=f"Quality Gate::{launch_id}",
                etag='W/"123"',
            ),
        )
        self.assertIn("statuscode eq 2", client.calls[0][1])

    def test_result_lookup_escapes_assignment_key(self) -> None:
        client = FakeClient([FakeResponse({"value": []})])
        self.assertFalse(client.result_exists("Quality Gate::O'Brien"))
        self.assertIn("O''Brien", client.calls[0][1])

    def test_claim_reports_etag_conflict(self) -> None:
        assignment = Assignment(
            task_id="task-id",
            launch_id="00000000-0000-0000-0000-000000000002",
            launch_name="Test",
            assignment_key="Quality Gate::test",
            etag='W/"123"',
        )
        client = FakeClient([FakeResponse(status_code=412)])
        self.assertFalse(client.claim(assignment))

    def test_verify_launch_access_requires_matching_record(self) -> None:
        assignment = Assignment(
            task_id="task-id",
            launch_id="00000000-0000-0000-0000-000000000002",
            launch_name="Test Launch",
            assignment_key="Quality Gate::test",
        )
        client = FakeClient([FakeResponse({
            "lc_launchid": assignment.launch_id,
            "lc_name": assignment.launch_name,
        })])
        self.assertEqual(
            client.verify_launch_access(assignment),
            assignment.launch_name,
        )
        self.assertIn(
            f"/lc_launchs({assignment.launch_id})",
            client.calls[0][1],
        )

    def test_request_uses_fresh_bearer_token(self) -> None:
        client = DataverseClient(FakeConfig(), lambda: "fresh-token")
        response = FakeResponse()
        with patch(
            "agent.dataverse.requests.request", return_value=response
        ) as request:
            client._request("GET", "/WhoAmI")
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"],
            "Bearer fresh-token",
        )

    def test_publish_evidence_attaches_screenshot_and_trace(self) -> None:
        assignment = Assignment(
            task_id="task-id",
            launch_id="00000000-0000-0000-0000-000000000002",
            launch_name="Test Launch",
            assignment_key="Quality Gate::test",
        )
        client = FakeClient([FakeResponse(), FakeResponse()])
        with tempfile.TemporaryDirectory() as directory:
            screenshot = Path(directory) / "evidence.png"
            trace = Path(directory) / "trace.zip"
            screenshot.write_bytes(b"png")
            trace.write_bytes(b"zip")
            client.publish_evidence(
                assignment,
                screenshot=screenshot,
                trace=trace,
            )

        self.assertEqual(len(client.calls), 2)
        screenshot_note = client.calls[0][2]
        trace_note = client.calls[1][2]
        self.assertIsNotNone(screenshot_note)
        self.assertIsNotNone(trace_note)
        assert screenshot_note is not None
        assert trace_note is not None
        self.assertEqual(screenshot_note["mimetype"], "image/png")
        self.assertEqual(b64decode(screenshot_note["documentbody"]), b"png")
        self.assertEqual(trace_note["mimetype"], "application/zip")
        self.assertEqual(b64decode(trace_note["documentbody"]), b"zip")
        self.assertIn(
            assignment.launch_id,
            trace_note["objectid_lc_launch@odata.bind"],
        )


class AgentTokenProviderTests(unittest.TestCase):
    @patch.dict(
        "os.environ",
        {
            "A365_BLUEPRINT_CLIENT_ID": "blueprint-client",
            "A365_BLUEPRINT_CLIENT_SECRET": "short-lived-secret",
            "A365_AGENT_ID": "agent-client",
            "A365_AGENT_USER_ID": "agent-user",
        },
        clear=True,
    )
    def test_agent_user_flow_uses_documented_three_exchanges(self) -> None:
        responses = [
            FakeResponse({"access_token": "t1", "expires_in": 3600}),
            FakeResponse({"access_token": "t2", "expires_in": 3600}),
            FakeResponse({"access_token": "resource", "expires_in": 3600}),
        ]
        provider = AgentTokenProvider(FakeConfig())
        with patch.object(
            provider.session, "post", side_effect=responses
        ) as post:
            self.assertEqual(provider(), "resource")
            self.assertEqual(provider(), "resource")

        self.assertEqual(post.call_count, 3)
        first = post.call_args_list[0].kwargs["data"]
        self.assertEqual(first["client_id"], "blueprint-client")
        self.assertEqual(first["fmi_path"], "agent-client")
        self.assertEqual(first["client_secret"], "short-lived-secret")
        second = post.call_args_list[1].kwargs["data"]
        self.assertEqual(second["client_id"], "agent-client")
        self.assertEqual(second["client_assertion"], "t1")
        third = post.call_args_list[2].kwargs["data"]
        self.assertEqual(third["grant_type"], "user_fic")
        self.assertEqual(third["client_assertion"], "t1")
        self.assertEqual(third["user_id"], "agent-user")
        self.assertEqual(third["user_federated_identity_credential"], "t2")
        self.assertEqual(
            third["scope"], "https://example.invalid/.default"
        )

    @patch.dict(
        "os.environ",
        {
            "A365_BLUEPRINT_CLIENT_ID": "blueprint-client",
            "A365_BLUEPRINT_CLIENT_SECRET": "secret-that-must-not-leak",
            "A365_AGENT_ID": "agent-client",
            "A365_AGENT_USER_ID": "agent-user",
        },
        clear=True,
    )
    def test_agent_user_flow_does_not_surface_secret_on_error(self) -> None:
        provider = AgentTokenProvider(FakeConfig())
        response = FakeResponse(
            {"error": "invalid_client"},
            status_code=401,
        )
        with patch.object(provider.session, "post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "invalid_client") as error:
                provider()
        self.assertNotIn("secret-that-must-not-leak", str(error.exception))


class WorkerTests(unittest.TestCase):
    def test_quality_check_exception_writes_error_then_completes(self) -> None:
        assignment = Assignment(
            task_id="task-id",
            launch_id="00000000-0000-0000-0000-000000000002",
            launch_name="Test",
            assignment_key="Quality Gate::test",
        )

        class Client:
            def __init__(self) -> None:
                self.events: list[object] = []

            def result_exists(self, _key: str) -> bool:
                return False

            def verify_launch_access(self, _assignment: Assignment) -> str:
                self.events.append("read")
                return _assignment.launch_name

            def research_launch(
                self, _assignment: Assignment
            ) -> LaunchResearch:
                self.events.append("research")
                return LaunchResearch(
                    launch={"lc_name": _assignment.launch_name},
                    milestones=[],
                    tasks=[],
                    status_updates=[],
                )

            def claim(self, _assignment: Assignment) -> bool:
                self.events.append("claim")
                return True

            def create_result(self, _assignment: Assignment, **result) -> str:
                self.events.append(result)
                return "result-id"

            def complete_task(self, _assignment: Assignment) -> None:
                self.events.append("complete")

        client = Client()
        span = SimpleNamespace(set_attribute=lambda *_args: None)
        with (
            patch(
                "agent.worker.run_quality_check",
                side_effect=RuntimeError("browser unavailable"),
            ),
            patch("agent.worker.configure_telemetry", return_value=object()),
            patch(
                "agent.worker.assignment_span",
                return_value=nullcontext(span),
            ),
            patch("agent.worker.log_event"),
        ):
            process_assignment(
                client,
                SimpleNamespace(quality_gate_url="https://example.invalid"),
                assignment,
            )

        self.assertEqual(client.events[0], "read")
        self.assertEqual(client.events[1], "claim")
        self.assertEqual(client.events[2], "research")
        self.assertEqual(client.events[3]["outcome"], "ERROR")
        self.assertEqual(client.events[4], "complete")

    def test_mail_notification_prioritizes_task_and_is_marked_read(self) -> None:
        first = Assignment(
            task_id="00000000-0000-0000-0000-000000000001",
            launch_id="00000000-0000-0000-0000-000000000011",
            launch_name="First",
            assignment_key="Quality Gate::first",
        )
        notified = Assignment(
            task_id="00000000-0000-0000-0000-000000000002",
            launch_id="00000000-0000-0000-0000-000000000012",
            launch_name="Notified",
            assignment_key="Quality Gate::notified",
        )

        class Client:
            def pending_assignments(self) -> list[Assignment]:
                return [first, notified]

        mailbox = SimpleNamespace(
            pending_notifications=lambda: [
                SimpleNamespace(
                    message_id="message-id", task_id=notified.task_id
                )
            ],
            mark_read=unittest.mock.Mock(),
        )
        processed = []
        with patch(
            "agent.worker.process_assignment",
            side_effect=(
                lambda _client, _config, assignment, _teams:
                processed.append(assignment.task_id)
            ),
        ):
            run_once(Client(), FakeConfig(), mailbox)

        self.assertEqual(processed, [notified.task_id, first.task_id])
        mailbox.mark_read.assert_called_once_with("message-id")


class MailboxClientTests(unittest.TestCase):
    def test_pending_notifications_ignores_malformed_subjects(self) -> None:
        task_id = "00000000-0000-0000-0000-000000000002"
        client = MailboxClient(
            "agent@example.com",
            SimpleNamespace(get_token=lambda _scope: "token"),
        )
        with patch.object(
            client,
            "_request",
            return_value=FakeResponse({
                "value": [
                    {
                        "id": "valid",
                        "subject": f"Launch Control quality gate::{task_id}",
                    },
                    {
                        "id": "invalid",
                        "subject": "Launch Control quality gate::not-a-guid",
                    },
                ]
            }),
        ):
            notifications = client.pending_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].task_id, task_id)


class TeamsNotifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assignment = Assignment(
            task_id="00000000-0000-0000-0000-000000000001",
            launch_id="00000000-0000-0000-0000-000000000002",
            launch_name="Q3 Widget Launch",
            assignment_key="Quality Gate::test",
        )
        self.config = SimpleNamespace(
            dataverse_url="https://example.crm.dynamics.com",
            teams_recipient="demo@example.com",
            launch_control_app_id=(
                "00000000-0000-0000-0000-000000000003"
            ),
        )
        self.provider = SimpleNamespace(
            get_token=unittest.mock.Mock(return_value="agent-token")
        )

    def test_pass_message_links_to_launch_approval_state(self) -> None:
        notifier = TeamsNotifier(
            self.config,
            self.provider,
            "00000000-0000-0000-0000-000000000004",
        )
        responses = [
            FakeResponse({"id": "chat-id"}, status_code=201),
            FakeResponse(
                {
                    "id": "message-id",
                    "from": {
                        "user": {
                            "id": (
                                "00000000-0000-0000-0000-000000000004"
                            )
                        }
                    },
                },
                status_code=201,
            ),
        ]
        with patch("agent.teams.requests.request", side_effect=responses) as call:
            result = notifier.send_completion(
                self.assignment,
                outcome="PASSED",
                score=93,
            )
        self.assertEqual(result.message_id, "message-id")
        self.assertIn("pagetype=entityrecord", result.launch_url)
        message = call.call_args_list[1].kwargs["json"]["body"]["content"]
        self.assertIn("Launch Approval", message)
        self.assertIn("Q3 Widget Launch", message)
        self.assertIn(result.launch_url.replace("&", "&amp;"), message)
        self.provider.get_token.assert_called_with(
            "https://graph.microsoft.com/.default"
        )

    def test_failed_message_links_to_quality_gate_state(self) -> None:
        notifier = TeamsNotifier(
            self.config,
            self.provider,
            "00000000-0000-0000-0000-000000000004",
        )
        responses = [
            FakeResponse({"id": "chat-id"}, status_code=201),
            FakeResponse(
                {
                    "id": "message-id",
                    "from": {
                        "user": {
                            "id": (
                                "00000000-0000-0000-0000-000000000004"
                            )
                        }
                    },
                },
                status_code=201,
            ),
        ]
        with patch("agent.teams.requests.request", side_effect=responses) as call:
            notifier.send_completion(
                self.assignment,
                outcome="FAILED",
                score=42,
            )
        message = call.call_args_list[1].kwargs["json"]["body"]["content"]
        self.assertIn("Quality Gate", message)
        self.assertIn("FAILED", message)



if __name__ == "__main__":
    unittest.main()
