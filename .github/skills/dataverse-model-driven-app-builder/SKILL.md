---
name: dataverse-model-driven-app-builder
description: Create, update, publish, verify, and solution-package minimal Dataverse model-driven apps and their site maps from a declarative specification. Use when building a new model-driven app, adding or restricting table navigation, creating a one-table app, wiring forms or views into an app, or ensuring app and site-map components are included for ALM.
---

# Dataverse Model-Driven App Builder

Create a separate app when a workflow needs focused navigation. Do not remove
navigation from an existing app unless the user explicitly requests it.

Use `scripts/model_app_builder.py` with a declarative JSON specification.
`assets/launch-control-quality-gate.json` is the one-table Episode 11 example.

## Workflow

1. Resolve the target Dataverse URL and unmanaged solution from ignored
   configuration.
2. Define the app name, unique name, description, solution, and ordered table
   navigation entries.
3. Resolve every table, form, view, dashboard, and process component from live
   metadata. Stop on missing or ambiguous matches.
4. Run a dry-run that reports create, update, keep, and conflict actions.
5. Create or update the `appmodule` by exact unique name.
6. Build the site map structurally with stable generated IDs and only the
   requested navigation entries.
7. Add the required table, form, view, process, app, and site-map components to
   the unmanaged solution.
8. Validate and publish the app.
9. Verify the live app, navigation, component membership, and solution
   membership.
10. Export and unpack the solution so Dataverse-generated artifacts become the
    ALM source.

```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts\model_app_builder.py --spec path\to\app.json --env <episode> --dry-run
python scripts\model_app_builder.py --spec path\to\app.json --env <episode> --apply
python scripts\model_app_builder.py --spec path\to\app.json --env <episode> --verify
```

## Declarative contract

Collect:

```text
app display name
app unique name
description
unmanaged solution unique name
publisher prefix
ordered navigation entries
default table, form, and view
optional BPF unique names
```

Each navigation entry must identify a live table logical name and its intended
label. Resolve component IDs at runtime. Never put environment-specific GUIDs
in the specification.

## Safety rules

- Never hardcode environment URLs, tenant IDs, app IDs, site-map IDs, table
  metadata IDs, form IDs, view IDs, or process IDs.
- Match apps by exact unique name and require at most one result.
- Use dry-run before apply. Make apply idempotent.
- Preserve an existing app unless the requested specification targets that
  app's exact unique name.
- Parse and generate site-map XML structurally. Do not use broad string
  replacement.
- Keep navigation limited to the declared entries. Do not silently include all
  solution tables.
- Do not report success from record creation alone. Publish and verify the
  runnable app.
- Do not modify an app owned by another episode merely to make a focused demo.

## Verification

Verify:

1. exactly one app has the requested unique name
2. display name and description match
3. the app is enabled and published
4. navigation contains exactly the requested table entries in order
5. each entry opens the intended table and default view
6. intended forms, views, and BPFs are app components
7. no unrelated table appears in navigation
8. app, site map, tables, forms, views, and processes belong to the unmanaged
   solution
9. the exported solution contains the current app and site-map artifacts
10. the app opens successfully in a clean browser session

For a one-table app, test that the home navigation exposes only that table and
that a record opens with the intended form, BPF, and custom controls.