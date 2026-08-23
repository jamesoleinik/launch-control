"""Create and verify standard Dataverse business process flows."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from html import escape
from pathlib import Path
from typing import Any

import requests
from azure.identity import AzureCliCredential
from PowerPlatform.Dataverse.client import DataverseClient
from PowerPlatform.Dataverse.core.config import OperationContext


CLASS_IDS = {
    "Boolean": "3ef39988-22bb-4f0b-bbbe-64b5a3748aee",
    "Customer": "270bd3db-d9af-4782-9025-509e298dec0a",
    "DateTime": "5b773807-9fb2-42db-97c3-7a91eff8adff",
    "Decimal": "c6d124ca-7eda-4a60-aea9-7fb8d318b68f",
    "Double": "c6d124ca-7eda-4a60-aea9-7fb8d318b68f",
    "Integer": "c6d124ca-7eda-4a60-aea9-7fb8d318b68f",
    "Lookup": "270bd3db-d9af-4782-9025-509e298dec0a",
    "Memo": "4273edbd-ac1d-40d3-9fb2-095c621b552d",
    "Money": "c6d124ca-7eda-4a60-aea9-7fb8d318b68f",
    "Owner": "270bd3db-d9af-4782-9025-509e298dec0a",
    "Picklist": "3ef39988-22bb-4f0b-bbbe-64b5a3748aee",
    "State": "3ef39988-22bb-4f0b-bbbe-64b5a3748aee",
    "Status": "3ef39988-22bb-4f0b-bbbe-64b5a3748aee",
    "String": "4273edbd-ac1d-40d3-9fb2-095c621b552d",
}
URL_CLASS_ID = "71716b6c-711e-476c-8ab8-5d11542bfb47"


def guid() -> str:
    return str(uuid.uuid4())


def read_spec(path: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    required = ("name", "unique_name", "table", "solution", "stages")
    missing = [name for name in required if not spec.get(name)]
    if missing:
        raise ValueError(f"Missing spec properties: {', '.join(missing)}")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", spec["unique_name"]):
        raise ValueError("unique_name must be a valid Dataverse logical name")
    if not isinstance(spec["stages"], list) or not spec["stages"]:
        raise ValueError("stages must be a non-empty array")
    return spec


def credential() -> AzureCliCredential:
    tenant = os.environ.get("TENANT_ID")
    return AzureCliCredential(tenant_id=tenant, process_timeout=60)


def client_for(url: str) -> DataverseClient:
    context = OperationContext("app=dataverse-bpf-builder/1.0")
    return DataverseClient(url, credential(), context=context)


def attribute_catalog(client: DataverseClient, table: str) -> dict[str, dict[str, Any]]:
    columns = client.tables.list_columns(table)
    return {
        row["LogicalName"]: row
        for row in columns
        if row.get("LogicalName") and row.get("AttributeOf") is None
    }


def solution_exists(client: DataverseClient, unique_name: str) -> bool:
    rows = client.records.list(
        "solution",
        filter=f"uniquename eq '{unique_name.replace(chr(39), chr(39) * 2)}'",
        select=["solutionid", "ismanaged"],
        top=1,
    )
    return bool(rows) and not bool(rows[0].get("ismanaged"))


def resolve_roles(
    client: DataverseClient, role_names: list[str]
) -> dict[str, str]:
    if not role_names:
        return {}
    clauses = [
        f"name eq '{name.replace(chr(39), chr(39) * 2)}'"
        for name in role_names
    ]
    rows = client.records.list(
        "role",
        filter=" or ".join(clauses),
        select=["roleid", "name"],
    )
    by_name = {row["name"]: row["roleid"] for row in rows}
    missing = [name for name in role_names if name not in by_name]
    if missing:
        raise ValueError(f"Security roles not found: {', '.join(missing)}")
    return by_name


def resolve_app(client: DataverseClient, unique_name: str | None):
    if not unique_name:
        return None
    escaped = unique_name.replace("'", "''")
    rows = client.records.list(
        "appmodule",
        filter=f"uniquename eq '{escaped}'",
        select=["appmoduleid", "appmoduleidunique", "name", "uniquename"],
        top=1,
    )
    if not rows:
        raise ValueError(f"Model-driven app {unique_name!r} was not found")
    return rows[0]


def control_class(column: dict[str, Any]) -> str:
    kind = column.get("AttributeType")
    if kind == "String":
        format_name = column.get("FormatName")
        if isinstance(format_name, dict):
            format_name = format_name.get("Value")
        if str(format_name).lower() == "url":
            return URL_CLASS_ID
    if kind not in CLASS_IDS:
        raise ValueError(
            f"Unsupported BPF field type {kind!r} for {column.get('LogicalName')}"
        )
    return CLASS_IDS[kind]


def validate_spec(
    client: DataverseClient, spec: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    if not solution_exists(client, spec["solution"]):
        raise ValueError(
            f"Unmanaged solution {spec['solution']!r} was not found"
        )
    columns = attribute_catalog(client, spec["table"])
    resolve_roles(client, list(spec.get("security_roles", [])))
    resolve_app(client, spec.get("app_unique_name"))
    duplicate_ok = bool(spec.get("allow_duplicate_fields", False))
    for stage in spec["stages"]:
        if not stage.get("name"):
            raise ValueError("Every stage requires a name")
        if not isinstance(stage.get("steps"), list):
            raise ValueError(f"Stage {stage['name']!r} requires a steps array")
        seen: set[str] = set()
        for step in stage["steps"]:
            field = step.get("field")
            if not field or field not in columns:
                raise ValueError(
                    f"Stage {stage['name']!r} references missing field {field!r}"
                )
            if field in seen and not duplicate_ok:
                raise ValueError(
                    f"Stage {stage['name']!r} repeats field {field!r}"
                )
            seen.add(field)
            control_class(columns[field])
    return columns


def build_model(
    spec: dict[str, Any], columns: dict[str, dict[str, Any]]
) -> tuple[str, str, str]:
    workflow_id = guid()
    language = int(spec.get("language_code", 1033))
    counter = 0

    def sid(prefix: str) -> str:
        nonlocal counter
        value = f"{prefix}{counter}"
        counter += 1
        return value

    stages: list[dict[str, Any]] = []
    for stage_spec in spec["stages"]:
        stage_id = guid()
        steps: list[dict[str, Any]] = []
        for step_spec in stage_spec["steps"]:
            step_id = guid()
            field = step_spec["field"]
            column = columns[field]
            display = column.get("DisplayName", {})
            display_label = (
                display.get("UserLocalizedLabel", {}).get("Label")
                if isinstance(display, dict)
                else None
            ) or field
            steps.append(
                {
                    "node_id": sid("StepStep"),
                    "control_node_id": sid("ControlStep"),
                    "id": step_id,
                    "label": step_spec.get("label") or display_label,
                    "field": field,
                    "display": display_label,
                    "required": bool(step_spec.get("required", False)),
                    "class_id": control_class(column),
                }
            )
        stages.append(
            {
                "entity_node_id": sid("EntityStep"),
                "node_id": sid("StageStep"),
                "id": stage_id,
                "name": stage_spec["name"],
                "category": int(stage_spec.get("category", -1)),
                "steps": steps,
            }
        )
    for index, stage in enumerate(stages):
        stage["next_id"] = stages[index + 1]["id"] if index + 1 < len(stages) else None

    client_steps: list[dict[str, Any]] = [
        {
            "__class": "RelationshipCollectionStep:#Microsoft.Crm.Workflow.ObjectModel",
            "id": "RelationshipCollectionStep0",
            "description": "",
            "name": "Step_0",
            "stepLabels": {"list": []},
            "steps": {"list": []},
        }
    ]
    for stage in stages:
        child_steps = []
        for step in stage["steps"]:
            child_steps.append(
                {
                    "__class": "StepStep:#Microsoft.Crm.Workflow.ObjectModel",
                    "id": step["node_id"],
                    "description": "New Step",
                    "name": step["node_id"],
                    "stepLabels": {
                        "list": [
                            {
                                "labelId": step["id"],
                                "languageCode": language,
                                "description": step["label"],
                            }
                        ]
                    },
                    "steps": {
                        "list": [
                            {
                                "__class": "ControlStep:#Microsoft.Crm.Workflow.ObjectModel",
                                "id": step["control_node_id"],
                                "description": "",
                                "name": step["control_node_id"],
                                "stepLabels": {"list": []},
                                "controlId": step["field"],
                                "classId": step["class_id"],
                                "dataFieldName": step["field"],
                                "systemStepType": "IdentifyContact",
                                "isSystemControl": False,
                                "parameters": "",
                                "controlDisplayName": step["display"],
                                "isUnbound": False,
                                "controlType": "0",
                            }
                        ]
                    },
                    "stepStepId": step["id"],
                    "isProcessRequired": step["required"],
                    "isHidden": False,
                }
            )
        client_steps.append(
            {
                "__class": "EntityStep:#Microsoft.Crm.Workflow.ObjectModel",
                "id": stage["entity_node_id"],
                "description": spec["table"],
                "name": stage["entity_node_id"],
                "stepLabels": {"list": []},
                "steps": {
                    "list": [
                        {
                            "__class": "StageStep:#Microsoft.Crm.Workflow.ObjectModel",
                            "id": stage["node_id"],
                            "description": stage["name"],
                            "name": stage["node_id"],
                            "stepLabels": {
                                "list": [
                                    {
                                        "labelId": stage["id"],
                                        "languageCode": language,
                                        "description": stage["name"],
                                    }
                                ]
                            },
                            "steps": {"list": child_steps},
                            "stageId": stage["id"],
                            "nextStageId": stage["next_id"],
                            "stageCategory": str(stage["category"]),
                        }
                    ]
                },
                "relationshipName": None,
                "attributeName": None,
                "isClosedLoop": False,
            }
        )
    clientdata = {
        "__class": "WorkflowStep:#Microsoft.Crm.Workflow.ObjectModel",
        "id": "WorkflowStep0",
        "description": "",
        "name": "Step_0",
        "stepLabels": {"list": []},
        "steps": {"list": client_steps},
        "primaryEntityName": spec["table"],
        "nextStepIndex": counter,
        "isCrmUIWorkflow": True,
        "category": 4,
        "businessProcessType": 0,
        "mode": 0,
        "title": spec["name"],
        "description": "",
        "workflowEntityId": workflow_id,
        "formId": None,
        "argumentsArray": [],
        "variables": [],
        "inputs": [],
    }
    xaml = render_xaml(workflow_id, spec["table"], stages, language)
    return workflow_id, json.dumps(clientdata, separators=(",", ":")), xaml


def render_xaml(
    workflow_id: str,
    table: str,
    stages: list[dict[str, Any]],
    language: int,
) -> str:
    entity_xml = []
    for stage in stages:
        step_xml = []
        for step in stage["steps"]:
            required = "True" if step["required"] else "False"
            step_xml.append(
                f"""
                <mxswa:ActivityReference AssemblyQualifiedName="Microsoft.Crm.Workflow.Activities.StepComposite, Microsoft.Crm.Workflow, Version=9.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35" DisplayName="{escape(step['node_id'])}: New Step">
                  <mxswa:ActivityReference.Properties>
                    <sco:Collection x:TypeArguments="Variable" x:Key="Variables" />
                    <sco:Collection x:TypeArguments="Activity" x:Key="Activities">
                      <Sequence DisplayName="{escape(step['control_node_id'])}">
                        <mcwb:Control ClassId="{step['class_id']}" ControlDisplayName="{escape(step['display'])}" ControlId="{escape(step['field'])}" DataFieldName="{escape(step['field'])}" IsSystemControl="False" IsUnbound="False" SystemStepType="0">
                          <mcwb:Control.Parameters><InArgument x:TypeArguments="x:String"><Literal x:TypeArguments="x:String" Value="" /></InArgument></mcwb:Control.Parameters>
                        </mcwb:Control>
                      </Sequence>
                    </sco:Collection>
                    <sco:Collection x:TypeArguments="mcwo:StepLabel" x:Key="StepLabels"><mcwo:StepLabel Description="{escape(step['label'])}" LabelId="{step['id']}" LanguageCode="{language}" /></sco:Collection>
                    <x:String x:Key="ProcessStepId">{step['id']}</x:String>
                    <x:Boolean x:Key="IsProcessRequired">{required}</x:Boolean>
                  </mxswa:ActivityReference.Properties>
                </mxswa:ActivityReference>"""
            )
        next_xml = (
            f"<x:String x:Key=\"NextStageId\">{stage['next_id']}</x:String>"
            if stage["next_id"]
            else '<x:Null x:Key="NextStageId" />'
        )
        entity_xml.append(
            f"""
    <mxswa:ActivityReference AssemblyQualifiedName="Microsoft.Crm.Workflow.Activities.EntityComposite, Microsoft.Crm.Workflow, Version=9.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35" DisplayName="{escape(stage['entity_node_id'])}: {escape(table)}">
      <mxswa:ActivityReference.Properties>
        <sco:Collection x:TypeArguments="Variable" x:Key="Variables" />
        <sco:Collection x:TypeArguments="Activity" x:Key="Activities">
          <mxswa:ActivityReference AssemblyQualifiedName="Microsoft.Crm.Workflow.Activities.StageComposite, Microsoft.Crm.Workflow, Version=9.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35" DisplayName="{escape(stage['node_id'])}: {escape(stage['name'])}">
            <mxswa:ActivityReference.Properties>
              <sco:Collection x:TypeArguments="Variable" x:Key="Variables" />
              <sco:Collection x:TypeArguments="Activity" x:Key="Activities">{''.join(step_xml)}
              </sco:Collection>
              <sco:Collection x:TypeArguments="mcwo:StepLabel" x:Key="StepLabels"><mcwo:StepLabel Description="{escape(stage['name'])}" LabelId="{stage['id']}" LanguageCode="{language}" /></sco:Collection>
              <x:String x:Key="StageId">{stage['id']}</x:String>
              <x:String x:Key="StageCategory">{stage['category']}</x:String>
              {next_xml}
            </mxswa:ActivityReference.Properties>
          </mxswa:ActivityReference>
        </sco:Collection>
        <x:Null x:Key="RelationshipName" />
        <x:Null x:Key="AttributeName" />
        <x:Boolean x:Key="IsClosedLoop">False</x:Boolean>
      </mxswa:ActivityReference.Properties>
    </mxswa:ActivityReference>"""
        )
    class_name = "XrmWorkflow" + workflow_id.replace("-", "")
    return f"""<Activity x:Class="{class_name}" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" xmlns:mcwb="clr-namespace:Microsoft.Crm.Workflow.BusinessProcessFlowActivities;assembly=Microsoft.Crm.Workflow, Version=9.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35" xmlns:mcwo="clr-namespace:Microsoft.Crm.Workflow.ObjectModel;assembly=Microsoft.Crm, Version=9.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35" xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35" xmlns:mxs="clr-namespace:Microsoft.Xrm.Sdk;assembly=Microsoft.Xrm.Sdk, Version=9.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35" xmlns:mxswa="clr-namespace:Microsoft.Xrm.Sdk.Workflow.Activities;assembly=Microsoft.Xrm.Sdk.Workflow, Version=9.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35" xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089" xmlns:sco="clr-namespace:System.Collections.ObjectModel;assembly=mscorlib, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <x:Members><x:Property Name="InputEntities" Type="InArgument(scg:IDictionary(x:String, mxs:Entity))" /><x:Property Name="CreatedEntities" Type="InArgument(scg:IDictionary(x:String, mxs:Entity))" /></x:Members>
  <this:{class_name}.InputEntities xmlns:this="clr-namespace:"><InArgument x:TypeArguments="scg:IDictionary(x:String, mxs:Entity)" /></this:{class_name}.InputEntities>
  <this:{class_name}.CreatedEntities xmlns:this="clr-namespace:"><InArgument x:TypeArguments="scg:IDictionary(x:String, mxs:Entity)" /></this:{class_name}.CreatedEntities>
  <mva:VisualBasic.Settings>Assembly references and imported namespaces for internal implementation</mva:VisualBasic.Settings>
  <mxswa:Workflow>
    <mxswa:ActivityReference AssemblyQualifiedName="Microsoft.Crm.Workflow.BusinessProcessFlowActivities.StageRelationshipCollectionComposite, Microsoft.Crm.Workflow, Version=9.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35" DisplayName="RelationshipCollectionStep0"><mxswa:ActivityReference.Properties><sco:Collection x:TypeArguments="Variable" x:Key="Variables" /><sco:Collection x:TypeArguments="Activity" x:Key="Activities" /></mxswa:ActivityReference.Properties></mxswa:ActivityReference>
    {''.join(entity_xml)}
  </mxswa:Workflow>
