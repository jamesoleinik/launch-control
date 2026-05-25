# Custom Virtual Entity Provider: Step-by-Step Guide

This guide documents every step needed to create a custom virtual entity data provider 
for Dataverse — using GitHub Issues as the example. These steps were validated against 
a real environment and include workarounds for common pitfalls.

## Prerequisites

- .NET Framework 4.6.2 targeting pack (or .NET 4.7.2+)
- PAC CLI authenticated to target environment
- Python with `azure-identity` for Web API scripts
- Plugin Registration Tool (PRT) — install via `pac tool PRT`

## Step 1: Build the Plugin Assembly

```bash
cd datamodel/virtual-entities/GitHubIssuesProvider/GitHubIssuesProvider
dotnet build --configuration Release
```

**Key notes:**
- Target `net462` in the `.csproj`
- Must be signed with a strong name key (`key.snk`)
- Use `DataContractJsonSerializer` with `DateTimeFormat` for ISO 8601 dates:
  ```csharp
  var settings = new DataContractJsonSerializerSettings {
      DateTimeFormat = new DateTimeFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
  };
  ```
- Plugin must run in Sandbox isolation mode
- Avoid external NuGet dependencies — use only `Microsoft.CrmSdk.CoreAssemblies` and BCL

## Step 2: Register the Plugin Assembly (Web API)

```python
# Register via Web API POST to /api/data/v9.2/pluginassemblies
# Body: { "name": "GitHubIssuesProvider", "content": "<base64-DLL>", "isolationmode": 2, "sourcetype": 0 }
python scripts/register_ve_plugin.py
```

**Returns:** Assembly ID (e.g., `f159854b-c042-f111-bec6-000d3a336093`)

## Step 3: Register Plugin Types (Web API)

Plugin types are NOT auto-registered when you upload an assembly. Register each one explicitly:

```python
# POST to /api/data/v9.2/plugintypes for each plugin class:
#   - GitHubIssuesProvider.RetrieveMultiplePlugin
#   - GitHubIssuesProvider.RetrievePlugin
# Body: { "typename": "...", "friendlyname": "...", "name": "...", 
#          "pluginassemblyid@odata.bind": "/pluginassemblies(<assembly-id>)" }
```

**Returns:** Plugin Type IDs for each plugin.

## Step 4: Register the Data Provider — PRT (GUI) or Web API (script)

> **Update (May 2026):** PRT is **optional.** The original "the Web API can't do this" claim was wrong. We reverse-engineered what PRT writes ([`scripts/python/register_ve_data_provider.py`](../../scripts/python/register_ve_data_provider.py)) and verified the rebuild path end-to-end from a clean slate (full teardown → re-register via Web API → query returns 6 live GitHub issues). PRT remains the recommended on-camera path because the GUI dialog is more discoverable for viewers; the script is the documented Web-API alternative.

**The two paths produce the same two rows:**

1. **One `entitydataproviders` row** — has one column per SDK message (`retrievemultipleplugin`, `retrieveplugin`, `createplugin`, `updateplugin`, ...). Implemented operations get your plugin-type GUIDs; every unimplemented slot gets the OOB "Not Implemented" plugintype (`c1919979-0021-4f11-a587-a8f904bdfdf9`). The `datasourcelogicalname` column links to row 2 by **logical name** (not GUID).
2. **One data-source virtual entity** — a regular `TableType=Virtual` entity backed by the OOB `JsonConverter` data provider (`b2112a7e-b26c-42f7-9b63-9a809a9d716f`). Holds the provider's configuration rows.

Neither PRT nor the script creates any `sdkmessageprocessingsteps` for VE data providers — the binding IS the entitydataprovider row's own columns. This is different from "regular" plugins bound to a specific message.

### Three Web-API gotchas (only relevant for the script path)

If you write your own version of `register_ve_data_provider.py` from scratch, these are the three errors you will hit in order — captured from the clean-slate rebuild test:

| Symptom | Cause | Fix |
|---|---|---|
| `400 CanChangeTrackingBeEnabled can not be active for ... virtual Entity` | The data-source entity is itself a virtual entity and needs the full virtual-entity managed-property set | Include `ChangeTrackingEnabled: false`, `CanChangeTrackingBeEnabled: {Value: false, CanBeChanged: false}`, `IsAvailableOffline`, `IsVisibleInMobileClient`, `CanCreateCharts` on the data-source entity create |
| `400 You must specify a value for the External Collection Name property` | Only `ExternalName` was set | Set both `ExternalName` AND `ExternalCollectionName` |
| `400 An ODataPrimitiveValue was instantiated with a value of type 'ODataEntityReferenceLink'` when creating the `entitydataprovider` row | The `*plugin` columns look like lookups but are `Uniqueidentifier` primitives | Send each plugin column as a **raw GUID string**, not `@odata.bind`. Confirmed via `EntityDefinitions(LogicalName='entitydataprovider')/Attributes` — all 20 plugin columns are `AttributeType=Uniqueidentifier` |

