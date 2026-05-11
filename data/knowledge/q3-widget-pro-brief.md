# Q3 Widget Pro — Product Launch Brief

**Category:** Spec  
**Launch:** Q3 Widget Pro  
**Owner:** Sample Product Team  
**Last reviewed:** 2026-04-20

> Note: this is a fictional product used for the Launch Control demo series.
> Any resemblance to real Widgets is coincidental.

## 1. Product summary

Q3 Widget Pro is the next iteration of the company's flagship Widget. It
focuses on three themes: faster setup, richer telemetry, and a redesigned
admin surface. The agent uses this brief whenever a stakeholder asks "what
is launching" or "what does this launch include".

## 2. Personas

* **Admin Alex** — configures and maintains the Widget across an
  organization. Cares about uptime and observability.
* **Operator Olivia** — uses the Widget day-to-day to run team rituals.
  Cares about ergonomics and integrations.
* **Director Dana** — sponsors the rollout. Cares about adoption and ROI.

## 3. In scope

* Setup wizard with a five-step guided experience.
* Telemetry dashboards with daily, weekly, and monthly aggregates.
* New admin surface with role-based access control.
* Power Platform connector for downstream automation.
* Documentation refresh in `learn.contoso.com/widgets`.

## 4. Out of scope

* Mobile app — deferred to Q4.
* On-premises deployment — not in roadmap.
* Localization beyond en-US, fr-FR, ja-JP, de-DE — handled in a follow-up.

## 5. Readiness gates and owners

| Gate              | Owner             | Status target by GA |
|-------------------|-------------------|---------------------|
| Engineering       | Eng lead          | Green               |
| Marketing         | Marketing manager | Green               |
| Sales enablement  | Field readiness   | Green               |
| Support           | Support manager   | Green               |
| Compliance        | Compliance officer| Green               |
| Legal             | Legal counsel     | Green               |

## 6. Risks and mitigations

* **Risk:** Setup wizard depends on a backend service that is still in
  preview.
  **Mitigation:** Feature-flag the new flow; fall back to classic setup.
* **Risk:** Telemetry dashboards require a schema change in the analytics
  store.
  **Mitigation:** Schema migration runs two weeks ahead of GA, validated by
  the analytics team.
* **Risk:** Connector certification can slip due to review backlog.
  **Mitigation:** Submit two weeks earlier than the previous launch; add a
  buffer milestone.

## 7. Communications plan

* Internal kickoff at T-8 weeks.
* Customer preview at T-4 weeks (limited audience).
* GA announcement at T-0, with blog, social, and field briefing.
* Post-launch retrospective at T+3 weeks.
