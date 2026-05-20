# Soft-Launch Rollout Plan

How LaughTrack moves from private validation to a public launch without turning the first broad announcement into the first production test.

## Decision roles

- **Launch owner:** Matt Gioe.
- **Go/no-go owner for every gate:** Matt Gioe.
- **Backup if Matt is unavailable:** hold the current cohort; do not advance automatically.

The go/no-go owner reviews the metrics at the end of each cohort window and records the decision in the task or launch notes before inviting the next cohort.

## Rollout stages

| Stage | Cohort | Duration | Exit gate |
|-------|--------|----------|-----------|
| 0 | Internal smoke users | 2 business days | Core flows work end-to-end with no unresolved launch-blocking issues. |
| 1 | 10 friendly users | 3 business days | Early-user feedback produces no critical usability blockers and reliability stays within gate. |
| 2 | 100 invited beta users | 7 calendar days | Usage, conversion, and support load show the app can absorb public traffic. |
| 3 | Public launch | Ongoing | Monitor launch metrics daily for the first week, then fold into normal operations. |

Do not advance a stage just because the calendar window elapsed. The duration is the minimum observation period; the go/no-go owner may hold a cohort longer when metrics are inconclusive.

## Gating metrics

Evaluate each gate over the cohort window unless noted otherwise.

| Metric | Stage 0 gate | Stage 1 gate | Stage 2 gate | Public launch watch |
|--------|--------------|--------------|--------------|---------------------|
| Sentry error rate | No unresolved crash or server error in core flows. | Less than 1% affected sessions and no repeated crash signature. | Less than 0.5% affected sessions and no P0/P1 issue open. | Investigate any spike above 0.5% affected sessions. |
| p95 app/API latency | Key browse and detail views under 1.5s p95 in normal regions. | Public search and detail API p95 under 1.5s. | Public search and detail API p95 under 1.2s. | Page if p95 stays above 2.0s for 30 minutes. |
| Uptime | No known outage during smoke window. | 99.5% or better during the cohort window. | 99.9% or better during the cohort window. | 99.9% weekly target. |
| Sign-up to favorite conversion | Manual check that a new account can favorite at least one comedian or show. | At least 30% of invited users who sign up favorite a comedian or show. | At least 20% of signed-up beta users favorite a comedian or show. | Track weekly; investigate if below 15%. |
| Support load | No unresolved internal blocker. | No more than 2 unresolved support issues from the cohort. | No more than 5 unresolved non-critical support issues, and no unresolved critical support issue. | Triage according to `docs/support.md`. |

## Abort criteria

Abort means stop new invitations or public promotion, keep the current cohort stable when possible, and fix forward or roll back depending on severity.

- A security, data-loss, payment, authentication, or privacy issue is confirmed.
- Sentry shows a repeated crash or server error affecting core browse, search, detail, sign-up, or favorite flows.
- p95 latency exceeds 2.0s for core public routes for 30 minutes without an active mitigation.
- Uptime drops below 99% during a pre-public cohort window.
- More than 10% of invited users report they cannot complete sign-up or favorite a comedian/show.
- The support inbox contains an unresolved critical issue from the current cohort.

When an abort criterion triggers, Matt records the reason, pauses advancement, files or updates the relevant tusk task, and announces the hold in the launch notes. Re-entry requires the same gate to pass for a fresh 24-hour observation window.

## Stage checklist

### Stage 0: internal smoke users

- Invite: Matt and any internal testers already familiar with the app.
- Minimum duration: 2 business days.
- Focus: sign-up, browse/search, show detail pages, comedian favorites, support email path, and production monitoring.
- Advance when: every Stage 0 gate passes and no launch-blocking task remains open.
- Go/no-go owner: Matt Gioe.

### Stage 1: 10 friendly users

- Invite: 10 users who are comfortable giving direct feedback and retrying after fixes.
- Minimum duration: 3 business days.
- Focus: onboarding clarity, local show discovery, favorite behavior, and obvious content gaps.
- Advance when: every Stage 1 gate passes and feedback does not identify a blocking usability issue.
- Go/no-go owner: Matt Gioe.

### Stage 2: 100 invited beta users

- Invite: up to 100 users across target launch cities.
- Minimum duration: 7 calendar days.
- Focus: reliability under broader geography, scraper/content quality, conversion to favorites, and support volume.
- Advance when: every Stage 2 gate passes, all critical support issues are closed, and remaining launch risks have owners.
- Go/no-go owner: Matt Gioe.

### Stage 3: public launch

- Invite: public announcement, app store promotion, and broader sharing.
- Minimum duration: continuous monitoring for the first 7 days.
- Focus: daily review of Sentry, p95 latency, uptime, conversion, support inbox, and scraper health.
- Continue when: launch watch metrics remain within bounds or active mitigations are in place.
- Go/no-go owner: Matt Gioe.
