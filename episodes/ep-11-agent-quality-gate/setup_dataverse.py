"""Create the Episode 11 Quality Gate schema and least-privilege role.

Dry-run first:
    python setup_dataverse.py --dry-run
    python setup_dataverse.py --apply
    python setup_dataverse.py --verify
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import auth  # noqa: E402

EPISODE = "ep-11-agent-quality-gate"
SOLUTION = "LaunchControl"
RESULT_TABLE = "lc_qualitygateresult"
RESULT_SET = "lc_qualitygateresults"
ROLE_NAME = "lc Quality Gate Agent"
USER = "Basic"
BU = "Local"
ROLE_PRIVILEGES = [
    ("prvReadlc_launch", USER),
    ("prvReadlc_milestone", USER),
    ("prvReadlc_task", USER),
    ("prvCreatelc_task", USER),
    ("prvAppendlc_task", USER),
    ("prvReadlc_statusupdate", USER),
    ("prvCreatelc_statusupdate", USER),
    ("prvAppendlc_statusupdate", USER),
    ("prvReadActivity", USER),
    ("prvWriteActivity", USER),
    ("prvCreateNote", USER),
    ("prvReadNote", USER),
    ("prvAppendNote", USER),
    ("prvCreatelc_QualityGateResult", USER),
    ("prvReadlc_QualityGateResult", USER),
    ("prvWritelc_QualityGateResult", USER),
    ("prvAppendlc_QualityGateResult", USER),
    ("prvAppendTolc_launch", USER),
]
EXPECTED_COLUMNS = {
    "lc_name": "String",
    "lc_outcome": "Picklist",
    "lc_score": "Integer",
    "lc_checkedon": "DateTime",
    "lc_feedback": "Memo",
    "lc_evidence": "String",
    "lc_assignmentkey": "String",
}
EXPECTED_LAUNCH_COLUMNS = {
    "lc_approvaldecision": "Picklist",
    "lc_qualitygatestatus": "Picklist",
    "lc_qualitygatescore": "Integer",
    "lc_qualitygatefeedback": "Memo",
    "lc_qualitygatecheckedon": "DateTime",
    "lc_qualitygateevidence": "String",
}


def label(text: str) -> dict[str, Any]:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [{
            "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
            "Label": text,
            "LanguageCode": 1033,
        }],
    }


def required(value: str = "None") -> dict[str, Any]:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.AttributeRequiredLevelManagedProperty",
        "Value": value,
    }


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

    def get(self, path: str) -> dict[str, Any]:
        response = requests.get(self.api + path, headers=self.headers, timeout=90)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, body: dict[str, Any], *, solution: bool = False) -> requests.Response:
        headers = dict(self.headers)
        if solution:
            headers["MSCRM.SolutionUniqueName"] = SOLUTION
        response = requests.post(
            self.api + path, headers=headers, json=body, timeout=180
        )
        if response.status_code not in (200, 201, 204):
            raise RuntimeError(
                f"POST {path} failed ({response.status_code}): {response.text[:800]}"
            )
        return response

    def put(
        self, path: str, body: dict[str, Any], *, solution: bool = False
    ) -> requests.Response:
        headers = dict(self.headers)
        headers["MSCRM.MergeLabels"] = "true"
        if solution:
            headers["MSCRM.SolutionUniqueName"] = SOLUTION
        response = requests.put(
            self.api + path, headers=headers, json=body, timeout=180
        )
        if response.status_code not in (200, 204):
            raise RuntimeError(
                f"PUT {path} failed ({response.status_code}): "
                f"{response.text[:800]}"
            )
        return response

def table_exists(dv: Dataverse) -> bool:
    path = (
        "/EntityDefinitions?"
        "$select=LogicalName&$filter=LogicalName eq 'lc_qualitygateresult'"
    )
    return bool(dv.get(path).get("value"))


def create_result_table(dv: Dataverse, dry_run: bool) -> None:
    if table_exists(dv):
        print(f"[skip] {RESULT_TABLE} already exists")
        return
    if dry_run:
        print(f"[dry-run] would create table {RESULT_TABLE}")
        return

    options = [
        (106000000, "Passed"),
        (106000001, "Failed"),
        (106000002, "Needs review"),
        (106000003, "Error"),
    ]
    payload = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": "lc_QualityGateResult",
        "DisplayName": label("Quality Gate Result"),
        "DisplayCollectionName": label("Quality Gate Results"),
        "Description": label(
            "An attributable result produced by the governed Quality Gate agent."
        ),
        "OwnershipType": "UserOwned",
        "IsActivity": False,
        "HasActivities": False,
        "HasNotes": False,
        "Attributes": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "AttributeType": "String",
                "SchemaName": "lc_Name",
                "DisplayName": label("Name"),
                "IsPrimaryName": True,
                "MaxLength": 200,
                "RequiredLevel": required("ApplicationRequired"),
            },
            {
                "@odata.type": "Microsoft.Dynamics.CRM.PicklistAttributeMetadata",
                "AttributeType": "Picklist",
                "SchemaName": "lc_Outcome",
                "DisplayName": label("Outcome"),
                "RequiredLevel": required("ApplicationRequired"),
                "OptionSet": {
                    "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
                    "IsGlobal": False,
                    "OptionSetType": "Picklist",
                    "Options": [
                        {
                            "Value": value,
                            "Label": label(text),
                        }
                        for value, text in options
                    ],
                },
            },
            {
                "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
                "AttributeType": "Integer",
                "SchemaName": "lc_Score",
                "DisplayName": label("Score"),
                "MinValue": 0,
                "MaxValue": 100,
                "Format": "None",
            },
            {
                "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
                "AttributeType": "DateTime",
                "SchemaName": "lc_CheckedOn",
                "DisplayName": label("Checked On"),
                "Format": "DateAndTime",
                "DateTimeBehavior": {"Value": "UserLocal"},
            },
            {
                "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
                "AttributeType": "Memo",
                "SchemaName": "lc_Feedback",
                "DisplayName": label("Feedback"),
                "MaxLength": 10000,
            },
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "AttributeType": "String",
                "SchemaName": "lc_Evidence",
                "DisplayName": label("Evidence"),
                "MaxLength": 1000,
                "FormatName": {"Value": "Url"},
            },
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "AttributeType": "String",
                "SchemaName": "lc_AssignmentKey",
                "DisplayName": label("Assignment Key"),
                "MaxLength": 200,
                "RequiredLevel": required("ApplicationRequired"),
            },
        ],
    }
    dv.post("/EntityDefinitions", payload, solution=True)
    print(f"[ok] created table {RESULT_TABLE}")


def lookup_exists(dv: Dataverse, schema_name: str) -> bool:
    path = (
        f"/EntityDefinitions(LogicalName='{RESULT_TABLE}')/Attributes/"
        "Microsoft.Dynamics.CRM.LookupAttributeMetadata"
        f"?$select=SchemaName&$filter=SchemaName eq '{schema_name}'"
    )
    return bool(dv.get(path).get("value"))


def create_launch_lookup(dv: Dataverse, dry_run: bool) -> None:
    schema_name = "lc_Launch"
    if not table_exists(dv):
        print("[wait] result table does not exist yet")
        return
    if lookup_exists(dv, schema_name):
        print(f"[skip] lookup {schema_name} already exists")
        return
    if dry_run:
        print(f"[dry-run] would create {RESULT_TABLE}.lc_launch lookup")
        return
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": "lc_launch_QualityGateResults",
        "ReferencedEntity": "lc_launch",
        "ReferencingEntity": RESULT_TABLE,
        "CascadeConfiguration": {
            "Assign": "NoCascade",
            "Delete": "RemoveLink",
            "Merge": "NoCascade",
            "Reparent": "NoCascade",
            "Share": "NoCascade",
            "Unshare": "NoCascade",
        },
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "SchemaName": schema_name,
            "DisplayName": label("Launch"),
            "RequiredLevel": required("ApplicationRequired"),
        },
    }
    dv.post("/RelationshipDefinitions", body, solution=True)
    print("[ok] created launch lookup")


def launch_column_exists(dv: Dataverse, logical_name: str) -> bool:
    rows = dv.get(
        "/EntityDefinitions(LogicalName='lc_launch')/Attributes"
        f"?$select=LogicalName&$filter=LogicalName eq '{logical_name}'"
    )["value"]
    return bool(rows)


def ensure_launch_activities(dv: Dataverse, dry_run: bool) -> None:
    path = "/EntityDefinitions(LogicalName='lc_launch')"
    metadata = dv.get(path)
    if metadata.get("HasActivities") is True:
        print("[skip] lc_launch activities already enabled")
        return
    if dry_run:
        print("[dry-run] would enable activities on lc_launch")
        return
    metadata["HasActivities"] = True
    dv.put(path, metadata, solution=True)
    dv.post(
        "/PublishXml",
        {
            "ParameterXml": (
                "<importexportxml><entities><entity>lc_launch</entity>"
                "</entities></importexportxml>"
            )
        },
    )
    print("[ok] enabled and published activities on lc_launch")


def ensure_launch_columns(dv: Dataverse, dry_run: bool) -> None:
    approval_options = [
        (106000000, "Pending"),
        (106000001, "Approved"),
        (106000002, "Rejected"),
    ]
    status_options = [
        (106000000, "Pending"),
        (106000001, "Passed"),
        (106000002, "Failed"),
        (106000003, "Needs review"),
        (106000004, "Error"),
    ]
    attributes: list[tuple[str, dict[str, Any]]] = [
        (
            "lc_approvaldecision",
            {
                "@odata.type": "Microsoft.Dynamics.CRM.PicklistAttributeMetadata",
                "AttributeType": "Picklist",
                "SchemaName": "lc_ApprovalDecision",
                "DisplayName": label("Approval Decision"),
                "RequiredLevel": required(),
                "OptionSet": {
                    "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
                    "IsGlobal": False,
                    "OptionSetType": "Picklist",
                    "Options": [
                        {"Value": value, "Label": label(text)}
                        for value, text in approval_options
                    ],
                },
            },
        ),
        (
            "lc_qualitygatestatus",
            {
                "@odata.type": "Microsoft.Dynamics.CRM.PicklistAttributeMetadata",
                "AttributeType": "Picklist",
                "SchemaName": "lc_QualityGateStatus",
                "DisplayName": label("Quality Gate Status"),
                "RequiredLevel": required(),
                "OptionSet": {
                    "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
                    "IsGlobal": False,
                    "OptionSetType": "Picklist",
                    "Options": [
                        {"Value": value, "Label": label(text)}
                        for value, text in status_options
                    ],
                },
            },
        ),
        (
            "lc_qualitygatescore",
            {
                "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
                "AttributeType": "Integer",
                "SchemaName": "lc_QualityGateScore",
                "DisplayName": label("Quality Gate Score"),
                "MinValue": 0,
                "MaxValue": 100,
                "Format": "None",
            },
        ),
        (
            "lc_qualitygatefeedback",
            {
                "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
                "AttributeType": "Memo",
                "SchemaName": "lc_QualityGateFeedback",
                "DisplayName": label("Quality Gate Feedback"),
                "MaxLength": 10000,
            },
        ),
        (
            "lc_qualitygatecheckedon",
            {
                "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
                "AttributeType": "DateTime",
                "SchemaName": "lc_QualityGateCheckedOn",
                "DisplayName": label("Quality Gate Checked On"),
                "Format": "DateAndTime",
                "DateTimeBehavior": {"Value": "UserLocal"},
            },
        ),
        (
            "lc_qualitygateevidence",
            {
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "AttributeType": "String",
                "SchemaName": "lc_QualityGateEvidence",
                "DisplayName": label("Quality Gate Evidence"),
                "MaxLength": 1000,
                "FormatName": {"Value": "Url"},
            },
        ),
    ]
    for logical_name, attribute in attributes:
        if launch_column_exists(dv, logical_name):
            print(f"[skip] lc_launch.{logical_name} already exists")
        elif dry_run:
            print(f"[dry-run] would create lc_launch.{logical_name}")
        else:
            dv.post(
                "/EntityDefinitions(LogicalName='lc_launch')/Attributes",
                attribute,
                solution=True,
            )
            print(f"[ok] created lc_launch.{logical_name}")


def root_business_unit(dv: Dataverse) -> str:
    rows = dv.get(
        "/businessunits?$select=businessunitid,_parentbusinessunitid_value"
    )["value"]
    return next(
        row["businessunitid"]
        for row in rows
        if not row.get("_parentbusinessunitid_value")
    )


def ensure_role(dv: Dataverse, dry_run: bool) -> str | None:
    root = root_business_unit(dv)
    rows = dv.get(
        f"/roles?$select=roleid,name&$filter=name eq '{ROLE_NAME}' "
        f"and _businessunitid_value eq {root}"
    )["value"]
    if rows:
        role_id = rows[0]["roleid"]
        print(f"[skip] role {ROLE_NAME} already exists")
    elif dry_run:
        print(f"[dry-run] would create role {ROLE_NAME}")
        return None
    else:
        response = dv.post(
            "/roles",
            {
                "name": ROLE_NAME,
                "businessunitid@odata.bind": f"/businessunits({root})",
            },
            solution=True,
        )
        entity_id = response.headers.get("OData-EntityId", "")
        role_id = entity_id.rsplit("(", 1)[-1].rstrip(")")
        print(f"[ok] created role {ROLE_NAME}")

    names = " or ".join(f"name eq '{name}'" for name, _ in ROLE_PRIVILEGES)
    privileges = dv.get(
        f"/privileges?$select=privilegeid,name&$filter={names}"
    )["value"]
    by_name = {row["name"]: row["privilegeid"] for row in privileges}
    missing = [name for name, _ in ROLE_PRIVILEGES if name not in by_name]
    if missing:
        if dry_run and not table_exists(dv):
            print("[dry-run] result-table privileges become available after apply")
            return role_id
        raise RuntimeError(f"Missing Dataverse privileges: {', '.join(missing)}")

    if dry_run:
        print(
            f"[dry-run] would sync exactly {len(ROLE_PRIVILEGES)} "
            "role privileges"
        )
        return role_id
    dv.post(
        f"/roles({role_id})/Microsoft.Dynamics.CRM.AddPrivilegesRole",
        {
            "Privileges": [
                {"PrivilegeId": by_name[name], "Depth": depth}
                for name, depth in ROLE_PRIVILEGES
            ]
        },
    )
    assigned = dv.get(
        f"/roles({role_id})/roleprivileges_association"
        "?$select=privilegeid,name"
    )["value"]
    desired_ids = set(by_name.values())
    extras = [
        row for row in assigned if row["privilegeid"] not in desired_ids
    ]
    for privilege in extras:
        dv.post(
            f"/roles({role_id})/"
            "Microsoft.Dynamics.CRM.RemovePrivilegeRole",
            {"Privilege": {"privilegeid": privilege["privilegeid"]}},
        )
        print(f"[ok] removed unrelated privilege {privilege['name']}")
    print(f"[ok] synced exactly {len(ROLE_PRIVILEGES)} role privileges")
    return role_id


def assign_role(dv: Dataverse, role_id: str | None, dry_run: bool) -> None:
    user_id = os.environ.get("QUALITY_GATE_AGENT_SYSTEMUSER_ID", "").strip()
    if not user_id:
        print("[info] QUALITY_GATE_AGENT_SYSTEMUSER_ID not set; role not assigned")
        return
    if not role_id:
        print("[dry-run] would assign role after it is created")
        return
    root = root_business_unit(dv)
    basic = dv.get(
        "/roles?$select=roleid,name"
        f"&$filter=name eq 'Basic User' and _businessunitid_value eq {root}"
    )["value"]
    if not basic:
        raise RuntimeError("Basic User role not found in the root business unit")
    roles = [(ROLE_NAME, role_id), ("Basic User", basic[0]["roleid"])]
    for name, assigned_role_id in roles:
        if dry_run:
            print(f"[dry-run] would assign {name} to configured agent user")
            continue
        body = {"@odata.id": f"{dv.api}/roles({assigned_role_id})"}
        response = requests.post(
            dv.api
            + f"/systemusers({user_id})/systemuserroles_association/$ref",
            headers=dv.headers,
            json=body,
            timeout=90,
        )
        if (
            response.status_code not in (200, 204)
            and "duplicate" not in response.text.lower()
        ):
            raise RuntimeError(
                f"{name} assignment failed ({response.status_code}): "
                f"{response.text[:500]}"
            )
        print(f"[ok] ensured {name} assignment")


def verify(dv: Dataverse) -> int:
    columns: dict[str, str] = {}
    if table_exists(dv):
        rows = dv.get(
            f"/EntityDefinitions(LogicalName='{RESULT_TABLE}')/Attributes"
            "?$select=LogicalName,AttributeType"
        )["value"]
        columns = {
            row["LogicalName"]: row.get("AttributeType", "")
            for row in rows
        }
    launch_columns = {
        row["LogicalName"]: row.get("AttributeType", "")
        for row in dv.get(
            "/EntityDefinitions(LogicalName='lc_launch')/Attributes"
            "?$select=LogicalName,AttributeType"
        )["value"]
    }
    launch_metadata = dv.get(
        "/EntityDefinitions(LogicalName='lc_launch')"
        "?$select=HasActivities"
    )
    role_rows = dv.get(
        f"/roles?$select=roleid&$filter=name eq '{ROLE_NAME}'"
    )["value"]
    role_privileges = set()
    if role_rows:
        role_privileges = {
            row["name"]
            for row in dv.get(
                f"/roles({role_rows[0]['roleid']})/"
                "roleprivileges_association?$select=name"
            )["value"]
        }
    checks = {
        "result table": table_exists(dv),
        **{
            f"column {name} ({kind})": columns.get(name) == kind
            for name, kind in EXPECTED_COLUMNS.items()
        },
        "launch lookup": table_exists(dv) and lookup_exists(dv, "lc_Launch"),
        **{
            f"launch column {name} ({kind})": launch_columns.get(name) == kind
            for name, kind in EXPECTED_LAUNCH_COLUMNS.items()
        },
        "launch activities enabled": launch_metadata.get("HasActivities") is True,
        "security role": bool(role_rows),
        "security role has exact privileges": role_privileges
        == {name for name, _ in ROLE_PRIVILEGES},
    }
    failed = False
    for name, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        failed = failed or not passed
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument(
        "--role-only",
        action="store_true",
        help="Skip schema checks and synchronize only the Agent User role.",
    )
    args = parser.parse_args()

    dv = Dataverse()
    if args.verify:
        return verify(dv)
    if args.role_only:
        role_id = ensure_role(dv, args.dry_run)
        assign_role(dv, role_id, args.dry_run)
        return 0

    create_result_table(dv, args.dry_run)
    if args.apply and not lookup_exists(dv, "lc_Launch"):
        for _ in range(12):
            if table_exists(dv):
                break
            time.sleep(5)
    create_launch_lookup(dv, args.dry_run)
    ensure_launch_activities(dv, args.dry_run)
    ensure_launch_columns(dv, args.dry_run)
    role_id = ensure_role(dv, args.dry_run)
    assign_role(dv, role_id, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
