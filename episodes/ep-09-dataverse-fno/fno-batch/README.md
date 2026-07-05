# Native F&O batch job: `LcProcurementSyncController`

This folder is a **deploy-ready X++ scaffold** for the Launch Control procurement
sync as a *native Finance and Operations batch job*. Once deployed and scheduled,
each run appears under **System administration > Inquiries > Batch jobs** (the
"Batch job history" screen).

It is the F&O-native counterpart of the external digest in
`../batch_launch_sync.py`. The external job reads the unified Dataverse model
(launch + procurement) and runs in GitHub Actions or the Dataverse CLI. This one
runs *inside* F&O and owns the procurement side: per-vendor open commitment
straight from `PurchTable` / `PurchLine`.

## Why this needs a dev box (and the external job does not)

An F&O batch job runs inside the F&O batch server and executes **compiled X++**.
There is no stock class that computes our rollup, so the logic has to be authored
in X++, compiled into a model, packaged as a deployable package, and installed on
the environment. That requires a F&O development environment (a tier-1 box with
Visual Studio and the X++ tools) and a deployment path (LCS asset library or an
Azure DevOps pipeline). It cannot be done from a data-plane CLI session, which is
exactly why the cross-system digest was built as an external job first.

## What is in this folder

| File | Element | Role |
|---|---|---|
| `LcProcurementSyncContract.xpp` | class (data contract) | Batch-dialog parameters: outstanding threshold, legal entity. |
| `LcProcurementSyncService.xpp` | class (SysOperation service) | Server-side body: aggregates open PO commitment per vendor, logs the digest, flags AT-RISK vendors. |
| `LcProcurementSyncController.xpp` | class (SysOperation controller) | Runnable, batch-enabled entry point. Renders the "Run in the background" tab so it can be scheduled. |

These are X++ *source* files (`.xpp`). Following the same "create metadata in the
tool, do not hand-author the element XML" rule this repo uses for Dataverse, you
create the three classes in Visual Studio (which generates the `AxClass` metadata)
and paste this source in. Do not hand-write the `AxClass\*.xml` files.

## Deploy runbook

Prerequisites: a F&O development VM (Visual Studio with the Finance and Operations
developer tools) connected to a build/dev environment, and permission to deploy a
package to the target environment via LCS or a release pipeline.

1. **Create a model.** In Visual Studio: *Dynamics 365 > Model Management > Create
   model*. Name it `LaunchControl`, new package, referencing
   `ApplicationSuite`, `ApplicationPlatform`, and `ApplicationFoundation` (for
   `PurchTable` / `PurchLine` and the SysOperation framework).
2. **Create a project** in that model (Finance Operations project template).
3. **Add three classes** to the project: `LcProcurementSyncContract`,
   `LcProcurementSyncService`, `LcProcurementSyncController`. Paste the body of
   the matching `.xpp` file into each.
4. **Add an Action menu item** named `LcProcurementSync` with *Object type* Class
   and *Object* `LcProcurementSyncController` so the job is launchable from a menu
   (optional but recommended; you can also run the class directly during testing).
5. **Build** the project (Dynamics 365 > Build models). Fix any reference gaps.
6. **Package.** *Dynamics 365 > Deploy > Create deployable package*; include the
   `LaunchControl` model.
7. **Deploy** the package to the target environment through LCS (Asset library >
   Software deployable package > apply) or your release pipeline.
8. **Schedule.** In the target: run the `LcProcurementSync` menu item (or the
   controller class), open the **Run in the background** tab, tick *Batch
   processing*, set a **Recurrence** (for example daily at 06:00) and a batch
   group, then OK.
9. **Verify.** *System administration > Inquiries > Batch jobs* now lists the job;
   open its history and the **Log** to see the per-vendor digest lines.

## Verify from the unified CLI

Once scheduled, the same job is visible from the unified Dataverse CLI, which is
what the nightly workflow uses to monitor F&O batches:

```
npx @microsoft/dataverse erp batch list
```

## Extending to committed-minus-invoiced

The scaffold reports open purchase-order line amount as outstanding commitment.
To match the external digest's committed / invoiced / outstanding columns, extend
`run()` to subtract the already-invoiced portion per vendor from `VendTrans`
(vendor transactions, `TransType == LedgerTransType::Purch`) or
`VendInvoiceJour`, joined on the vendor account. Keep it a second grouped
aggregate rather than a per-line method call so it stays set-based.
