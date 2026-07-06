# TASK-3592 — ComedyTickets dedicated-club manual-research dispositions

Resolves the 24 `needs_manual_research` dedicated-club rows left open by
TASK-3588 (`task-3588-comedytickets-dedicated-onboarding.csv`). ComedyTickets is
used **only** as a discovery signal — it is never a scrape target. Every venue
was checked against its **own first-party website**, and a `scraping_sources`
row was enabled **only** when the mapped scraper was smoke-tested end-to-end
against that first-party source and returned real future shows.

## Method

1. Confirmed none of the 24 venues already had an enabled source in the DB.
2. Per venue: found the first-party site (web search), detected the ticketing
   platform / data feed (JSON-LD, ticketing-domain links, embedded widgets,
   platform APIs), and mapped it to an existing scraper key.
3. Smoke-tested each mapping with the **real scraper HTTP stack** — constructed
   an ad-hoc `Club` with the candidate `scraping_sources` config and ran the
   scraper's fetch+transform pipeline, counting future-dated shows. No DB writes.
4. Enabled a source only on a passing smoke test. Everything else is documented
   below with a concrete reason.

Smoke-test counts are as of **2026-07-06**.

## Summary

| Disposition | Count |
|---|---|
| onboarded (migration) | 9 clubs + 1 source correction (High Line) |
| duplicate of an onboarded row | 2 |
| deferred (platform verified, needs scraper work) | 6 |
| unresolved (no supported first-party source) | 6 |
| **total rows** | **24** |

## Onboarded (smoke-tested, enabled in migration `20260706173000`)

| Venue | Scraper | Future shows | Notes |
|---|---|---:|---|
| Loony Bin Comedy Club - Little Rock | standup_media | 119 | loc `46a4734a…` / `looneybin_prod` |
| Loony Bin Comedy Club - Tulsa | standup_media | 141 | loc `bca30415…` / `looneybin_prod` |
| Loony Bin Comedy Club - Wichita | standup_media | 105 | loc `bb17db1f…` / `Wichita_prod` |
| Dallas Comedy Club | json_ld | 535 | Prekindle org 531433527806655349 |
| Hyena's Comedy Nightclub Albuquerque | json_ld | 103 | Prekindle slug `hyenas-albuquerque` (hyphen) |
| Big Laugh Comedy Club (Fort Worth) | json_ld | 61 | SeatEngine whitelabel page emits ComedyEvent JSON-LD |
| Lafayette Comedy | json_ld | 3 | First-party JSON-LD; roving Acadiana producer |
| Howler Comedy Club | wix_events | 15 | Wix Events widget |
| Laughs Comedy Club (Seattle) | the_events_calendar | 37 | WP Tribe Events REST feed |
| High Line Comedy Club | eventbrite | 21 | **source correction** (see below) |

### High Line source correction

A parallel session created `High Line Comedy Club` (club id 16041) while this
task was in flight and enabled an eventbrite source with org **242807453**
(`source_url=https://www.eventbrite.com`), which returns **0 shows**. The
verified first-party organizer is **91898788783** (21 future shows). The
migration's trailing guarded `UPDATE` rewrites the broken value to the verified
organizer; it is a no-op once corrected.

## Deferred — platform verified, needs scraper work (follow-ups)

These have a confirmed first-party platform but the mapped scraper does not yet
extract them cleanly. Documented here rather than enabled, so no dead source
ships.

- **Ann Arbor Comedy Showcase** — etix venue 515 (official ticketing partner).
  Local smoke blocked by DataDome 403 (capsolver rejects the etix URL); the etix
  scraper is proven in production for Funny Bone venues, so this is an
  environment artifact. Enable + verify on the GHA nightly.
- **New York Comedy Club - Stamford** — dedicated NYCC subdomain
  (`stamford.newyorkcomedyclub.com`, ~38 future shows + JSON-LD). The
  `new_york_comedy_club` scraper returns 0 against the subdomain (NYC-only venue
  handling / address filter). Needs a scraper change to support the Stamford
  location (230 Tresser Blvd).
- **Olsen Run Comedy Club** — Shopify (`/collections/shows`, 46+ products). The
  `shopify` scraper extracts 0 (showtime encoded outside the fields it reads); no
  JSON-LD fallback. Needs shopify date-mapping work.
- **Soul Joel's Comedy Club** — WooCommerce Store API (moved to SunnyBrook
  Ballroom, Pottstown). The `woocommerce_store_api` scraper extracts 0
  showtimes (products lack structured dates). Needs woo date-extraction work.
- **Talk to the Moon Comedy Club** — Squarespace products collection. The
  `squarespace` scraper returns template/lorem-ipsum items and real shows encode
  the date in the title (`startDate` is null). Needs squarespace title-date
  parsing.
- **Greenwich Village Comedy Club** — Tessera ticketing (same SDK/response as the
  existing `broadway` Tessera instance). Needs a new Tessera instance file
  pointed at `tickets.greenwichvillagecomedyclub.com`.

## Unresolved — no supported first-party source

- **Claude's Comedy Club & Bar** (Philadelphia) — brand-new venue (opening at
  1123 S Broad); no dated shows / products / Event schema yet. Revisit after it
  opens.
- **Flop House Comedy Club** (Brooklyn) — Vue SPA on S3 with no static feed /
  JSON-LD; linked Eventbrite org empty. Needs live network inspection.
- **Quezada's Comedy Club & Catina** (Santa Ana Pueblo) — HoldMyTicket (no
  supported scraper); no JSON-LD / ICS. Would need a new HoldMyTicket scraper.
- **San Antonio Improv** — defunct; `improv.com/sanantonio` 404s and the old
  domain 301-redirects to `improvtx.com/sanantonio` = LOL San Antonio (the
  excluded venue, already onboarded as club 41). No live first-party page.
- **Sesh Comedy (Chrystie)** (New York) — hand-rolled PHP + client-side
  FullCalendar; tickets on Square Online (seshtix.com) + ShowClix/Leap. None map
  to a supported scraper.
- **Stir Crazy Comedy Club** (Glendale) — custom ASP.NET JS calendar with no
  static events / JSON-LD / ticket-domain links; only incidental third-party
  Eventbrite one-offs. Needs browser/network inspection.
