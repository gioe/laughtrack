# Affiliate Programs — Expansion Evaluation (TASK-2683)

Evaluation of candidate event-ticket affiliate programs beyond the first 10
priority programs, toward the 13–15 program target. Decision date: 2026-06-22.

## Outcome

**Final configured count: 10 (unchanged).** No candidate was onboarded in this
pass. This is below the 13–15 stretch target; the explicit exclusion reasons are
recorded per program below. Each candidate was scored on the four required
viability dimensions — **program availability**, **commission model**,
**deep-link support**, and **trust risk** — plus **comedy-inventory relevance**,
since LaughTrack is a comedy-show discovery platform whose outbound clicks should
favor the primary/venue ticketing source (see the project's venue-first value).

The existing 10 priority programs already default to **disabled** (each activates
only when its env var(s) are present — see `lib/affiliate/affiliateRouting.ts`
`affiliateRulesFromEnv()`), and any provider not in `PROVIDER_HOSTS` passes
through unrewritten. Because nothing was onboarded, no new configuration entries
were added; `lib/affiliate/eventProgramExpansion.test.ts` locks in that every
evaluated candidate stays absent from the priority set and never rewrites an
outbound URL.

## Candidate decisions

### TodayTix — DEFER
- **Availability:** Affiliate program exists (FlexOffers / CJ / Rakuten / ShareASale; ~30-day cookie).
- **Commission:** ~1–2% of sale.
- **Deep-link support:** Yes — per-show event URLs.
- **Trust risk:** Low — legitimate primary theater-ticketing platform.
- **Comedy relevance:** Low — Broadway / theater / opera / dance in a handful of cities; little comedy-club inventory.
- **Reason:** Legitimate and technically integrable, but the comedy-club inventory overlap is minimal, so the marginal commercial value does not justify onboarding now. Revisit if a meaningful share of LaughTrack shows resolve to TodayTix.

### Goldstar — DEFER
- **Availability:** Affiliate program exists (FlexOffers; signup at affiliates.goldstar.com; ~30-day cookie).
- **Commission:** ~1–2% of sale.
- **Deep-link support:** Yes — event pages; also a developer API.
- **Trust risk:** Low — established half-price live-entertainment aggregator; earning requires new-member registration (added conversion friction).
- **Comedy relevance:** Moderate — Goldstar lists some comedy shows/club discounts.
- **Reason:** Best comedy fit of the candidates, but its discount-membership model competes with sending users to the venue's own primary purchase, and registration friction depresses conversion. Defer; reconsider as a ride-along if comedy inventory match proves material.

### TicketSmarter — REJECT
- **Availability:** Affiliate program exists (FlexOffers / Sovrn; ~14-day cookie).
- **Commission:** ~3% of sale.
- **Deep-link support:** Yes.
- **Trust risk:** **High** — secondary-resale marketplace, BBB **not accredited**, with complaints citing undelivered tickets and refund difficulties.
- **Comedy relevance:** Secondary-market resale (marked-up third-party listings), not primary inventory.
- **Reason:** Sending discovery traffic to a marked-up resale marketplace with documented delivery/refund complaints conflicts with LaughTrack's venue-first value and poses reputational risk. Reject.

### Ticket Squeeze — REJECT
- **Availability:** Affiliate program exists (in-house).
- **Commission:** ~10% of sale (highest of the set).
- **Deep-link support:** Yes (API), but attribution is Google-Analytics-driven rather than the cookie/redirect model the current `AffiliateRule` engine (`query` / `redirect`) implements — a technical mismatch.
- **Trust risk:** Moderate — secondary-resale marketplace; mixed public reviews.
- **Comedy relevance:** Secondary-market resale.
- **Reason:** Despite the high headline rate, it is a resale marketplace (markup + venue-first conflict) and its GA-based tracking does not fit the existing affiliate-rule architecture. Reject.

### SI Tickets (Sports Illustrated Tickets) — REJECT
- **Availability:** Affiliate program exists (in-house; "no fees at checkout" positioning).
- **Commission:** Not clearly published.
- **Deep-link support:** Unclear.
- **Trust risk:** **High** — secondary-resale marketplace, BBB **not accredited**, with complaints citing website/ticket errors and customer-service disputes.
- **Comedy relevance:** Secondary-market resale, sports-led inventory; weak comedy match.
- **Reason:** Trust risk plus weak comedy relevance; same venue-first conflict as the other resellers. Reject.

### AXS — DEFER (previously decided, TASK-2706)
- See `apps/web/docs/affiliate-axs-decision.md`. Viable on the Impact network
  (already integrated for Ticketmaster/SeatGeek) but future inventory is
  negligible (~0.025%). Ride along once a real threshold is hit (~250 future AXS
  tickets). No change in this pass.

## Why the count stayed at 10

Of the candidates, the two legitimate primary/aggregator programs (TodayTix,
Goldstar) have only low/moderate comedy-club inventory overlap, and the three
secondary-resale marketplaces (TicketSmarter, Ticket Squeeze, SI Tickets) carry
markup and consumer-trust risk that conflict with LaughTrack's preference for
routing buyers to the venue/primary source. None cleared the bar for onboarding
now, so the program count remains 10 with the deferrals/rejections documented
above for re-evaluation when inventory or commercial terms change.
