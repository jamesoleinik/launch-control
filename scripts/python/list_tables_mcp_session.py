"""List custom tables on the env via the DataverseClient SDK (same Web API the MCP server fronts)."""
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient

load_env()

with DataverseClient(base_url=os.environ["DATAVERSE_URL"], credential=get_credential()) as client:
    rows = []
    for page in client.records.get(
        "EntityDefinitions",
        select=["LogicalName", "SchemaName", "DisplayName", "TableType", "IsManaged"],
        filter="IsCustomEntity eq true",
    ):
        for r in page:
            disp = (r.get("DisplayName") or {}).get("UserLocalizedLabel") or {}
            rows.append({
                "logical":  r.get("LogicalName"),
                "schema":   r.get("SchemaName"),
                "display":  disp.get("Label", ""),
                "type":     r.get("TableType") or "",
                "managed":  bool(r.get("IsManaged")),
            })

# Split unmanaged (your own customizations) from managed (everything brought in by solutions)
mine = sorted([r for r in rows if not r["managed"]], key=lambda x: x["logical"])
mgd  = sorted([r for r in rows if r["managed"]],  key=lambda x: x["logical"])

print(f"Custom tables total: {len(rows)}  (unmanaged: {len(mine)}, managed: {len(mgd)})\n")

print("=== UNMANAGED (yours) ===")
print(f"{'Logical':<40} {'Type':<10} Display")
print("-" * 90)
for r in mine:
    print(f"{r['logical']:<40} {r['type']:<10} {r['display']}")

# Just show the lc_* ones from managed (the AppSource / first-party noise is huge)
lc_managed = [r for r in mgd if r["logical"].startswith("lc_")]
if lc_managed:
    print(f"\n=== MANAGED lc_* ({len(lc_managed)}) ===")
    for r in lc_managed:
        print(f"{r['logical']:<40} {r['type']:<10} {r['display']}")
