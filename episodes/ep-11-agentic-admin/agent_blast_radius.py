"""episodes/ep-11-agentic-admin/agent_blast_radius.py

Episode 11 proof point #4: enumerate every agent in this env + what it can touch.

Sources:
  - bot                 (Copilot Studio agents)
  - botcomponent        (per-agent: topics, actions, MCP refs, triggers, gen orchestration)
  - workflow            (Power Automate cloud flows: category 5, modern)
  - connectionreference (connectors flows + agents bind to)

Output sections:
  1. Custom agents (non-msdyn, schema doesn't start with msdyn_)
  2. Pre-built / template agents (msdyn_*)
  3. Active modern cloud flows + their connection references
  4. Connector usage roll-up across the env

Use:
  python episodes/ep-11-agentic-admin/agent_blast_radius.py
  python episodes/ep-11-agentic-admin/agent_blast_radius.py --json
  python episodes/ep-11-agentic-admin/agent_blast_radius.py --custom-only
"""
from __future__ import annotations
import argparse, json, os, sys
from collections import Counter, defaultdict
from typing import Any, Dict, List

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from dotenv import load_dotenv
from auth import get_credential

# botcomponent.componenttype enum (observed in this env; not exhaustive but covers what we display)
COMPONENT_TYPE = {
    0: 'misc', 2: 'entity', 4: 'option', 6: 'flow-ref', 7: 'flow-ref', 8: 'flow-ref',
    9: 'topic-or-action', 10: 'library-intent', 12: 'skill',
    15: 'gen-orchestration', 16: 'knowledge-topic', 17: 'external-trigger', 18: 'tool',
}
# Within type 9, the schemaname prefix tells us topic vs action
def classify_type9(schema: str) -> str:
    s = schema or ''
    if '.action.' in s: return 'action'
    if '.topic.' in s: return 'topic'
    return 'other'


