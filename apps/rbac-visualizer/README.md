# RBAC & Data-Masking Visualizer

The Episode 8 demo app. Pick a persona, and the page runs *the same* launch
query as that user, then shows two things side by side:

- **Axis 1 — Row-level security:** how many `lc_*` rows each persona can read.
- **Axis 2 — Data masking:** whether the secured columns (`lc_blockerreason`,
  `lc_risksummary`) come back as cleartext or as a masked `████████`.

Impersonation is real. In live mode every Web API call carries the
`MSCRMCallerID` header set to the selected user's `systemuserid`, exactly like
the `rbac_validate.py` smoke-test. The platform decides what comes back; the app
just renders it. When a caller sits outside the `lc Sensitive Readers` field
security profile, Dataverse withholds the secured column, and the app shows that
as a red mask.

## Run it

```bash
pip install -r apps/rbac-visualizer/requirements.txt

# Offline demo — seeded snapshot, no Dataverse needed (use this for the recording)
python apps/rbac-visualizer/app.py --mock

# Live — uses scripts/auth.py + .env DATAVERSE_URL, discovers personas from the lc teams
python apps/rbac-visualizer/app.py
```

Then open http://127.0.0.1:5000 and switch personas from the dropdown.

If no `DATAVERSE_URL` is set, the app starts in demo mode automatically, so a
first run never errors.

## How masking is detected

A field-secured column is omitted (or returned null) in the Web API payload for
any caller outside the field security profile. The app treats **present** as
cleartext and **absent/null** as masked. That is the same signal an agent would
get: it literally cannot read the value, so it cannot leak it — including through
Episode 7's `search_data`.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Flask app: persona dropdown, impersonated queries, two-lens render. |
| `samples/snapshot.json` | Seeded data for `--mock` mode (mirrors the smoke-test). |
| `requirements.txt` | flask, requests, python-dotenv, azure-identity. |
