"""Prove whether the Agent User can read a specific Launch."""
from __future__ import annotations

import argparse

import requests

from agent.config import Config
from agent.identity import AgentTokenProvider
from seed_demo import Dataverse, exactly_one


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-name", default="Q3 Widget Launch")
    parser.add_argument(
        "--expect",
        choices=("denied", "granted"),
        required=True,
    )
    args = parser.parse_args()

    safe_name = args.launch_name.replace("'", "''")
    control = Dataverse()
    launch_record = exactly_one(
        control.get(
            "/lc_launchs?$select=lc_launchid"
            f"&$filter=lc_name eq '{safe_name}'&$top=2"
        )["value"],
        f"launch named {args.launch_name!r}",
    )
    launch_id = launch_record["lc_launchid"]

    config = Config.load()
    token = AgentTokenProvider(config)()
    api = config.dataverse_url + "/api/data/v9.2"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    launch = requests.get(
        api + f"/lc_launchs({launch_id})?$select=lc_name",
        headers=headers,
        timeout=90,
    )
    granted = launch.status_code == 200
    if args.expect == "denied" and not granted:
        print(
            "[PASS] Agent User cannot read the Launch without an active "
            "assignment"
        )
        return 0
    if args.expect == "granted" and granted:
        print(
            "[PASS] Agent User can read the assigned Launch: "
            + launch.json().get("lc_name", "")
        )
        return 0
    state = "granted" if granted else f"denied ({launch.status_code})"
    raise RuntimeError(
        f"Expected Launch access to be {args.expect}, but it was {state}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
