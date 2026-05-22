# TASK-2405 — Ticket.price null-default audit & plan

## Goal

Shift the codebase convention so `Ticket.price = None` is the default for *unknown* price, and `Ticket.price = 0` is reserved for explicitly-proven free events (RSVP-only, JSON-LD `Offer { price: 0 }`, vendor "free" flags, etc.).

Triggered by the TASK-2389 audit: 19/19 future tickets for club 655 (House of Comedy Bloomington) showed `price=0.00`, none of which are actually free — the scraper hardcoded zero for every event.

## Audit summary

### Schema / type layer — already nullable, no change required

- `apps/web/prisma/schema.prisma:649` — `Ticket.price Decimal? @db.Decimal(7, 2)` ✓
- `apps/web/objects/class/ticket/ticket.interface.ts:3,11` — both `TicketInterface.price` and `TicketDTO.price` are `number | null` ✓
- `apps/scraper/src/laughtrack/core/entities/ticket/model.py:18` — `price: Optional[float]` ✓
- `apps/web/prisma/migrations/20260512010000_add_show_min_price_with_trigger` — the `shows.min_price` trigger already filters `WHERE price IS NOT NULL AND price > 0`, so it treats 0 and NULL identically (both excluded from the cheapest-paid summary). No trigger change required.

### UI render branches — already distinguish 0 from null, no change required

Both clients filter null prices and render "Free" for explicit zero:

- `apps/web/util/ticket/ticketUtil.ts:31-55` (`formatTicketString`) — `.filter((price): price is number => price != null)`, then "Free" when min === 0, "$N" otherwise. Tests at `apps/web/util/ticket/ticketUtil.test.ts:21-33` already assert that null prices do NOT render as "Free".
- `apps/web/ui/components/cards/show/header/index.tsx:90-95`, `apps/web/ui/components/cards/show/compact/index.tsx:23,31-34`, `apps/web/ui/pages/entity/show/ticketCta/index.tsx:25,71-75` — all delegate to `formatTicketString`.
- `apps/web/util/jsonLd.ts:220-224` — `price != null && price > 0` gate; both 0 and null are omitted from schema.org Offer output. No distinction needed at the SEO layer.
- `ios/Sources/LaughTrackApp/Components/ShowPricePresentation.swift:13-54` — null → "Unavailable" (detail) or nil (list rows); 0 → "Free". Already correct.

**Conclusion:** the UI is ready for the new semantics. The fix is entirely on the scraper side.

### Scraper / Python writer call sites

Bug classes:

1. **Hardcoded `price=0` placeholder** when the API/HTML did not surface a price.
2. **Falsy-coercing patterns** that conflate `None` and `0`: `price=offer.price or 0`, `price=tier.get("price", 0)`, `(value or 0) / 100`.
3. **Shared `create_fallback_ticket(price=0.0, ...)` default** propagated through ~30 event entity classes.

Sites grouped by remediation:

