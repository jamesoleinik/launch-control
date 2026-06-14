# Q3 trigger emails (Episode 7 Part 2, Setup B)

Send both of these to **`jamesol@a365preview001.onmicrosoft.com`** before the take.
Attach the matching PDF from this directory to each one.

## Email A - ENRICH (overlaps the seeded export-crash baseline task)

**Subject:** `Q3 Widget Launch - export to CSV crashes the app for Northwind`

**Attachment:** `Q3-widget-export-crash-northwind.pdf`

**Body:**

> Q3 Widget Launch field report from Northwind.
>
> Northwind hit a hard crash on Export to CSV with a large widget composition (about 14 widgets on one canvas). The export spinner runs for roughly 30 seconds and then the app crashes back to the home screen. They lose unsaved work.
>
> Repro is consistent on their tenant. Severity from their side: blocker for the Q3 rollout. Attached PDF has the customer's repro notes verbatim.
>

## Email B - NEW TASK (no existing task on the launch covers this)

**Subject:** `Q3 Widget Launch - mobile auth callback fails after SSO`

**Attachment:** `Q3-widget-mobile-auth-callback.pdf`

**Body:**

> Q3 Widget Launch issue from mobile beta cohort.
>
> Mobile users on the Q3 Widget Launch beta build cannot complete sign-in. After the IdP redirect the OAuth callback returns a 500 and the app drops the user back at the login screen. Reproduced on iOS and Android in the same build.
>
> No existing task on the launch covers this. Filed via this email so the morning sweep picks it up. Attached PDF has the device matrix and the exact callback URL that 500s.
>
