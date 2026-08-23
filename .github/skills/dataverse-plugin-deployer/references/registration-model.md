# Dataverse plug-in registration model

## Core tables

| Table | Purpose |
|---|---|
| `pluginassemblies` | Assembly metadata and base64 DLL content |
| `plugintypes` | Discoverable `IPlugin` types in an assembly |
| `sdkmessages` | Create, Update, Delete, and other message definitions |
| `sdkmessagefilters` | Valid primary-table bindings for messages |
| `sdkmessageprocessingsteps` | Registered execution steps |
| `solutioncomponents` | ALM membership |

Use supported APIs or SDK clients. Resolve IDs from live metadata rather than
hardcoding them.

## Declarative step shape

Keep registration intent in data:

```json
{
  "name": "Quality Gate Result: Apply and Advance",
  "typename": "Example.ApplyResultPlugin",
  "message": "Create",
  "entity": "example_result",
  "stage": 40,
  "mode": 0,
  "rank": 1,
  "filteringattributes": ""
}
```

Use constants or named enums in implementation code so raw numeric values are
not unexplained.

## Idempotent upsert

1. Query exact assembly name.
2. If absent, create with Release DLL content and isolation settings.
3. If present once, patch content.
4. If present more than once, stop.
5. Resolve each plug-in type by fully qualified name.
6. Resolve the SDK message and compatible message filter.
7. Query exact step name.
8. Create or patch the full behavior contract.
9. Verify live values after writes.

Do not assume a DLL update changes step registration. Treat assembly content
and step behavior as separate state.

## Pipeline guidance

| Stage | Typical use |
|---|---|
| Pre-validation | reject before the database transaction |
| Pre-operation | mutate target or validate within transaction |
| Post-operation sync | create related records or project a committed row in transaction |
| Post-operation async | noncritical work that can complete later |

Choose synchronous steps for rules that must atomically block or advance a
governed process. Avoid external network calls in a synchronous sandbox step.

## Execution depth

Depth greater than 1 does not always mean recursion. A supported server
operation or MCP tool can invoke another plug-in internally. Protect against
the specific recursive path:

- inspect message, primary table, parent context, and changed attributes
- make writes idempotent
- reject only depths that cannot occur in supported flows
- test both direct Web API and mediated tool paths

## Trace diagnosis

Record only safe diagnostics:

- correlation and operation IDs
- plug-in type, message, stage, mode, and depth
- initiating and effective user IDs when policy permits
- target logical name and changed attribute names
- decision branch and validation failure

Never trace secrets, access tokens, full sensitive row payloads, or personal
data.

## Solution synchronization

After registration:

1. Add assembly and steps to the unmanaged solution.
2. Export the solution.
3. Unpack it with the repository's existing tooling.
4. Copy the exact built DLL into the unpacked plug-in assembly folder when the
   solution unpack format requires it.
5. Verify source build and stored DLL hashes match.
6. Review generated XML instead of hand-authoring IDs.
