# Deferred storyline: Full Orchestra + Your Turn

> This storyline is preserved for a future episode or finale. It is not the active Episode 16 preview. See [README.md](README.md) for the current Business Apps in Work IQ and external agents direction.

## The idea

Close the series by bringing previously demonstrated Launch Control capabilities together around one launch record, then invite viewers to try a safe, documented setup themselves.

The planned finale has two parts:

1. **Full Orchestra:** a short montage of verified surfaces using the same launch record. Each beat must be revalidated against the current product, data, access, and recording environment before it is shown.
2. **Your Turn:** a guided path for viewers to prepare their own environment and create a starter launch, only after the repository setup and public-release instructions are reviewed and safe to publish.

The earlier draft also proposed a new-launch teaser between the two parts. Keep it optional until the flow and its effects have been rehearsed in an approved demo environment.

## Assets retained in this folder

| Asset | Deferred purpose |
|---|---|
| `preflight.py` | Pre-record checks for the earlier orchestra concept. It is not a Work IQ or external-agent compatibility check. |
| `orchestra/setup_launch_week.py` | Prepares the earlier launch record for a montage. Its `--apply` path writes to the configured Dataverse environment. |
| `orchestra/teardown_launch_week.py` | Restores the earlier rehearsal state. Its `--apply` path writes to and deletes rows in the configured Dataverse environment. |
| `orchestra/spin_up_launch.py` | Creates a launch and related starter rows when run with `--apply`. It is not an external-agent connector. |
| `orchestra/_common.py` | Shared Dataverse client and status values for those scripts. |

The scripts default to dry-run, but still depend on local configuration and can read the configured environment. Do not run them as evidence for the active Episode 16 preview. Review their current behavior, target environment, and dry-run output before any future rehearsal; use `--apply` only with explicit operator approval in the intended demo environment.

## Revival gates

- Reconfirm which earlier episode surfaces still exist and work as described. Do not rely on draft claims, old timings, counts, or preflight results.
- Rehearse the montage with approved sample data and a verified source of truth for each displayed result.
- Review every setup, teardown, and creation action for current side effects and approvals.
- Confirm viewer setup instructions use placeholders, protect credentials, and accurately describe prerequisites and cost or licensing implications.
- Complete a current repository, privacy, and public-release review before promising a public release or a viewer-ready clone flow.

The Full Orchestra concept is intentionally retained as a deferred storyline, not as a validated recording plan.
