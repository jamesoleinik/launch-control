---
name: dataverse-plugin-deployer
description: Build, register, update, verify, troubleshoot, and solution-package Dataverse plug-in assemblies and SDK message processing steps. Use when deploying C# IPlugin code, changing a plug-in DLL, configuring message/entity/stage/mode/filtering attributes, diagnosing execution depth or trace failures, or synchronizing plug-in artifacts for ALM.
---

# Dataverse Plug-in Deployer

Use a dry-run, apply, verify workflow. Read
[references/registration-model.md](references/registration-model.md) before
writing a registration script.

## Workflow

1. Inspect the solution, project, assembly name, plug-in types, and intended
   SDK message steps.
2. Define each step declaratively: name, type, message, primary table, stage,
   mode, rank, filtering attributes, and impersonation behavior.
3. Build Release and fail on compiler warnings or errors relevant to the
   deployment.
4. Run registration `--dry-run`; report create, update, skip, and conflict
   actions without mutation.
5. Run `--apply` to upsert the assembly, discover types, and upsert steps.
6. Add the assembly and steps to the unmanaged solution.
7. Run `--verify` against live registration state.
8. Execute an isolated behavior matrix and clean up test rows.
9. Export and unpack the solution, then synchronize the built DLL and generated
   registration metadata.

## Registration rules

- Match an assembly by exact name and require at most one result.
- Update existing assembly content instead of creating a duplicate.
- Match plug-in types by exact fully qualified type name.
- Resolve SDK messages and message filters from live metadata.
- Match steps by a stable unique name and verify all behavior fields.
- Use synchronous pre-operation or post-operation only when transaction
  semantics require it. Explain the stage choice.
- Set filtering attributes for Update steps to avoid unnecessary executions.
- Treat execution depth as evidence, not a universal recursion rule.
- Do not use a blanket `Depth > 1` guard when a supported platform operation
  legitimately invokes the plug-in at depth 2.
- Never swallow `InvalidPluginExecutionException` or return success after a
  failed governed operation.

## ALM rules

- Register into an unmanaged solution.
- Include the plug-in assembly and every SDK message processing step.
- Store source and project files in the repository.
- Build the DLL from the committed source before solution synchronization.
- Export and unpack after live registration so generated IDs and metadata come
  from Dataverse.
- Verify the solution contains the assembly and steps before committing.
- Never commit credentials, environment URLs, or user IDs.

## Verification

Verify:

1. exactly one assembly exists
2. assembly content matches the latest Release build
3. every expected type exists
4. every expected step exists and is enabled
5. message, table, stage, mode, rank, and filtering attributes match
6. assembly and steps are solution components
7. a success case produces the intended records and attribution
8. unauthorized, duplicate, and invalid-state cases fail
9. trace output contains no unexpected recursion or silent failure
10. isolated test data is removed

If registration is correct but behavior is wrong, inspect Plug-in Trace Log and
the actual execution depth, initiating user, target attributes, and images
before changing permissions or recursion guards.
