# Comedy-venue scraper triage — ZIP 44622 (100 mi)

Triage pass for **TASK-2863**. Produced by `make discover-nearby ZIP=44622 RADIUS=100 NEW_ONLY=1`
(Google Places), then website/booking-link probing + comedy confirmation. The point of this
sheet is to make per-venue onboarding fast: it records each candidate's ticketing/calendar
platform, the matching `scraper_key` (or a "not scrapable / net-new" flag), and whether the
venue actually hosts comedy — so the operator can skip the dead ends and go straight to the
ready wins.

Generated 2026-06-16. Re-run the recipe in "Method" for any other ZIP.

## Summary

- **175** net-new candidates returned by discovery (not already in `clubs`).
- Filtered to **17** high-signal *probable-comedy* candidates = Google `primary_type='comedy_club'`
  **OR** a comedy-ish name (comedy/comic/improv/laugh/standup/funny/wisecrack/slapstik/…).
  The other ~158 (generic `performing_arts_theater`/`bar`/`event_venue`/etc. with no comedy
  signal) were **not individually probed** in this pass — they are lower-signal and most host
  comedy only incidentally; probe them on demand if a specific lead arises.
- Of the 17: **2 map to existing scrapers**, 1 is likely already covered by an onboarded host
  venue, and **the remaining 14 are dead ends** (Google misclassifications, not-comedy,
  social-/door-only, or roving acts).

> **Update (TASK-2940):** The Cellar @ Pittsburgh Winery was onboarded (club 8730, etix venue
> 31604) but is a **mixed music+comedy venue** (~5 comedy of ~22 events) — the `etix` scraper has
> no genre filter, so the full music calendar comes in too and is pruned manually (operator
> decision). It is *not* the "clean win" this sheet first implied; comedy at a Pittsburgh winery
> is already covered comedy-filtered by **City Winery Pittsburgh** (club 8720, a different chain
> venue, `genre=Comedy`). See convention #195 (mixed-venue onboarding needs a platform genre
> filter). Local verify was 0 shows (etix DataDome block); N>0 pending the GHA nightly.

### Recommended next actions (file these as onboarding tasks)

| Venue | City | Platform | `scraper_key` | Why it's ready |
|---|---|---|---|---|
| **The Cellar @ The Original Pittsburgh Winery** | Pittsburgh, PA | Etix | **`etix`** (exists) | ONBOARDED (TASK-2940, club 8730) with a caveat — mixed music+comedy, no genre filter, music pruned manually. NOT a clean win. |
| **Something Dada Improv Comedy Co.** | Cleveland, OH | TicketLeap (`somethingdada.ticketleap.com/dada`) | **`ticketleap`** (exists) | Long-running improv troupe; tickets via a TicketLeap subdomain. |

Neither is currently in `clubs` or has a dedicated onboarding task (dupe-checked 2026-06-16).

## Full triage table

