# AXS affiliate program — evaluation & decision (TASK-2706)

**Date:** 2026-06-20
**Decision:** **Defer** until AXS inventory grows. Do not sign up now.
**Parent:** TASK-2683 (evaluate/onboard remaining event affiliate programs beyond the first 10).

## Is there a viable affiliate path? — Yes

AXS runs a ticket affiliate program **on the Impact network**
(`impact.com`). This is the **same network LaughTrack already uses for
Ticketmaster** (`PRIORITY_PROGRAMS[ticketmaster].networkName = "Impact"`,
env `TICKETMASTER_AFFILIATE_CAMEFROM`) and SeatGeek. So the network plumbing
and account relationship already exist; onboarding AXS later is a low-effort
add, not a net-new integration.

Sources:
- AXS affiliate program listing on Impact (e.g. discoverable via Impact's
  marketplace; per-event promo pages exist under
  `axs.com/events/<id>/<slug>/promos/<promo_id>`).
- AXS is an AEG Worldwide ticketing division.

## Why defer — inventory is negligible

Future ticket inventory by provider (queried 2026-06-20, `tickets` joined to
`shows` where `date >= now()`):

| Provider            | Future tickets | Share   |
|---------------------|---------------:|--------:|
| other / direct      | 30,685         | ~64.6%  |
| Ticketmaster family | 12,736         | ~26.8%  |
| Eventbrite          | 2,752          | ~5.8%   |
| Tixr                | 1,358          | ~2.9%   |
| **AXS**             | **12**         | **~0.025%** |

All 12 AXS shows point at `www.axs.com`. At 12 tickets, AXS is a rounding
error — the expected affiliate revenue does not justify the signup +
per-event tracking + routing-rule + env-var work, even though that work is
small. (At filing on 2026-06-06 there was only 1 AXS show; it has grown to 12
but is still far below any meaningful tier.)

## Trigger to revisit

Revisit AXS onboarding when **either**:

1. AXS future-ticket inventory crosses a meaningful threshold — suggest
   **≥250 future tickets** (roughly the Tixr tier / ~0.5% share), OR
2. TASK-2683 batch-onboards the remaining programs. Because AXS is already on
   Impact, it can ride along with that effort at marginal cost — add it to the
   batch rather than tracking it separately.

## What onboarding would require (captured for when we do pursue it)

Mirror the existing Impact/Ticketmaster wiring in
`apps/web/lib/affiliate/affiliateRouting.ts`:

1. Add `"axs"` to `AffiliateProvider` (and `PriorityAffiliateProvider` /
   `PRIORITY_AFFILIATE_PROVIDERS` if promoting it to a priority program).
2. Add an AXS entry to `PRIORITY_PROGRAMS` with
   `networkName: "Impact"`, an env var (e.g. `AXS_AFFILIATE_CAMEFROM` or an
   Impact redirect-base URL, matching whatever Impact issues for AXS), and
   `launchStatus: "requires_account_approval"`.
3. Add the host mapping (`hosts: ["axs.com"]`) and an `AffiliateRule`
   (query-param or redirect, per the Impact-issued link format).
4. Set the Impact-issued tracking value in the Vercel env (prod) — payout/
   account is the existing LaughTrack Impact account, so no new payout setup
   is needed beyond enabling the AXS campaign within Impact.

No code shipped for the onboarding itself — that is intentionally deferred.
