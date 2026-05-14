import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient

load_env()
client = DataverseClient(os.environ["DATAVERSE_URL"], get_credential())

for ln in ["lc_launch","lc_milestone","lc_task","lc_teammember","lc_statusupdate",
           "lc_stg_tracker_a","lc_stg_tracker_b","lc_stg_tracker_c","lc_stg_tracker_d","lc_stg_tracker_e"]:
    info = client.tables.get(ln)
    print(f"{ln}: {'EXISTS' if info else 'missing'}")
