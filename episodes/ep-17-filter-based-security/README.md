# Episode 17: Filter-based Security in Dataverse (Public Preview)

> *Can a business attribute safely grant access to the records that match it,
> without changing who owns those records?*

**Status:** Public Preview. Validate current availability and limitations in an
isolated sandbox. Do not use preview features for production workloads.
**Season:** Dataverse security
**Hero capability:** Filter-based security on an existing user/team-owned table
**Result target:** Show that a Dataverse security role can grant access to
matching Launch records, while existing ownership rules and nonmatching records
remain distinguishable.

## The build: three sections

This episode demonstrates filter-based security as an additional row-level
grant on the existing Launch table. It does not rebuild Episode 8's roles,
teams, column security, or per-agent access model.

```text
Section 1  Choose the model  -> Compare additive filters with filtered ownership
Section 2  Design the policy -> Inspect a real column and preview a narrow filter
Section 3  Prove the boundary -> Compare matching and nonmatching records as a non-admin
```

## Section 1: Choose the model

Filter-based security uses a Record Filter, an Entity Record Filter that
associates it with a table, and filter privileges granted through a security
role. The policy evaluates record data. On a user/team-owned table, filter
privileges add access to the existing ownership-based model.

Filtered ownership is a different table ownership model. Its records have no
owner and cannot be assigned or shared; filters determine access. The ownership
type cannot be changed after table creation. This demo keeps the existing
ownership model and does not create a filtered-ownership table.

### Prompt

> I want a backup launch coordinator to read Launch records that match a
> business condition, without changing who owns them. Can you explain how
> filter-based security would add that access to our existing Launch table,
> and how that differs from filtered record ownership? Please check the current
> preview documentation and don't change anything yet.

### Result

- The existing user/team-owned model is distinguished from filtered ownership.
- The demo policy is additive and does not imply that a filter replaces other
  role, team, ownership, or sharing access.
- Preview limitations and the irreversible ownership-type decision are called
  out before implementation.

### Run it

> Review the current Microsoft Learn guidance for filter-based security and
> filtered record ownership. Tell me which model fits this demo and list the
> access and ownership tradeoffs before proposing changes.

## Section 2: Design the policy

Inspect the deployed `lc_launch` table and its `lc_launchstatus` choice values.
Use only a status and records confirmed in the isolated demo environment.
Prepare the FetchXML Record Filter, its Entity Record Filter association, the
specific operation privilege, and the role assignment as a reviewable plan.
Do not infer a status label or privilege from a different environment.

### Prompt

> Inspect the Launch table and its deployed status choices in my sandbox. Help
> me plan a narrowly scoped Read filter for one status that exists in the demo
> data. Show the FetchXML, table association, role privilege, affected test
> users, and rollback steps. Don't create or assign anything until I approve
> the exact plan.

### Result

- The filter uses the actual deployed table, column, choice, and demo rows.
- The planned role grants only the intended operation for matching records.
- Existing permissions and team memberships are checked so the expected
  result can be attributed to the filter.
- The preview support and query limitations are reviewed before applying.

### Run it

> Give me a read-only plan for the Launch status filter. Include the exact
> records and role changes it would affect, and stop for my approval before
> making any change.

## Section 3: Prove the boundary

Apply the approved plan only in the sandbox, using disposable demo records and
non-admin test users. Compare the same read as a principal with the filter
privilege and a control principal without it. Check both a matching and a
nonmatching record. System Administrators receive the system-provided **All
records** filter, so an administrator session cannot prove the row restriction.

If the demo changes a record's filter attribute, use a disposable record and
verify access before and after the change without changing its owner. Read back
the filter, table association, role grants, and test results. Remove the demo
configuration and data using a reviewed rollback plan.

### Prompt

> Apply the approved filter plan in this sandbox only. Using the same query,
> compare a non-admin test user with the filter role to a control user without
> it. Show one matching and one nonmatching Launch record, confirm that
> ownership did not change, and read back the filter and role configuration.
> Stop if the results differ from the plan. Don't touch production.

### Result

- The authorized non-admin can read the intended matching record.
- The control user cannot read that record through the filter grant, and the
  filtered user's query does not expose nonmatching records.
- Existing ownership, sharing, team, and role access are not confused with
  filter-based grants.
- Configuration and cleanup are verified from read-back evidence.

### Run it

> Verify the exact filter and role grants, then run the approved matching and
> nonmatching checks as non-admin users. Show me the source records and
> effective access. If any outcome is ambiguous, stop and report it.

## Stop conditions

- Public Preview is unavailable or the documented feature behavior has changed.
- The target environment is not an isolated sandbox.
- The table, choice values, filter query, role, or test identities are unclear.
- Admin access, ownership, sharing, or team membership could explain the result.
- A requested design depends on assigning or sharing filtered-ownership records.
- The query or filter behavior is unsupported or has not been verified.

## Pre-record checklist

- [ ] Current preview availability and documentation are confirmed.
- [ ] The demo uses the existing Launch ownership type and sandbox data.
- [ ] The exact filter and role changes were reviewed before applying.
- [ ] Matching and nonmatching results are tested as non-admin users.
- [ ] Admin All records access is not used as proof of restriction.
- [ ] Read-back and rollback are verified; captures contain no tenant identifiers or personal data.

## References

- [Filter-based security in Microsoft Dataverse (preview)](https://learn.microsoft.com/en-us/power-platform/admin/filter-based-security)
- [Filtered record ownership](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/filtered-view-record-ownership)
- [Filtered record ownership with code (preview)](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/filtered-record-ownership?tabs=sdk)
- [Episode 8: Roles & Reach](../ep-08-security/README.md) and its [security model](../ep-08-security/SKILL.md)
- [Episode 16: External Agents](../ep-16-external-agents/README.md)

## Voice-over

[LinkedIn video script](voiceover-script.md)
