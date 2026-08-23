from __future__ import annotations

import json
import base64
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import requests

from .config import Config
from .identity import TokenProvider

TASK_PREFIX = "Quality Gate::"
OUTCOME = {
    "PASSED": 106000000,
    "FAILED": 106000001,
    "NEEDS_REVIEW": 106000002,
    "ERROR": 106000003,
}


@dataclass(frozen=True)
class Assignment:
    task_id: str
    launch_id: str
    launch_name: str
    assignment_key: str
    etag: str = ""


@dataclass(frozen=True)
class LaunchResearch:
    launch: dict[str, Any]
    milestones: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    status_updates: list[dict[str, Any]]


class DataverseClient:
    def __init__(self, config: Config, token_provider: TokenProvider) -> None:
        self.config = config
        self.token_provider = token_provider
        self.api = config.dataverse_url + "/api/data/v9.2"

    def _headers(self, write: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token_provider()}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        if write:
            headers["Content-Type"] = "application/json"
        if os.environ.get(
            "QUALITY_GATE_IMPERSONATE_AGENT", ""
        ).lower() in {"1", "true", "yes"}:
            headers["MSCRMCallerID"] = self.config.agent_systemuser_id
        return headers

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
        allowed_statuses: tuple[int, ...] = (200, 201, 204),
    ) -> requests.Response:
        request_headers = self._headers(write=body is not None)
        if headers:
            request_headers.update(headers)
        response = requests.request(
            method,
            self.api + path,
            headers=request_headers,
            json=body,
            timeout=90,
        )
        if response.status_code not in allowed_statuses:
            raise RuntimeError(
                f"Dataverse {method} {path} failed "
                f"({response.status_code}): {response.text[:800]}"
            )
        return response

    def pending_assignments(self) -> list[Assignment]:
        owner = self.config.agent_systemuser_id
        query = (
            "/tasks?$select=activityid,subject,description,statuscode"
            f"&$filter=_ownerid_value eq {owner} and statecode eq 0 "
            "and statuscode eq 2 "
            f"and startswith(subject,'{TASK_PREFIX}')"
            "&$orderby=createdon asc"
        )
        rows = self._request("GET", query).json().get("value", [])
        assignments: list[Assignment] = []
        for row in rows:
            try:
                payload = json.loads(row.get("description") or "{}")
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Task {row['activityid']} has invalid JSON in description"
                ) from exc
            launch_id = str(payload.get("launch_id", "")).strip("{}")
            try:
                launch_id = str(UUID(launch_id))
            except ValueError as exc:
                raise RuntimeError(
                    f"Task {row['activityid']} has an invalid launch_id"
                ) from exc
            assignments.append(
                Assignment(
                    task_id=row["activityid"],
                    launch_id=launch_id,
                    launch_name=str(payload.get("launch_name", "Launch")),
                    assignment_key=row["subject"],
                    etag=row.get("@odata.etag", ""),
                )
            )
        return assignments

    def result_exists(self, assignment_key: str) -> bool:
        safe = assignment_key.replace("'", "''")
        query = (
            "/lc_qualitygateresults?$select=lc_qualitygateresultid"
            f"&$filter=lc_assignmentkey eq '{safe}'&$top=1"
        )
        return bool(self._request("GET", query).json().get("value"))

    def verify_launch_access(self, assignment: Assignment) -> str:
        launch = self._request(
            "GET",
            f"/lc_launchs({assignment.launch_id})"
            "?$select=lc_launchid,lc_name",
        ).json()
        actual_name = str(launch.get("lc_name", ""))
        if actual_name != assignment.launch_name:
            raise RuntimeError(
                "Assigned task Launch context does not match the accessible "
                "Launch record"
            )
        return actual_name

    def research_launch(self, assignment: Assignment) -> LaunchResearch:
        annotation = 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'
        headers = {"Prefer": annotation}
        launch = self._request(
            "GET",
            f"/lc_launchs({assignment.launch_id})"
            "?$select=lc_launchid,lc_name,lc_description,lc_code,"
            "lc_launchstatus,lc_priority,lc_targetdate,lc_releasewindow,"
            "lc_risksummary",
            headers=headers,
        ).json()
        milestones = self._request(
            "GET",
            "/lc_milestones"
            "?$select=lc_milestoneid,lc_name,lc_description,"
            "lc_milestonestatus,lc_duedate"
            f"&$filter=_lc_launchid_value eq {assignment.launch_id}"
            "&$orderby=lc_duedate asc",
            headers=headers,
        ).json().get("value", [])
        tasks = self._request(
            "GET",
            "/lc_tasks"
            "?$select=lc_taskid,lc_title,lc_notes,lc_taskstatus,"
            "lc_priority,lc_isblocked,lc_blockerreason,lc_duedate"
            f"&$filter=_lc_launchid_value eq {assignment.launch_id}"
            "&$orderby=lc_duedate asc",
            headers=headers,
        ).json().get("value", [])
        updates = self._request(
            "GET",
            "/lc_statusupdates"
            "?$select=lc_statusupdateid,lc_title,lc_summary,lc_health,"
            "lc_postedat"
            f"&$filter=_lc_launchid_value eq {assignment.launch_id}"
            "&$orderby=lc_postedat desc&$top=5",
            headers=headers,
        ).json().get("value", [])
        return LaunchResearch(
            launch=launch,
            milestones=milestones,
            tasks=tasks,
            status_updates=updates,
        )

    def claim(self, assignment: Assignment) -> bool:
        response = self._request(
            "PATCH",
            f"/tasks({assignment.task_id})",
            {
                "statuscode": 3,
                "actualstart": datetime.now(timezone.utc).isoformat(),
            },
            headers={"If-Match": assignment.etag} if assignment.etag else None,
            allowed_statuses=(204, 412),
        )
        return response.status_code == 204

    def create_result(
        self,
        assignment: Assignment,
        *,
        outcome: str,
        score: int,
        feedback: str,
        evidence: str,
    ) -> str:
        body = {
            "lc_name": f"{assignment.launch_name} quality gate",
            "lc_outcome": OUTCOME[outcome],
            "lc_score": score,
            "lc_checkedon": datetime.now(timezone.utc).isoformat(),
            "lc_feedback": feedback,
            "lc_evidence": evidence,
            "lc_assignmentkey": assignment.assignment_key,
            "lc_Launch@odata.bind": f"/lc_launchs({assignment.launch_id})",
        }
        response = self._request(
            "POST",
            "/lc_qualitygateresults",
            body,
            headers={"Prefer": "return=representation"},
        )
        entity_id = response.headers.get("OData-EntityId", "")
        if entity_id:
            return entity_id.rsplit("(", 1)[-1].rstrip(")")
        result_id = response.json().get("lc_qualitygateresultid")
        if not result_id:
            raise RuntimeError("Dataverse result creation returned no record id")
        return result_id

    def publish_remediation(
        self,
        assignment: Assignment,
        *,
        feedback: str,
        screenshot: Path,
    ) -> None:
        now = datetime.now(timezone.utc)
        due = (now + timedelta(days=3)).date().isoformat()
        self._request(
            "POST",
            "/lc_tasks",
            {
                "lc_title": "[Quality Gate] Resolve release telemetry validation",
                "lc_notes": (
                    "Created by the Quality Gate Agent after Playwright "
                    "validation of the release candidate."
                ),
                "lc_taskstatus": 10600303,
                "lc_isblocked": True,
                "lc_blockerreason": feedback[:2000],
                "lc_duedate": due,
                "lc_launchid@odata.bind": f"/lc_launchs({assignment.launch_id})",
            },
        )
        self._request(
            "POST",
            "/lc_statusupdates",
            {
                "lc_title": "Quality Gate risk identified",
                "lc_summary": (
                    "Agent browser validation found a release telemetry risk. "
                    "A blocked remediation task was created and the launch "
                    "should return to Draft."
                ),
                "lc_health": 10600602,
                "lc_postedat": now.isoformat(),
                "lc_launchid@odata.bind": f"/lc_launchs({assignment.launch_id})",
            },
        )
        self._request(
            "POST",
            "/annotations",
            {
                "subject": "Quality Gate browser evidence",
                "notetext": (
                    "The Quality Gate Agent found a release telemetry "
                    "validation failure and recommends returning to Draft. "
                    f"{feedback[:3000]}"
                ),
                "filename": screenshot.name,
                "mimetype": "image/png",
                "documentbody": base64.b64encode(
                    screenshot.read_bytes()
                ).decode("ascii"),
                "objectid_lc_launch@odata.bind": (
                    f"/lc_launchs({assignment.launch_id})"
                ),
            },
        )

    def complete_task(self, assignment: Assignment) -> None:
        self._request(
            "PATCH",
            f"/tasks({assignment.task_id})",
            {
                "statecode": 1,
                "statuscode": 5,
                "actualend": datetime.now(timezone.utc).isoformat(),
            },
        )
