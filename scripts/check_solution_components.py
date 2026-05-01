"""Check which Ep5 plugin/custom-api components are in the LaunchControl solution."""
import os, json, urllib.request, urllib.parse, sys
sys.path.insert(0, '.')
from scripts.auth import get_token, load_env

load_env()
env = os.environ['DATAVERSE_URL'].rstrip('/')
tok = get_token()


def get(path):
    req = urllib.request.Request(env + '/api/data/v9.2/' + urllib.parse.quote(path, safe="?$=&'/,"))
    req.add_header('Authorization', 'Bearer ' + tok)
    req.add_header('Accept', 'application/json')
    return json.loads(urllib.request.urlopen(req).read())


sols = get("solutions?$filter=uniquename eq 'LaunchControl'&$select=solutionid,uniquename")['value']
if not sols:
    print('LaunchControl solution NOT FOUND')
    sys.exit(0)
sid = sols[0]['solutionid']
print('Solution:', sid)

comps = get(f"solutioncomponents?$filter=_solutionid_value eq {sid}&$select=objectid,componenttype")['value']
print('Total components:', len(comps))

targets = {
    'ed27e514-d742-f111-bec6-000d3a336093': 'PluginAssembly: CalculateLaunchReadiness',
    'e65ae21a-d742-f111-bec6-000d3a336093': 'PluginType:     CalculateLaunchReadinessPlugin',
    'ec5ae21a-d742-f111-bec6-000d3a336093': 'CustomAPI:      lc_CalculateLaunchReadiness',
}

found = {c['objectid']: c['componenttype'] for c in comps if c['objectid'] in targets}

print()
print('--- Plugin / Custom API components in LaunchControl solution ---')
for tid, name in targets.items():
    if tid in found:
        print(f'  [IN ] {name} (componenttype={found[tid]})')
    else:
        print(f'  [OUT] {name}  <-- NOT in solution')
