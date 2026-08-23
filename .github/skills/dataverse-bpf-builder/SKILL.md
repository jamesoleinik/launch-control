---
name: dataverse-bpf-builder
description: Create, activate, verify, and solution-package standard Dataverse Business Process Flows programmatically from a declarative JSON specification. Use when a user asks to build a BPF, add process stages or data steps, automate a stage-gated lifecycle, replace manual BPF designer work, inspect an existing BPF, or ensure the generated BPF table is included for ALM.
---

# Dataverse BPF Builder

Use `scripts/bpf_builder.py`. It uses the official Dataverse Python SDK for
workflow record operations and the Dataverse Web API only for unbound solution
component actions that the SDK does not expose.

## Workflow

1. Confirm the target Dataverse URL and unmanaged solution.
2. Create a JSON spec using `references/spec.md`. Include human security roles,
   process order, and a model-driven app unique name when applicable.
3. Run `--dry-run` to validate the table, fields, field types, duplicate steps,
   unique name, and solution without writing.
4. Run `--apply` to create and activate the BPF.
5. Run `--verify` to compare the live active workflow against the spec.
6. Export and unpack the solution after creation.

```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts\bpf_builder.py --spec path\to\bpf.json --dry-run
python scripts\bpf_builder.py --spec path\to\bpf.json --apply
python scripts\bpf_builder.py --spec path\to\bpf.json --verify
```

Authentication uses `AzureCliCredential`. Set `DATAVERSE_URL` and optionally
`TENANT_ID`, or pass `--url`.

## Rules

- Never create a BPF outside an unmanaged solution.
- Never edit solution XML by hand to create the BPF.
- Validate every step field against live table metadata before writing.
- Use one field at most once per stage unless the spec explicitly sets
  `allow_duplicate_fields`.
- Keep `clientdata` and XAML IDs identical. The script owns all IDs.
- Activate only after the draft record is created successfully.
- Add workflow component type `29` to the solution.
- After activation, add the generated BPF table component type `1` to the same
  solution. Without it, solution export fails.
- Apply BPF visibility only to the security roles named in the spec. Do not
  grant an automation or agent role unless explicitly requested.
- Add the BPF to the specified model-driven app and publish it.
- Set process order even when only one BPF currently exists, so later additions
  have a deterministic default.
- Do not patch `IsBusinessProcessEnabled`. Dataverse sets it automatically.
- For an existing BPF, use `--verify`; do not silently replace or duplicate it.
- Use `--replace` only when the user explicitly approves replacing a draft BPF.
  Never replace an active BPF automatically.

## Supported step fields

The script maps String, Memo, URL, Integer, Decimal, Money, Double, DateTime,
Picklist, Boolean, State, Status, Lookup, Owner, and Customer attributes to BPF
controls. If a type is unsupported, stop and reverse-engineer a working active
BPF that uses that field type rather than guessing.

## After creation

Verify:

- workflow category is `4`
- primary table matches the spec
- state is active
- stage names and order match
- each stage has the expected fields exactly once
- required flags match
- the generated table logical name equals the workflow unique name
- workflow and generated table are both solution components
- security-role visibility matches the spec
- process order matches the spec
- the BPF is included in the specified model-driven app

Then export and unpack the solution so Dataverse-generated XML becomes the
repository artifact.
