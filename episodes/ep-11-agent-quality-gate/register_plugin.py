"""Build, register, and verify the Episode 11 Dataverse plug-in.

Dry-run first:
    python register_plugin.py --dry-run
    python register_plugin.py --apply
    python register_plugin.py --verify
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import auth  # noqa: E402

EPISODE = "ep-11-agent-quality-gate"
SOLUTION = "LaunchControl"
ASSEMBLY = "QualityGateAutomation"
BPF_ENTITY = "new_bpf_ae8e29d7071f4eec9ef2a881a1590d5c"
QUALITY_GATE_PREFIX = "Quality Gate::"
PROJECT = (
    ROOT
    / "plugins"
    / ASSEMBLY
    / ASSEMBLY
    / f"{ASSEMBLY}.csproj"
)
DLL = PROJECT.parent / "bin" / "Release" / "net462" / f"{ASSEMBLY}.dll"
PLUGIN_TYPES = [
    "QualityGateAutomation.CreateQualityGateAssignmentPlugin",
    "QualityGateAutomation.ApplyQualityGateResultPlugin",
]
STEPS = [
    {
        "name": "Launch Approval: Create Quality Gate Assignment",
        "typename": PLUGIN_TYPES[0],
        "message": "Update",
        "entity": BPF_ENTITY,
        "filteringattributes": "activestageid",
        "description": (
            "Create one governed Agentic User task when Launch Approval "
            "enters Quality Gate."
        ),
    },
    {
        "name": "Quality Gate Result: Apply and Advance",
        "typename": PLUGIN_TYPES[1],
        "message": "Create",
        "entity": "lc_qualitygateresult",
        "filteringattributes": None,
        "description": (
            "Validate the agent assignment, project the result to Launch, "
            "and advance Passed results to Launch Approval."
        ),
    },
]


class Dataverse:
    def __init__(self) -> None:
        auth.load_env(EPISODE)
        self.url = os.environ["DATAVERSE_URL"].rstrip("/")
        self.api = self.url + "/api/data/v9.2"
        token = auth.get_token(EPISODE)
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        solution: bool = False,
    ) -> tuple[dict[str, Any], str | None]:
        headers = dict(self.headers)
        if solution:
            headers["MSCRM.SolutionName"] = SOLUTION
        response = requests.request(
            method,
            f"{self.api}/{path}",
            headers=headers,
            json=body,
            timeout=180,
        )
        if response.status_code not in (200, 201, 204):
            raise RuntimeError(
                f"{method} {path} failed ({response.status_code}): "
                f"{response.text[:1000]}"
            )
        payload = response.json() if response.content else {}
        entity_url = response.headers.get("OData-EntityId", "")
        entity_id = (
            entity_url.rsplit("(", 1)[-1].rstrip(")")
            if "(" in entity_url
            else None
        )
        return payload, entity_id

    def rows(
        self,
        table: str,
        *,
        filter: str,
        select: str,
        top: int = 5,
    ) -> list[dict[str, Any]]:
        path = (
            f"{table}?$select={select}&$filter={quote(filter, safe='(),$= ')}"
            f"&$top={top}"
        )
        payload, _ = self.request("GET", path)
        return payload.get("value", [])


def build() -> None:
    subprocess.run(
        ["dotnet", "build", str(PROJECT), "-c", "Release", "--nologo"],
        cwd=ROOT,
        check=True,
    )
    if not DLL.exists():
        raise RuntimeError(f"Build did not produce {DLL}")


def one(rows: list[dict[str, Any]], description: str) -> dict[str, Any]:
    if len(rows) != 1:
        raise RuntimeError(f"Expected exactly one {description}; got {len(rows)}")
    return rows[0]


def upsert_assembly(dv: Dataverse) -> str:
    content = base64.b64encode(DLL.read_bytes()).decode("ascii")
    rows = dv.rows(
        "pluginassemblies",
        filter=f"name eq '{ASSEMBLY}'",
        select="pluginassemblyid",
        top=2,
    )
    if rows:
        assembly_id = one(rows, "plug-in assembly")["pluginassemblyid"]
        dv.request(
            "PATCH",
            f"pluginassemblies({assembly_id})",
            {"content": content},
        )
        print("[ok] updated plug-in assembly")
        return assembly_id
    _, assembly_id = dv.request(
        "POST",
        "pluginassemblies",
        {
            "name": ASSEMBLY,
            "content": content,
            "isolationmode": 2,
            "sourcetype": 0,
            "description": (
                "Governed assignment and result automation for Episode 11."
            ),
        },
        solution=True,
    )
    if not assembly_id:
        raise RuntimeError("Plug-in assembly creation returned no ID")
    print("[ok] created plug-in assembly")
    return assembly_id


def upsert_types(dv: Dataverse, assembly_id: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for typename in PLUGIN_TYPES:
        rows = dv.rows(
            "plugintypes",
            filter=f"typename eq '{typename}'",
            select="plugintypeid,typename",
            top=2,
        )
        if rows:
            result[typename] = one(rows, f"plug-in type {typename}")[
                "plugintypeid"
            ]
            print(f"[skip] plug-in type exists: {typename}")
            continue
        _, type_id = dv.request(
            "POST",
            "plugintypes",
            {
                "typename": typename,
                "friendlyname": typename.rsplit(".", 1)[-1],
                "name": typename,
                "pluginassemblyid@odata.bind": (
                    f"/pluginassemblies({assembly_id})"
                ),
            },
            solution=True,
        )
        if not type_id:
            raise RuntimeError(f"Plug-in type creation returned no ID: {typename}")
        result[typename] = type_id
        print(f"[ok] created plug-in type: {typename}")
    return result


def message_and_filter(
    dv: Dataverse,
    message: str,
    entity: str,
) -> tuple[str, str]:
    message_row = one(
        dv.rows(
            "sdkmessages",
            filter=f"name eq '{message}'",
            select="sdkmessageid",
            top=2,
        ),
        f"SDK message {message}",
    )
    message_id = message_row["sdkmessageid"]
    filter_row = one(
        dv.rows(
            "sdkmessagefilters",
            filter=(
                f"primaryobjecttypecode eq '{entity}' "
                f"and _sdkmessageid_value eq {message_id}"
            ),
            select="sdkmessagefilterid",
            top=2,
        ),
        f"{entity}/{message} SDK message filter",
    )
    return message_id, filter_row["sdkmessagefilterid"]


def upsert_steps(
    dv: Dataverse, type_ids: dict[str, str]
) -> list[str]:
    step_ids: list[str] = []
    for step in STEPS:
        message_id, filter_id = message_and_filter(
            dv, step["message"], step["entity"]
        )
        rows = dv.rows(
            "sdkmessageprocessingsteps",
            filter=f"name eq '{step['name']}'",
            select="sdkmessageprocessingstepid",
            top=2,
        )
        behavior = {
            "description": step["description"],
            "mode": 0,
            "stage": 40,
            "rank": 1,
            "supporteddeployment": 0,
            "invocationsource": 0,
            "asyncautodelete": False,
        }
        if step["filteringattributes"]:
            behavior["filteringattributes"] = step["filteringattributes"]
        if rows:
            step_id = one(rows, f"step {step['name']}")[
                "sdkmessageprocessingstepid"
            ]
            dv.request(
                "PATCH",
                f"sdkmessageprocessingsteps({step_id})",
                behavior,
            )
            print(f"[ok] updated step: {step['name']}")
            step_ids.append(step_id)
            continue
        body = dict(behavior)
        body.update(
            {
                "name": step["name"],
                "plugintypeid@odata.bind": (
                    f"/plugintypes({type_ids[step['typename']]})"
                ),
                "sdkmessageid@odata.bind": f"/sdkmessages({message_id})",
                "sdkmessagefilterid@odata.bind": (
                    f"/sdkmessagefilters({filter_id})"
                ),
            }
        )
        _, step_id = dv.request(
            "POST",
            "sdkmessageprocessingsteps",
            body,
            solution=True,
        )
        if not step_id:
            raise RuntimeError(
                f"Step creation returned no ID: {step['name']}"
            )
        step_ids.append(step_id)
        print(f"[ok] created step: {step['name']}")
    return step_ids


def solution_id(dv: Dataverse) -> str:
    return one(
        dv.rows(
            "solutions",
            filter=f"uniquename eq '{SOLUTION}'",
            select="solutionid",
            top=2,
        ),
        f"solution {SOLUTION}",
    )["solutionid"]


def ensure_solution_component(
    dv: Dataverse,
    solution: str,
    component_id: str,
    component_type: int,
) -> None:
    rows = dv.rows(
        "solutioncomponents",
        filter=(
            f"_solutionid_value eq {solution} "
            f"and objectid eq {component_id} "
            f"and componenttype eq {component_type}"
        ),
        select="solutioncomponentid",
        top=1,
    )
    if rows:
        print(
            f"[skip] solution component exists: "
            f"{component_type}/{component_id}"
        )
        return
    dv.request(
        "POST",
        "AddSolutionComponent",
        {
            "ComponentId": component_id,
            "ComponentType": component_type,
            "SolutionUniqueName": SOLUTION,
            "AddRequiredComponents": True,
            "IncludedComponentSettingsValues": None,
        },
    )
    print(f"[ok] added solution component: {component_type}/{component_id}")


def regarding_launch_navigation_property(dv: Dataverse) -> str:
    headers = {
        "Authorization": dv.headers["Authorization"],
        "Accept": "application/xml",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    response = requests.get(
        f"{dv.api}/$metadata",
        headers=headers,
        timeout=90,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"GET $metadata failed ({response.status_code}): "
            f"{response.text[:500]}"
        )
    root = ET.fromstring(response.content)
    namespace = {"edm": "http://docs.oasis-open.org/odata/ns/edm"}
    task = root.find(".//edm:EntityType[@Name='task']", namespace)
    if task is None:
        raise RuntimeError("Dataverse $metadata contains no task entity type")
    matches = [
        node.get("Name")
        for node in task.findall("edm:NavigationProperty", namespace)
        if node.get("Type", "").endswith(".lc_launch")
    ]
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError(
            "Expected exactly one task Regarding navigation property for "
            "lc_launch"
        )
    return matches[0]


def backfill_quality_gate_task_regarding(dv: Dataverse) -> None:
    navigation = regarding_launch_navigation_property(dv)
    tasks = dv.rows(
        "tasks",
        filter=(
            f"startswith(subject,'{QUALITY_GATE_PREFIX}') "
            "and _regardingobjectid_value eq null"
        ),
        select="activityid,subject",
        top=500,
    )
    updated = 0
    for task in tasks:
        subject = task.get("subject", "")
        launch_id = subject[len(QUALITY_GATE_PREFIX):]
        launches = dv.rows(
            "lc_launchs",
            filter=f"lc_launchid eq {launch_id}",
            select="lc_launchid",
            top=1,
        )
        if not launches:
            print(
                f"[warn] skipped task {task['activityid']}: "
                "referenced Launch no longer exists"
            )
            continue
        dv.request(
            "PATCH",
            f"tasks({task['activityid']})",
            {f"{navigation}@odata.bind": f"/lc_launchs({launch_id})"},
        )
        updated += 1
    print(f"[ok] backfilled Regarding on {updated} Quality Gate task(s)")


def verify(dv: Dataverse) -> int:
    checks: list[tuple[str, bool]] = []
    assembly_rows = dv.rows(
        "pluginassemblies",
        filter=f"name eq '{ASSEMBLY}'",
        select="pluginassemblyid",
        top=2,
    )
    checks.append(("plug-in assembly", len(assembly_rows) == 1))
    assembly_id = (
        assembly_rows[0]["pluginassemblyid"]
        if len(assembly_rows) == 1
        else None
    )
    for typename in PLUGIN_TYPES:
        rows = dv.rows(
            "plugintypes",
            filter=f"typename eq '{typename}'",
            select="plugintypeid",
            top=2,
        )
        checks.append((typename, len(rows) == 1))
    for step in STEPS:
        rows = dv.rows(
            "sdkmessageprocessingsteps",
            filter=f"name eq '{step['name']}'",
            select="mode,stage,statecode,filteringattributes",
            top=2,
        )
        expected_filter = step["filteringattributes"] or None
        valid = (
            len(rows) == 1
            and rows[0].get("mode") == 0
            and rows[0].get("stage") == 40
            and rows[0].get("statecode") == 0
            and (rows[0].get("filteringattributes") or None)
            == expected_filter
        )
        checks.append((step["name"], valid))
    target_ids = [assembly_id] if assembly_id else []
    target_ids.extend(
        row["sdkmessageprocessingstepid"]
        for step in STEPS
        for row in dv.rows(
            "sdkmessageprocessingsteps",
            filter=f"name eq '{step['name']}'",
            select="sdkmessageprocessingstepid",
            top=2,
        )
    )
    solution = solution_id(dv)
    membership = all(
        bool(
            dv.rows(
                "solutioncomponents",
                filter=(
                    f"_solutionid_value eq {solution} "
                    f"and objectid eq {component_id}"
                ),
                select="solutioncomponentid",
                top=1,
            )
        )
        for component_id in target_ids
    )
    checks.append(
        ("LaunchControl plug-in solution membership", membership)
    )
    for label, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    return 0 if all(passed for _, passed in checks) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    dv = Dataverse()
    if args.verify:
        return verify(dv)

    print(f"Target: {dv.url}")
    print(f"Project: {PROJECT}")
    print(f"Assembly: {ASSEMBLY}")
    for step in STEPS:
        message_and_filter(dv, step["message"], step["entity"])
        print(
            f"[plan] {step['message']} {step['entity']} -> "
            f"{step['typename']}"
        )
    if args.dry_run:
        print("[dry-run] no Dataverse changes made")
        return 0

    build()
    assembly_id = upsert_assembly(dv)
    type_ids = upsert_types(dv, assembly_id)
    step_ids = upsert_steps(dv, type_ids)
    target_solution = solution_id(dv)
    ensure_solution_component(dv, target_solution, assembly_id, 91)
    for step_id in step_ids:
        ensure_solution_component(dv, target_solution, step_id, 92)
    backfill_quality_gate_task_regarding(dv)
    return verify(dv)


if __name__ == "__main__":
    raise SystemExit(main())
