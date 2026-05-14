import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient

load_env()
client = DataverseClient(os.environ["DATAVERSE_URL"], get_credential())

# Find or create publisher
pages = client.records.get(
    "publisher",
    filter="uniquename eq 'LaunchControl'",
    select=["publisherid", "uniquename", "customizationprefix"],
    top=1,
)
existing = [p for page in pages for p in page]

if existing:
    publisher_id = existing[0]["publisherid"]
    print(f"Publisher already exists: {publisher_id} (prefix: {existing[0]['customizationprefix']}_)")
else:
    publisher_id = client.records.create("publisher", {
        "uniquename": "LaunchControl",
        "friendlyname": "Launch Control",
        "customizationprefix": "lc",
        "description": "Launch Control publisher",
    })
    print(f"Created publisher: {publisher_id}")

# Find or create solution
pages = client.records.get(
    "solution",
    filter="uniquename eq 'LaunchControl'",
    select=["solutionid", "uniquename"],
    top=1,
)
existing_sol = [s for page in pages for s in page]

if existing_sol:
    print(f"Solution already exists: {existing_sol[0]['solutionid']}")
else:
    solution_id = client.records.create("solution", {
        "uniquename": "LaunchControl",
        "friendlyname": "LaunchControl",
        "version": "1.0.0.0",
        "publisherid@odata.bind": f"/publishers({publisher_id})",
    })
    print(f"Created solution: {solution_id}")