### PRT Connection Troubleshooting

- **MFA Error (AADSTS50076):** Leave the username/password fields BLANK and click Login. 
  PRT will launch a browser-based login dialog that supports MFA.
- **"Office 365" only (no OAuth option):** The blank-login workaround above solves this.
- Install PRT via: `pac tool PRT`

### In PRT:

1. Connect to your environment
2. Register → Register New Data Provider
3. Fill in:
   - **Name:** `GitHubIssuesProvider`
   - **Solution:** Select your solution (e.g., `LaunchControl`)
   - **Data Source Table:** Create New → name it (e.g., `GitHub Data Source`)
   - **RetrieveMultiple:** Select `GitHubIssuesProvider.RetrieveMultiplePlugin`
   - **Retrieve:** Select `GitHubIssuesProvider.RetrievePlugin`
   - Leave Create/Update/Delete empty for read-only providers
4. Click Register

**Result:** Creates both the `entitydataprovider` record AND the `lc_githubdatasource` 
virtual entity that serves as the data source configuration table.

## Step 5: Create the Virtual Table (Web API)

**IMPORTANT:** The `CanCreateCharts` managed property MUST be set to `False` for virtual 
entities, or creation will fail with "Cannot create charts for virtual Entity."

```python
payload = {
    "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
    "SchemaName": "lc_GitHubIssue",
    "DisplayName": label("GitHub Issue"),
    "DisplayCollectionName": label("GitHub Issues"),
    "OwnershipType": "OrganizationOwned",
    "TableType": "Virtual",
    "IsActivity": False,
    "HasActivities": False,
    "HasNotes": False,
    "ChangeTrackingEnabled": False,
    "CanChangeTrackingBeEnabled": {"Value": False, "CanBeChanged": False},
    "IsAvailableOffline": False,
    "IsVisibleInMobileClient": {"Value": False, "CanBeChanged": False},
    "CanCreateCharts": {"Value": False, "CanBeChanged": False},  # CRITICAL
    "ExternalName": "github_issues",
    "ExternalCollectionName": "github_issues",
    "DataProviderId": "<provider-id-from-step-4>",  # Must be the PRT-created one with datasource
    "Attributes": [
        {
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "SchemaName": "lc_Name",
            "MaxLength": 500,
            "IsPrimaryName": True,
            "ExternalName": "title",
            "DisplayName": label("Title"),
        }
    ]
}
# POST to /api/data/v9.2/EntityDefinitions
```

**DO NOT** try to create a virtual table using the Python SDK `client.tables.create()` — 
it creates a Standard table, not Virtual. Virtual tables require the Web API with 
`TableType: "Virtual"`.

## Step 6: Add Columns to the Virtual Table (Web API)

```python
# POST to /api/data/v9.2/EntityDefinitions(<table-metadata-id>)/Attributes
columns = [
    {"@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata", 
     "SchemaName": "lc_IssueNumber", "ExternalName": "number", ...},
    {"@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata", 
     "SchemaName": "lc_State", "ExternalName": "state", ...},
    # etc.
]
```

Each column's `ExternalName` must match the attribute name used in the plugin code.

## Step 7: Update the Plugin (PAC CLI)

When you need to update the plugin code (e.g., fix a bug):

```bash
pac plugin push --pluginId <assembly-id> \
  --pluginFile "path/to/GitHubIssuesProvider.dll" \
  --type Assembly
```

This is much faster than re-registering — it updates the assembly in-place.

## Step 8: Test via MCP

```sql
SELECT lc_name, lc_state, lc_issuenumber FROM lc_githubissue
```

This triggers the plugin's `RetrieveMultiplePlugin.Execute()`, which calls the GitHub API 
and returns issues as Dataverse records.

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `CanChangeTrackingBeEnabled can not be active` | Missing managed property on virtual entity | Add `"CanChangeTrackingBeEnabled": {"Value": False, "CanBeChanged": False}` |
| `Cannot create charts for virtual Entity` | Missing managed property | Add `"CanCreateCharts": {"Value": False, "CanBeChanged": False}` |
| `DateTime content does not start with /Date(` | `DataContractJsonSerializer` defaults to MS date format | Use `DateTimeFormat` setting for ISO 8601 |
| `dependent component does not exist` | Provider created without data source entity | Use PRT to create provider+datasource together |
| `AADSTS50076 MFA error in PRT` | Office 365 auth mode doesn't support MFA | Leave username blank → PRT opens browser auth |
| `entity logicalname not found` | Using schema name instead of logical name | Use lowercase logical names (e.g., `lc_milestone` not `lc_Milestone`) |
| `lc_launches not found` | Wrong entity set name | Check entity set name via `client.tables.get()` — it's `lc_launchs` not `lc_launches` |
| SDK `filters.py` SyntaxError on Python 3.11 | f-string nesting requires Python 3.12+ | Patch the SDK: replace nested f-string with concatenation |
