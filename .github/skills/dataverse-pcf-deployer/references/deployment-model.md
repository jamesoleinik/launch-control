# PCF deployment model

## Distinct deployment states

| State | Proof |
|---|---|
| Source build | `pcf-scripts build` succeeds |
| Packaged control | temporary solution contains manifest and bundle |
| Imported control | live `customcontrols` row has expected name and version |
| Form placement | target `systemform.formxml` contains intended binding |
| Publication | published form serves the current layout and bundle |
| ALM sync | unpacked solution contains current control and form artifacts |

Do not collapse these into a single "deployed" check.

## Build and version

Use the existing project tooling:

```powershell
npm run build
```

The manifest version is the deployment cache key. Increment it before importing
changed TypeScript, CSS, resources, or manifest metadata.

## Import

Prefer a generated temporary unmanaged solution wrapper or the repository's
existing packaging workflow. Submit the import asynchronously and poll its job
record until completion. Surface the import-job failure data instead of
returning a success-shaped timeout.

Resolve the control from `customcontrols` by its full namespace and constructor
name. If fallback substring matching is needed for diagnosis, never use it for
mutation without an exact-one check.

## Form XML transformation

Read `systemforms` for the target table and main form type. Parse `formxml` with
an XML library.

An idempotent transformer should:

1. locate the target tab and section by stable names or labels
2. find an existing binding by full control name
3. create missing nodes once
4. update only owned attributes
5. preserve unknown attributes and unrelated nodes
6. serialize valid XML
7. skip the patch when the desired state already exists

For side-by-side layouts, verify the actual orientation attribute and each
column width. Do not infer layout from section names.

## Solution membership

Add:

- the custom control component
- the target system form
- related web resources only when the control depends on separately deployed
  resources

Export and unpack after live changes. Treat generated GUIDs and XML as
Dataverse-owned artifacts.

## Publication and cache diagnosis

Use targeted `PublishXml` first. If Dataverse still serves stale form metadata
or control assets after a successful import, use `PublishAllXml`, then hard
refresh the model-driven app.

Diagnose in this order:

1. source manifest version
2. built manifest and bundle timestamp
3. imported custom control version
4. import job result
5. form binding and layout
6. targeted publication
7. publish all
8. browser cache

## Live verification

Query the live custom control and form, then assert the exact expected state.
Finally, open the model-driven form and confirm:

- the control initializes without console errors
- data loads under the current user's Dataverse privileges
- sizing and responsive layout match the design
- timeline or neighboring controls remain usable
- fallback behavior is acceptable when the PCF cannot initialize