| Venue | Dist | Comedy? | Website | Platform | Candidate `scraper_key` | Disposition | Conf. |
|---|---|---|---|---|---|---|---|
| The Cellar @ Pittsburgh Winery | 79.0mi | yes (mixed) | pittsburghwinery.com | Etix (venue 31604) | `etix` | **ONBOARDED w/ caveat** (TASK-2940, club 8730) — mixed music+comedy, music pruned manually; no genre filter | high |
| Something Dada Improv Comedy Co. | 68.0mi | yes | somethingdada.ticketleap.com/dada | TicketLeap | `ticketleap` | **ONBOARD** — ready | high |
| Columbus Improv Wars | 89.9mi | yes | improvwarscolumbus.com (down) | host theaters | — | Likely covered — ticketed via MadLab (club 8725) + The Nest (8713), both already onboarded | med |
| PNR Improv (Point of No Return) | 38.3mi | yes | pnrimprov.org | none — $5 cash at door | not scrapable | Skip — door-only cash; performs at Newell Theatre / Quirk Cultural Center | high |
| Funny Bus Cleveland | 67.7mi | n/a | funnybus.net/cleveland | Resmark (proprietary) | not scrapable | Skip — roving comedy BUS TOUR, not a fixed venue | high |
| Green Light Improv | 90.9mi | no | greenlightimprov.com → nathanminns.com | n/a | not a comedy venue | Skip — rebranded to corporate improv training/keynotes, no public shows | high |
| Cleveland Heights Civic Center | 68.0mi | no | bookthecivic.com | n/a | not a comedy venue | Skip — banquet/conference rental; Places misclassification | high |
| Funny Side Up | 18.3mi | no | funnysideupohio.com | n/a | not a comedy venue | Skip — breakfast restaurant | high |
| Wisecracks Comedy Escape Room | 33.1mi | no | wisecracksescaperoom.com (Wix) | n/a | not a comedy venue | Skip — escape room, not a comedy venue | high |
| La Boom Columbus | 95.1mi | no | zamoralive.com (WordPress) | n/a | not a comedy venue | Skip — Latin nightclub | med |
| SlapStik Comedy Entertainment | 83.1mi | unsure | comedyslaps.com | routes via CAPA presenter | not scrapable (no own room) | Skip — comedy-media company using partner theaters; no self-serve listing | med |
| Tidos Corner | 89.9mi | unsure | tidoscorner.com | none detected | unsure | Skip for now — bar; no comedy text or ticketing on site | low |
| Okies dokies | 35.3mi | no | none | n/a | not a comedy venue | Skip — no such venue; Places misclassification (lowercase name, no site) | high |
| westworld | 57.7mi | no | none | n/a | not a comedy venue | Skip — no venue by this name; misclassification | high |
| BH&M | 83.5mi | no | none | n/a | not a comedy venue | Skip — no comedy venue "BH&M" in Columbus; misclassification | med |
| Lyra quin | 86.2mi | no | none | n/a | not a comedy venue | Skip — almost certainly a person's name, not a venue | high |

(The two Something Dada rows from discovery — Cleveland + Lakewood — are the same troupe; listed once.)

## Method (re-run for any ZIP)

1. `cd apps/scraper && make discover-nearby ZIP=<zip> RADIUS=<mi> NEW_ONLY=1 FORMAT=json LIMIT=300`
   → net-new candidates not already in `clubs`.
2. Filter to **probable-comedy**: `primary_type == 'comedy_club'` OR name matches
   `comedy|comic|improv|laugh|standup|stand-up|funny|jest|punchline|wisecrack|slapstik|dada`.
3. For each, fetch the website and grep for ticketing/embed-domain signatures
   (eventbrite, tixr, seatengine, ovationtix, squarespace, wix, ticketweb, etix, dice.fm,
   prekindle, humanitix, simpletix, thundertix, ticketleap, tockify, squareup/square.site,
   opendate, bandsintown, showclix, see-tickets, venuepilot, crowdwork) or generic JSON-LD
   `"@type":"Event"`. For no-website / JS-hydrated venues, web-search the venue + inspect the
   live calendar (Playwright) before concluding.
4. Map the detected platform to an existing `scraper_key`
   (`grep -rhoE "key = ['\"][a-z0-9_]+['\"]" src/laughtrack/scrapers/implementations/ | sort -u`),
   else flag **needs net-new** or **not scrapable** (door-only / social-only / dead site /
   roving act / not a comedy venue).
5. **Confirm comedy from the venue's own calendar** — do not trust the Google `comedy_club`
   type or an aggregator listing. Lowercase one-word names with no website are usually Places
   misclassifications.

## Caveats / honest scope

- Only the 17 high-signal candidates were probed; the ~158 lower-signal net-new candidates
  (theaters, bars, event venues without a comedy signal) were not. They may host occasional
  comedy — probe individually if a lead surfaces.
- `improvwarscolumbus.com` and `pnrimprov.org` were unreachable at probe time; their
  dispositions rely on web research, not a live calendar fetch — re-verify before onboarding.
