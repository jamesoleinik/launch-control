"""Delete all Launch Control data records and optionally the solution."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient


def delete_all_records(client, table, label):
    """Delete all records from a table."""
    ids = []
    pages = client.records.get(table, select=["createdon"], top=5000)
    for page in pages:
        for r in page:
            pk = table.replace("lc_", "") + "id"
            rid = r.get("lc_%sid" % table.split("_")[1]) or r.get(list(r.keys())[0])
            ids.append(rid)
    if ids:
        print("  Deleting %d %s records..." % (len(ids), label))
        client.records.delete(table, ids)
        print("  Done.")
    else:
        print("  %s: no records to delete." % label)


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    with DataverseClient(env_url, get_credential()) as client:
        # Delete in dependency order (children first)
        tables = [
            ("lc_statusupdate", "Status Updates"),
            ("lc_task", "Tasks"),
            ("lc_milestone", "Milestones"),
            ("lc_teammember", "Team Members"),
            ("lc_launch", "Launches"),
        ]
        print("=== Clearing all Launch Control data ===")
        for table, label in tables:
            try:
                delete_all_records(client, table, label)
            except Exception as e:
                print("  Error on %s: %s" % (label, e))

        print("\nAll data cleared.")


if __name__ == "__main__":
    main()