def fetch_all(url: str, headers: dict) -> List[dict]:
    out, full = [], url
    while full:
        r = requests.get(full, headers=headers); r.raise_for_status()
        j = r.json(); out += j.get('value', [])
        full = j.get('@odata.nextLink')
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--json', action='store_true', help='machine-readable output')
    p.add_argument('--custom-only', action='store_true',
                   help='hide msdyn_* template/pre-built agents')
    args = p.parse_args()

    load_dotenv(os.path.join(ROOT, '.env'))
    base = os.environ['DATAVERSE_URL']
    tok = get_credential().get_token(base + '/.default').token
    h = {'Authorization': 'Bearer ' + tok, 'Accept': 'application/json'}

    bots = fetch_all(
        base + "/api/data/v9.2/bots?$select=name,botid,schemaname,statecode,publishedon,createdon",
        h)
    components = fetch_all(
        base + "/api/data/v9.2/botcomponents?$select=name,componenttype,schemaname,_parentbotid_value",
        h)
    flows = fetch_all(
        base + "/api/data/v9.2/workflows?$select=name,workflowid,statecode,clientdata,uniquename"
               "&$filter=category eq 5", h)
    connrefs = fetch_all(
        base + "/api/data/v9.2/connectionreferences?$select=connectionreferencedisplayname,"
               "connectionreferencelogicalname,connectorid", h)

    # roll components into per-bot summary
    by_bot: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        'actions': [], 'topics_user': [], 'gen_orchestration': False,
        'external_triggers': [], 'knowledge_topics': [], 'mcp_actions': [],
    })
    for c in components:
        bid = c.get('_parentbotid_value')
        if not bid: continue
        ct = c.get('componenttype')
        nm = c.get('name') or '?'
        sch = c.get('schemaname') or ''
        slot = by_bot[bid]
        if ct == 9:
            kind = classify_type9(sch)
            if kind == 'action':
                slot['actions'].append(nm)
                if 'mcp' in nm.lower() or 'mcp' in sch.lower():
                    slot['mcp_actions'].append(nm)
            elif kind == 'topic':
                # exclude system topics (Greeting, Goodbye, etc.); detect via well-known names
                if nm.strip() not in {'Thank you','Conversation Start','Goodbye','Escalate',
                              'Multiple Topics Matched','Start Over','Greeting',
                              'Reset Conversation','On Error','Fallback','Sign in',
                              'Conversational boosting','End of Conversation'}:
                    slot['topics_user'].append(nm)
        elif ct == 15:
            slot['gen_orchestration'] = True
        elif ct == 16:
            slot['knowledge_topics'].append(nm)
        elif ct == 17:
            slot['external_triggers'].append(nm)

    # flow connector refs
    flow_summary = []
    for f in flows:
        cd = f.get('clientdata') or '{}'
        try:
            d = json.loads(cd)
            refs = d.get('properties', {}).get('connectionReferences', {}) or {}
            connectors = sorted({(v.get('api') or {}).get('name','?') for v in refs.values()})
        except Exception:
            connectors = []
        flow_summary.append({
            'name': f.get('name'),
            'state': 'active' if f.get('statecode') == 1 else 'draft/off',
            'connectors': connectors,
        })

    connector_usage = Counter(
        (cr.get('connectorid') or '?').rsplit('/', 1)[-1] for cr in connrefs)

    # split bots
    custom, prebuilt = [], []
    for b in bots:
        rec = {
            'name': b.get('name'), 'schemaname': b.get('schemaname'),
            'state': 'active' if b.get('statecode') == 0 else 'inactive',
            'published': b.get('publishedon') is not None,
            **by_bot.get(b.get('botid'), {}),
        }
        rec.setdefault('actions', []); rec.setdefault('topics_user', [])
        rec.setdefault('mcp_actions', []); rec.setdefault('external_triggers', [])
        rec.setdefault('knowledge_topics', []); rec.setdefault('gen_orchestration', False)
        if (rec['schemaname'] or '').startswith('msdyn_'):
            prebuilt.append(rec)
        else:
            custom.append(rec)

    # build report
    report = {
        'env_url': base,
        'totals': {
            'bots': len(bots), 'custom_bots': len(custom),
            'prebuilt_bots': len(prebuilt),
            'modern_flows': len(flows),
            'active_modern_flows': sum(1 for fs in flow_summary if fs['state'] == 'active'),
            'connection_references': len(connrefs),
        },
        'custom_agents': custom,
        'prebuilt_agents': [] if args.custom_only else prebuilt,
        'flows': flow_summary,
        'connector_usage': connector_usage.most_common(),
    }

    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    # pretty
    print(f"\nEnv: {base}")
    t = report['totals']
    print(f"Bots: {t['bots']}  (custom: {t['custom_bots']}, pre-built: {t['prebuilt_bots']})")
    print(f"Modern cloud flows: {t['modern_flows']}  (active: {t['active_modern_flows']})")
    print(f"Connection references: {t['connection_references']}\n")

    print("=" * 70)
    print("CUSTOM AGENTS (in-house)")
    print("=" * 70)
    for a in custom:
        print(f"\n  {a['name']}  [{a['state']}, {'published' if a['published'] else 'unpublished'}]")
        print(f"    schema:        {a['schemaname']}")
        print(f"    gen-orchestr.: {'yes' if a['gen_orchestration'] else 'no'}")
        print(f"    actions:       {len(a['actions'])}  (MCP-backed: {len(a['mcp_actions'])})")
        for x in a['actions'][:6]: print(f"      - {x[:65]}")
        if a['actions'] and len(a['actions']) > 6:
            print(f"      ... +{len(a['actions']) - 6} more")
        print(f"    user topics:   {len(a['topics_user'])}")
        for x in a['topics_user'][:4]: print(f"      - {x[:65]}")
        print(f"    triggers:      {len(a['external_triggers'])}")
        for x in a['external_triggers']: print(f"      - {x[:65]}")
        print(f"    knowledge:     {len(a['knowledge_topics'])}")

    if not args.custom_only:
        print("\n" + "=" * 70)
        print(f"PRE-BUILT / TEMPLATE AGENTS ({len(prebuilt)} -- collapse with --custom-only)")
        print("=" * 70)
        active_pre = [a for a in prebuilt if a['state'] == 'active']
        with_actions = [a for a in active_pre if a['actions']]
        with_triggers = [a for a in active_pre if a['external_triggers']]
        print(f"  active: {len(active_pre)}  with actions: {len(with_actions)}  with triggers: {len(with_triggers)}")

    print("\n" + "=" * 70)
    print("ACTIVE MODERN FLOWS (data-plane access)")
    print("=" * 70)
    for fs in flow_summary:
        if fs['state'] == 'active':
            print(f"  {fs['name'][:60]:60s} -> {', '.join(fs['connectors'])[:60]}")
    if not any(fs['state'] == 'active' for fs in flow_summary):
        print(f"  (none of {len(flow_summary)} flows currently active)")

    print("\n" + "=" * 70)
    print("CONNECTOR USAGE (across all connection references)")
    print("=" * 70)
    for connector, n in report['connector_usage'][:15]:
        print(f"  {n:>3}  {connector}")

    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