| Layer | File:line | Pattern | Action |
|---|---|---|---|
| Central helper | `apps/scraper/src/laughtrack/utilities/domain/show/factory.py:212` | `def create_fallback_ticket(..., price: float = 0.0, ...)` — used by ~35 event entities | Change default to `price: Optional[float] = None` |
| Central helper | `apps/scraper/src/laughtrack/core/entities/ticket/model.py:66` (`Ticket.from_offer`) | `price=float(offer.price) if offer.price else 0.0` — converts `None` *and* explicit `0` from JSON-LD into 0.0 | `if offer.price is not None else None` (preserves explicit 0 as proven-free) |
| Generic JSON-LD `to_show` | `apps/scraper/src/laughtrack/core/entities/event/event.py:99` | `Ticket(price=0.0, ...)` placeholder when `not tickets and not self.offers` | `price=None` |
| Tixr client | `apps/scraper/src/laughtrack/core/clients/tixr/client.py:651-653` | `try: float(offer.get("price", 0)); except: price = 0.0` | Use `None` on missing/unparseable |
| Tixr client | `tixr/client.py:669` | "No offers found in JSON-LD" placeholder ticket with `price=0` | `price=None` |
| Tixr client | `tixr/client.py:873` (`_extract_ticket_info`) | `price=price or 0` — converts `None`/missing tier price to 0 | `price=price` (already `None`-or-float by line 866-870) |
| Tixr client | `tixr/client.py:885` (`_extract_ticket_info`) | `price=0  # Price not available` fallback when `not tickets` and `hasTickets` truthy | `price=None` |
| HOC Bloomington (Tixr listing scraper) | `apps/scraper/src/laughtrack/scrapers/implementations/venues/house_of_comedy_bloomington/scraper.py:138` | `Ticket(price=0, ...)` for *every* event on the listing page | `price=None` (downstream Tixr detail fetch fills it in; see TASK-2403) |
| SeatEngine v1 client | `apps/scraper/src/laughtrack/core/clients/seatengine/client.py:227` | `(inventory.get("price") or 0) / 100` — None becomes 0 cents | `raw / 100 if raw is not None else None` |
| SeatEngine v3 transformer | `apps/scraper/src/laughtrack/scrapers/implementations/api/seatengine_v3/transformer.py:87` | `inventories=[]` → synthesize `Ticket(price=0.0, ...)`. Comment explicitly calls out "free / RSVP-only events". | **KEEP as 0** — proven free by API contract |
| HaHa Comedy Club | `apps/scraper/src/laughtrack/scrapers/implementations/venues/haha_comedy_club/scraper.py:238-240` | `price = float(price_raw) if price_raw else 0.0; except: price = 0.0` | None when missing/unparseable, preserve string "0" as 0 if seen |
| Rodneys | `apps/scraper/src/laughtrack/scrapers/implementations/venues/rodneys/transformer.py:155-164` | "No price in HTML" fallback `Ticket(price=0.0, ...)` | `price=None` |
| Standup NY | `apps/scraper/src/laughtrack/scrapers/implementations/venues/standup_ny/transformer.py:158-168` | Inline comment already reads "Price unknown from GraphQL API" but emits 0 | `price=None` |
| Empire Comedy Club | `apps/scraper/src/laughtrack/scrapers/implementations/venues/empire_comedy_club/transformer.py:32` | `Ticket(price=0.0, ...)` with no extraction attempt | `price=None` |
| Comedy Works (downtown) | `apps/scraper/src/laughtrack/scrapers/implementations/venues/comedy_works_common/extractor.py:155` flowing into `apps/scraper/src/laughtrack/core/entities/event/comedy_works_downtown.py:81` | Tier dict's `price` defaults to 0.0 when no `<span.product-price>` is parsed | Change extractor default to `None`; relax `tier.get("price", 0.0)` to `tier.get("price")` |
| Ninkashi | `apps/scraper/src/laughtrack/core/entities/event/ninkashi.py:64,66,121` | `from_dict` returns `0.0` when API price is None; `to_show` does `t.price or 0.0` | Preserve `None` through both `from_dict` and `to_show` |
| Generic enricher wrapper | `apps/scraper/src/laughtrack/scrapers/utils/ticket_enrichment.py:26` | `Ticket(price=0.0, ...)` fallback when wrapper underlying isn't a Ticket | `price=None` |
| Eventbrite | `apps/scraper/src/laughtrack/core/entities/event/eventbrite.py:257` | Already correct: `price = 0.0 if self.is_free is True else None` | No change |

## Backfill plan for existing `price=0` rows

**Decision: option (b) — accept historical ambiguity, only enforce the new semantic going forward.**

Rationale:
- Once a row exists at `price=0`, it cannot be distinguished between "scraper proved free" and "scraper failed to extract" without re-scraping the event. The historical scraper code path is not preserved per row.
- Every show is re-scraped on a roughly-nightly cadence (`tasks/scraper` GHA), so future-dated rows from venues whose scrapers we've updated will have correct `price=None` within ~24 hours of merge.
- Past-dated rows do not surface in the user-facing UI (search defaults to upcoming-only), so a stale `price=0` on a past show has no rendering impact.
- A blanket `UPDATE tickets SET price=NULL WHERE price = 0` would clobber genuinely-free tickets from SeatEngine v3, Eventbrite `is_free=true`, and Ninkashi vendor-tagged free events — irreversible without per-source provenance, which we do not track.

**Verification that the going-forward fix is sufficient:**
- The denormalized `shows.min_price` trigger already excludes price=0 OR NULL — so search ranking and `ORDER BY min_price` already behave identically for both, both today and after the refactor.
- The UI rendering paths already treat null as "hide" and 0 as "Free", so the day-after-merge difference for affected scrapers (e.g. HOC Bloomington) is: cards stop showing a spurious "Free" badge and start showing no price label, which is the correct outcome.

**Caveat for future work (out of scope for this task):**
- If a future product surface needs to distinguish proven-free from unknown, scrapers should set a per-ticket provenance flag (e.g. `price_source: 'api' | 'rsvp' | 'unset'`) rather than relying on the 0-vs-NULL split. Not blocking; file a follow-up task only if/when a UI use case appears.

## Test plan (criterion 5)

Add unit-test assertions in `apps/scraper/tests/`:

1. **HOC Bloomington** — synthesize a minimal HTML fixture for the Tixr listing card, parse via the venue scraper, assert the resulting `Ticket.price is None` (not `0`).
2. **TixrClient `_extract_ticket_info`** — feed event data with (a) a tier where `price` is missing → `Ticket.price is None`; (b) a tier where `price` is unparseable → `Ticket.price is None`; (c) the `hasTickets=True, no sales` fallback path → `Ticket.price is None`.

Tests should NOT exhaustively cover every venue refactored above; the central `create_fallback_ticket` change is covered transitively whenever its callers are exercised in their existing test files.

## Out of scope

- TASK-2403 (Wire Tixr price extraction for HOC Bloomington) — this task makes HOC Bloomington emit `None` so the *fallback* is honest. TASK-2403 will then plug in the real per-event detail fetch.
- A `price_source` provenance column.
- Backfilling historical rows.
