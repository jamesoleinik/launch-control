# Episode 17 voiceover: Filter-based Security in Dataverse

**Estimated duration:** About 90 seconds
**Spoken word count:** 184

| Shot | Spoken copy |
|---|---|
| Show two Launch records with different status values, then highlight a filter. | Dataverse security has traditionally used roles, ownership, teams, and sharing. In public preview, filter-based security adds another way to decide which rows a user can access: evaluate business data on the record itself. |
| Show the existing Launch table and a simple filter plan. | In this demo, we keep the existing Launch ownership model. A security role grants a backup coordinator read access to records matching an approved filter. Ownership stays in place, and records outside the filter remain outside that grant. |
| Show the Record Filter, its table association, and the role grant. | We inspect the actual table and status choices, preview the filter, and review the role changes before applying them in an isolated sandbox. No guessed fields, no production data, and no change without approval. |
| Compare results for two non-admin users. | Then we run the same query as two non-admin test users. One has the filter privilege; the control user does not. We check both a matching and a nonmatching record, and read back the policy. |
| Show “Preview” and “Sandbox only,” then close on matching versus nonmatching results. | Filtered record ownership is a separate model: records have no owner and cannot be assigned or shared. We do not switch the Launch table to that model. This is a preview, so we validate its limits and never treat an administrator's access as proof. |
