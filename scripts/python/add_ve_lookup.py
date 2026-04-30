"""Add lc_GitHubIssueId lookup column on lc_task targeting the lc_githubissue
virtual entity.

This is the Episode 4 stitch: a real Dataverse relationship between a regular
table (lc_task) and a virtual table (lc_githubissue). Dataverse stores the VE's
deterministic GUID on the task; on read it calls the VE provider plugin's
RetrievePlugin to materialise the issue from GitHub.

Run once per environment. Idempotent — duplicates are skipped.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()
    solution_name = "LaunchControl"

    with DataverseClient(env_url, credential) as client:
        print(f"Adding lc_GitHubIssueId lookup on lc_task -> lc_githubissue ...")
        try:
            client.tables.create_lookup_field(
                "lc_task",
                "lc_GitHubIssueId",
                "lc_githubissue",
                display_name="GitHub Issue",
                solution=solution_name,
            )
            print("  Created.")
        except Exception as e:
            msg = str(e).lower()
            if any(x in msg for x in ("duplicate", "already exists", "matching key", "already being used")):
                print("  Already exists, skipping.")
            else:
                print(f"  ERROR: {e}")
                raise

        print("\nDone.")


if __name__ == "__main__":
    main()
