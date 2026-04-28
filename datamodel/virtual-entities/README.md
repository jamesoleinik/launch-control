# Episode 3: Virtual Entities — Connecting the Dots

## Overview

This episode demonstrates two approaches to virtual entities:

1. **OOB SharePoint List** — point-and-click configuration in the Power Apps maker portal
2. **Custom GitHub Issues Provider** — a .NET plugin that queries the GitHub API and surfaces issues as Dataverse records

## Custom GitHub Issues Provider

### What it does
- Implements `RetrieveMultiple` to fetch issues from a GitHub repo
- Implements `Retrieve` to fetch a single issue by its deterministic GUID
- Maps GitHub issue fields to Dataverse columns: title, body, state, assignee, labels, dates
- Uses deterministic GUIDs (derived from issue number) so the same issue always maps to the same record ID
- Filters out pull requests (GitHub API returns them as issues)

### Project structure
```
GitHubIssuesProvider/
├── GitHubIssuesProvider.csproj  # .NET 4.6.2 class library
├── Class1.cs                     # RetrieveMultiplePlugin + RetrievePlugin
└── key.snk                       # Strong name key (not committed)
```

### Build
```bash
cd datamodel/virtual-entities/GitHubIssuesProvider/GitHubIssuesProvider
dotnet build --configuration Release
```

### Registration steps (after build)
1. Register the assembly using the Plugin Registration Tool
2. Create a virtual entity data provider pointing to the registered plugins
3. Create a virtual entity data source with the GitHub repo owner/name
4. Create the virtual table `lc_GitHubIssue` with columns matching the plugin output
5. Map the virtual table to the data provider

### Columns exposed
| Dataverse Column | GitHub Field | Type |
|-----------------|-------------|------|
| lc_name | title | String |
| lc_description | body | Memo |
| lc_issuenumber | number | Integer |
| lc_state | state (open/closed) | String |
| lc_url | html_url | String |
| lc_assignee | assignee.login | String |
| lc_createdat | created_at | DateTime |
| lc_updatedat | updated_at | DateTime |
| lc_labels | labels (comma-separated) | String |

## OOB SharePoint List Virtual Entity

For the SharePoint List OOB virtual entity, see the [Power Apps documentation](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/virtual-entity-walkthrough-using-odata-provider).

Configuration steps:
1. In Power Apps maker portal → Tables → New table → Virtual table
2. Select "SharePoint" as the data provider
3. Enter your SharePoint site URL and list name
4. Map columns from the SharePoint list to Dataverse columns
5. The virtual table appears alongside native tables