</Activity>"""


def add_solution_component(
    url: str,
    component_id: str,
    component_type: int,
    solution: str,
) -> None:
    cred = credential()
    token = cred.get_token(f"{url}/.default").token
    response = requests.post(
        f"{url}/api/data/v9.2/AddSolutionComponent",
        headers={
            "Authorization": "Bearer" + " " + token,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "OData-Version": "4.0",
            "OData-MaxVersion": "4.0",
        },
        json={
            "ComponentId": component_id,
            "ComponentType": component_type,
            "SolutionUniqueName": solution,
            "AddRequiredComponents": True,
            "DoNotIncludeSubcomponents": False,
        },
        timeout=180,
    )
    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"AddSolutionComponent failed ({response.status_code}): "
            f"{response.text[:800]}"
        )


def post_action(url: str, action: str, body: dict[str, Any]) -> None:
    cred = credential()
    token = cred.get_token(f"{url}/.default").token
    response = requests.post(
        f"{url}/api/data/v9.2/{action}",
        headers={
            "Authorization": "Bearer" + " " + token,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "OData-Version": "4.0",
            "OData-MaxVersion": "4.0",
        },
        json=body,
        timeout=300,
    )
    if response.status_code not in (200, 204):
        raise RuntimeError(
            f"{action} failed ({response.status_code}): {response.text[:800]}"
        )


def role_assignment(client: DataverseClient, spec: dict[str, Any]) -> str:
    role_names = list(spec.get("security_roles", []))
    if not role_names:
        return "<DisplayConditions><Everyone /></DisplayConditions>"
    roles = resolve_roles(client, role_names)
    entries = "".join(
        f'<Role Id="{{{roles[name]}}}" />' for name in role_names
    )
    return f"<DisplayConditions>{entries}</DisplayConditions>"


def role_ids(xml: str | None) -> set[str]:
    if not xml:
        return set()
    return {
        value.lower()
        for value in re.findall(r'<Role Id="[{\s]*([0-9a-fA-F-]{36})', xml)
    }


def workflow_rows(
    client: DataverseClient, spec: dict[str, Any], include_xaml: bool = False
):
    select = [
        "workflowid",
        "name",
        "uniquename",
        "primaryentity",
        "category",
        "statecode",
        "statuscode",
        "processorder",
        "processroleassignment",
    ]
    if include_xaml:
        select.extend(["xaml", "clientdata"])
    escaped = spec["unique_name"].replace("'", "''")
    return client.records.list(
        "workflow",
        filter=f"uniquename eq '{escaped}' and category eq 4",
        select=select,
        top=2,
    )


def expected_structure(spec: dict[str, Any]) -> list[tuple[str, list[str]]]:
    return [
        (stage["name"], [step["field"] for step in stage["steps"]])
        for stage in spec["stages"]
    ]


def actual_structure(clientdata: str) -> list[tuple[str, list[str]]]:
    root = json.loads(clientdata)
    result = []
    for entity in root["steps"]["list"]:
        if not str(entity.get("__class", "")).startswith("EntityStep:"):
            continue
        for stage in entity["steps"]["list"]:
            fields = []
            for step in stage["steps"]["list"]:
                fields.append(step["steps"]["list"][0]["dataFieldName"])
            result.append((stage["description"], fields))
    return result


def verify(client: DataverseClient, spec: dict[str, Any]) -> int:
    rows = workflow_rows(client, spec, include_xaml=True)
    if len(rows) != 1:
        print(f"[FAIL] expected one BPF, found {len(rows)}")
        return 1
    row = rows[0]
    expected_roles = {
        value.lower()
        for value in resolve_roles(
            client, list(spec.get("security_roles", []))
        ).values()
    }
    app = resolve_app(client, spec.get("app_unique_name"))
    app_included = True
    if app:
        components = client.records.list(
            "appmodulecomponent",
            filter=f"objectid eq {row['workflowid']}",
            select=["objectid", "_appmoduleidunique_value"],
        )
        app_included = any(
            str(component.get("_appmoduleidunique_value", "")).lower()
            == str(app["appmoduleidunique"]).lower()
            for component in components
        )
    checks = {
        "display name": row.get("name") == spec["name"],
        "primary table": row.get("primaryentity") == spec["table"],
        "category": row.get("category") == 4,
        "active": row.get("statecode") == 1,
        "process order": row.get("processorder")
        == int(spec.get("process_order", 100)),
        "security roles": (
            role_ids(row.get("processroleassignment")) == expected_roles
            if expected_roles
            else "<Everyone" in (row.get("processroleassignment") or "")
        ),
        "model-driven app": app_included,
        "stages and fields": actual_structure(row["clientdata"])
        == expected_structure(spec),
    }
    failed = False
    for name, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        failed = failed or not passed
    return 1 if failed else 0


def apply(client: DataverseClient, url: str, spec: dict[str, Any], columns) -> int:
    rows = workflow_rows(client, spec)
    if rows:
        raise RuntimeError(
            f"BPF {spec['unique_name']!r} already exists; use --verify"
        )
    workflow_id, clientdata, xaml = build_model(spec, columns)
    payload = {
        "workflowid": workflow_id,
        "name": spec["name"],
        "uniquename": spec["unique_name"],
        "primaryentity": spec["table"],
        "category": 4,
        "type": 1,
        "businessprocesstype": 0,
        "iscrmuiworkflow": True,
        "mode": 0,
        "scope": 4,
        "runas": 1,
        "processtriggerscope": 1,
        "istransacted": True,
        "ondemand": False,
        "languagecode": int(spec.get("language_code", 1033)),
        "processorder": int(spec.get("process_order", 100)),
        "processroleassignment": role_assignment(client, spec),
        "clientdata": clientdata,
        "xaml": xaml,
    }
    created = client.records.create("workflow", payload)
    if created.lower() != workflow_id.lower():
        workflow_id = created
    add_solution_component(url, workflow_id, 29, spec["solution"])
    client.records.update(
        "workflow", workflow_id, {"statecode": 1, "statuscode": 2}
    )
    metadata = client.tables.get(spec["unique_name"])
    if not metadata:
        raise RuntimeError(
            "BPF activated but generated table metadata was not found"
        )
    add_solution_component(
        url, str(metadata["MetadataId"]), 1, spec["solution"]
    )
    app = resolve_app(client, spec.get("app_unique_name"))
    if app:
        post_action(
            url,
            "AddAppComponents",
            {
                "AppId": app["appmoduleid"],
                "Components": [
                    {
                        "@odata.type": "Microsoft.Dynamics.CRM.workflow",
                        "workflowid": workflow_id,
                    }
                ],
            },
        )
        post_action(url, "PublishAllXml", {})
    print(f"[ok] created and activated {spec['name']} ({workflow_id})")
    return verify(client, spec)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--url", default=os.environ.get("DATAVERSE_URL"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not args.url:
        raise SystemExit("Set DATAVERSE_URL or pass --url")
    url = args.url.rstrip("/")
    spec = read_spec(args.spec)
    with client_for(url) as client:
        columns = validate_spec(client, spec)
        if args.dry_run:
            workflow_id, clientdata, xaml = build_model(spec, columns)
            print(f"[PASS] metadata and solution validation")
            print(f"[dry-run] workflow id: {workflow_id}")
            print(f"[dry-run] clientdata bytes: {len(clientdata.encode())}")
            print(f"[dry-run] xaml bytes: {len(xaml.encode())}")
            return 0
        if args.verify:
            return verify(client, spec)
        return apply(client, url, spec, columns)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
