# BPF specification

```json
{
  "name": "Launch Approval",
  "unique_name": "lc_launchapproval",
  "table": "lc_launch",
  "solution": "LaunchControl",
  "process_order": 100,
  "security_roles": ["lc Admin", "lc Owner", "lc Member", "lc Viewer"],
  "app_unique_name": "lc_LaunchControl",
  "language_code": 1033,
  "stages": [
    {
      "name": "Draft",
      "category": 4,
      "steps": [
        {"label": "Launch Name", "field": "lc_name", "required": true},
        {"label": "Target Date", "field": "lc_targetdate", "required": true}
      ]
    },
    {
      "name": "Quality Gate",
      "category": 5,
      "steps": [
        {"label": "Quality Gate Status", "field": "lc_qualitygatestatus", "required": true}
      ]
    }
  ]
}
```

Required top-level properties:

- `name`: BPF display name
- `unique_name`: workflow unique name and generated BPF table logical name
- `table`: primary Dataverse table logical name
- `solution`: existing unmanaged solution unique name
- `stages`: ordered non-empty stage array

Stage properties:

- `name`: stage display name
- `category`: integer stage category; use `-1` when no category is wanted
- `steps`: ordered field steps

Step properties:

- `label`: display label
- `field`: logical column name on the stage table
- `required`: boolean, default `false`

Optional top-level properties:

- `language_code`: default `1033`
- `allow_duplicate_fields`: default `false`
- `process_order`: default `100`
- `security_roles`: role names allowed to use the BPF; omit for Everyone
- `app_unique_name`: model-driven app to receive the BPF component
