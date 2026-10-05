# Zanies admission evidence — 2026-10-05

Verified using ZaniesScraper.fetch_html (the native scraper HTTP stack), with
worktree src on PYTHONPATH. No checkout or inventory mutation was performed.

## Retained audit

The 2026-09-27 audit zanies-1.html binds Tim Convy & Sean O’Brien to Etix
performance 75851627, September 27 at 7 PM Chicago (September 28 00:00 UTC).
The singleEventDetails container displays $37.95; its JSON-LD price is a
contradictory zero placeholder. This recovers one matched historical ticket:
show 7093331 / ticket 8075377. It is a fixed-snapshot lower bound, not a
current inventory claim. Retained homepage series headers such as $26 do
not establish an individual performance price and remain unresolved.

## Current source check

- https://chicago.zanies.com/show/felicia-folkes/zanies-comedy-club-chicago/chicago-illinois/
  — October 8, 2026, 7 PM Chicago; Etix 87195369; visible $37.95.
- https://chicago.zanies.com/show/kevin-sullivan-special-event-2/zanies-comedy-club-chicago/chicago-illinois/
  — October 11, 2026, 4 PM Chicago; Etix 98292254; visible $37.95.

Both were discovered from the current homepage, have a matching dated
single-performance container and Buy Tickets CTA, and still publish JSON-LD
price zero. Currency is USD by the US venue's dollar-denominated admission
context (the JSON-LD does not declare currency). Prices describe one admission,
with no package/table wording. Two-item minimum purchases are separate and
must not enter ticket price. Chicago does not specify the fee/tax breakdown;
Nashville's all-in statement must not be generalized to Chicago. Buy Tickets
is advertised availability, not a verified quantity of remaining seats.

Matched recovery is one retained ticket plus two current source examples;
these are not counts of repaired production rows. Series-wide prices,
ambiguous ranges/packages/currencies, missing price text, and mismatched
performance containers remain price-unknown. No production backfill is claimed.
