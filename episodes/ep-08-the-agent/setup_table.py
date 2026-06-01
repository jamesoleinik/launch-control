"""Episode 3 Part 2: Create the lc_KnowledgeArticle table.

A knowledge-base table designed for agentic search via Dataverse Knowledge
in Copilot Studio (multiline-text + file-column grounding).

Columns:
- lc_Title (string, primary)
- lc_Summary (memo / multiline) — short body for fast retrieval
- lc_Document (file) — actual source PDF/DOCX/MD bytes
- lc_Category (choice: Policy/Playbook/Spec/Postmortem)
- lc_LaunchId (lookup -> lc_Launch) — added after table creation

NOTE on "Search support for multiline text and file data types" preview:
That flag is enabled per-table inside Copilot Studio when adding the table
as a Dataverse Knowledge source. The capability is enabled tenant-side via
the Power Platform admin center (Features → MCP / Knowledge previews).
This script provisions the data shape; the search-enable step is part of
the Ep 8 UI demo.
"""

import os
import sys
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402


class KnowledgeCategory(Enum):
    Policy = 10600100
    Playbook = 10600101
    Spec = 10600102
    Postmortem = 10600103


def _is_duplicate(e):
    msg = str(e).lower()
    return any(x in msg for x in [
        "duplicate", "already exists", "matching key",
        "already being used", "cannot be used again",
    ])


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()
    prefix = "lc"
    solution_name = "LaunchControl"

    with DataverseClient(env_url, credential) as client:
        print(f"Creating {prefix}_KnowledgeArticle table in solution '{solution_name}'...")
        try:
            client.tables.create(
                f"{prefix}_KnowledgeArticle",
                {
                    f"{prefix}_Summary": "memo",
                    f"{prefix}_Document": "file",
                    f"{prefix}_Category": KnowledgeCategory,
                },
                solution=solution_name,
                primary_column=f"{prefix}_Title",
            )
            print("  Created: lc_KnowledgeArticle")
        except Exception as e:
            if _is_duplicate(e):
                print("  lc_KnowledgeArticle already exists, skipping.")
            else:
                raise

        print("\nCreating lookup: lc_KnowledgeArticle -> lc_Launch (LaunchId)...")
        try:
            client.tables.create_lookup_field(
                f"{prefix}_knowledgearticle",
                f"{prefix}_LaunchId",
                f"{prefix}_launch",
                display_name="Launch",
                solution=solution_name,
            )
            print("  Created: lc_KnowledgeArticle -> lc_Launch")
        except Exception as e:
            if _is_duplicate(e):
                print("  Lookup already exists, skipping.")
            else:
                print(f"  Error: {e}")

        print("\n=== Episode 3 Part 2 knowledge table complete! ===")
        print("Table: lc_KnowledgeArticle")
        print("Columns: lc_Title (primary), lc_Summary (memo), lc_Document (file),")
        print("         lc_Category (choice), lc_LaunchId (lookup -> lc_Launch)")
        print("\nNext: run episodes/ep-08-the-agent/upload_knowledge.py to upload sample KB docs.")


if __name__ == "__main__":
    main()
