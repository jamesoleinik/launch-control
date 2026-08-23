---
name: dataverse-pcf-deployer
description: Build, import, place, publish, verify, and solution-package Power Apps Component Framework controls for Dataverse model-driven apps. Use when deploying a PCF control, binding it to a field or dataset, adding it to a form, changing form layout, publishing customizations, diagnosing stale bundles, or synchronizing generated control and form XML for ALM.
---

# Dataverse PCF Deployer

Treat control import, form placement, publication, and ALM synchronization as
separate verifiable phases. Read
[references/deployment-model.md](references/deployment-model.md) before
editing form XML.

## Workflow

1. Inspect the PCF manifest, namespace, constructor, version, bound properties,
   target table, target form, and unmanaged solution.
2. Build with the repository's existing `pcf-scripts` command.
3. Run lint and TypeScript checks through that build.
4. Package and import the control into the target environment.
5. Resolve exactly one live `customcontrol` by full control name.
6. Inspect the current model-driven form XML.
7. Apply an idempotent form transformation that preserves unrelated controls,
   labels, IDs, and layout.
8. Add the control and form to the unmanaged solution.
9. Publish the form; publish all customizations only if targeted publication
   does not expose the new version.
10. Verify live control version, binding, form placement, layout, and rendered
    behavior.
11. Export and unpack the solution to synchronize generated artifacts.

## Safety rules

- Never hardcode environment URLs, app IDs, form IDs, or control IDs.
- Select forms by table, type, and exact name; stop on zero or multiple rows.
- Parse XML and mutate nodes structurally. Do not use broad string replacement.
- Make placement idempotent and reject duplicate control bindings.
- Preserve unrelated form sections and controls.
- Increment the manifest version for every deployable control change.
- Do not report success from import alone; verify the live version and form.
- Do not use a fixed sleep for asynchronous imports. Poll the import job and
  surface failure details.
- Keep local build outputs and temporary solution packages uncommitted.

## Form placement contract

Define:

```text
control full name
target table
target form name and type
host tab, section, column, or bound field
expected dimensions and visibility
fallback behavior
```

For a field-bound control, preserve the standard control fallback unless the
UX explicitly requires replacement. For a full-width or dashboard-style
control, verify the form layout property that determines horizontal versus
vertical rendering.

## Verification

Verify:

1. build succeeds
2. manifest version equals the intended version
3. exactly one live custom control exists
4. live control version matches the manifest
5. exactly one target form exists
6. form XML contains one intended binding
7. bound property names match the manifest
8. tab, section, column count, widths, and layout orientation match
9. control and form belong to the unmanaged solution
10. published form renders the new bundle after a hard refresh
11. exported solution contains current control and form artifacts

If the form still renders an old control, verify version increment, import-job
completion, targeted publication, `PublishAllXml`, browser cache, and server
bundle version in that order.
