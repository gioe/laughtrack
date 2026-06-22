# TASK-3173 — Audit: Club geographic identity vs scraping-source venue

Date: 2026-06-22
Tool: `apps/scraper/bin/audit-club-source-geo` (`make audit-club-geo`)

## Motivation

During TASK-3152, club 461 "Red Room" was found labeled **New York, NY** while
its only scraping source (seatengine, `source_url` = `redroom.club`) is the
**Provincetown, MA** venue — so it had been ingesting P-town shows under an NYC
identity (and with no `comedy_filter`, drag/cabaret leaked in as comedy). Root
cause: a club's geographic identity (city/state/website) can drift from the
venue its scraping source actually points at, with no guard. This audit builds
a cheap, offline check that surfaces that drift so mislabeled / mis-wired clubs
can be corrected.

## What the audit checks (offline, no network)

Two deterministic signals over `scraping_sources` ⨝ `clubs`:

1. **`website_domain_mismatch`** — a *venue-specific* scraping source (i.e.
   `source_url` is the venue's own site, not a generic ticketing/aggregator
   host like ticketmaster.com / humanitix.com) whose registrable domain differs
   from the club's own `website` domain. This is the Red-Room-class detector:
   the source points at a different site than the club claims as its homepage.

2. **`shared_venue_across_geo`** — a venue-specific source domain, or a concrete
   per-platform venue id (`seatengine_id` / `eventbrite_id` / `ticketmaster_id`
   / `ovationtix_id` / `wix_event_id`), that maps to 2+ clubs whose
   `(city, state)` differ. Two clubs in different cities ingesting from the same
   venue is a strong mis-wire signal. Groups whose clubs all share one non-null
   `chain_id` are legitimate multi-city chains and are suppressed by default.

Generic ticketing platforms (ticketmaster, eventbrite, etix, …) and booking
SaaS (humanitix, prekindle, opendate, venuepilot, ticketsource, …) carry no
venue-specific geography, so sources on those hosts are excluded from signal 1
via a maintained denylist in the script.

## Run result (2026-06-22)

Audited 1,541 sources across visible clubs (1,584 with `--include-hidden`).
After denylisting platforms and suppressing chains:

- `website_domain_mismatch` = **6**
- `shared_venue_across_geo` = **4 groups**

**No confirmed geographic mismatches.** Red Room 461 no longer flags — its
identity was corrected to Provincetown, MA in TASK-3152, so its `website`
(`redroom.club`) now matches its source domain. Every residual row was reviewed
and is geographically consistent:

### `website_domain_mismatch` (6 — all benign)

| Club | City | Source domain | Website domain | Why it's fine |
|---|---|---|---|---|
| 74 The Comic Strip | El Paso, TX | laff2nite.com | elpasocomicstrip.com | "Laff 2nite" is the club's own ticketing brand; same venue |
| 486 Mic Drop Comedy | San Diego, CA | micdropcomedy.com | micdropcomedysandiego.com | Two of the venue's own domains; same venue |
| 638 Harrisburg Comedy Zone | New Cumberland, PA | harrisburgcomedyzone.com | boomeranggrill.com | Club operates inside Boomerang Grill; same location |
| 656 Stevie Ray's Improv | Chanhassen, MN | chanhassendt.com | stevierays.org | Performs at Chanhassen Dinner Theatres; same city |
| 9117 Kenosha Comedy Club | Kenosha, WI | happeningsmag.com | kenoshacomedyclub.com | Listings pulled from a local-magazine WP API; same city |
| 10975 Tupelo Music Hall | Derry, NH | tupelohall.com | tupelomusichall.com | `tickets.tupelohall.com` is the venue's ticketing subdomain |

These are the expected residual class once SaaS platforms are denylisted:
a venue that exposes more than one of its own domains (marketing site +
ticketing host), or a host-venue relationship. None are mislabels.

### `shared_venue_across_geo` (4 groups — all legit brands)

| Domain | Clubs | Note |
|---|---|---|
| citywinery.com | 7 (NYC, Boston, Atlanta, Philly, St. Louis, Pittsburgh, Chicago) | City Winery chain; geo correct per-city |
| govs.com | 3 (Bohemia, Bellmore, Levittown — all NY) | Governors' Comedy Clubs family (Long Island) |
| levitylive.com | 3 (West Nyack NY, Oxnard CA, Huntsville AL) | Levity Live (Improv-affiliated) chain |
| comedyworks.com | 2 (Denver, Greenwood Village — both CO) | Comedy Works Downtown + South |

These surfaced (rather than being chain-suppressed) only because their member
clubs lack a consistent `chain_id` — e.g. City Winery Pittsburgh (8720) has a
null `chain_id` while the other six carry `chain_id=16`; govs / levitylive /
comedyworks have no chain rows at all. The geography is correct in every case;
the gap is a **`chain_id` backfill** opportunity, not a geo mismatch. Not in
scope for this task and below the bar for a dedicated follow-up.

## Conclusion

- Criterion 1 (audit lists inconsistent clubs): satisfied by
  `bin/audit-club-source-geo` / `make audit-club-geo`.
- Criterion 2 (run once, correct/file follow-ups for confirmed mismatches):
  run completed; **zero confirmed mismatches** remain (Red Room 461 already
  fixed in TASK-3152). No corrections or follow-up tasks required.

The tool is left in place to re-run after future onboardings — the Red-Room
failure mode (a source re-pointed to a different venue, or a club mislabeled at
creation) will surface in signal 1 as a venue-specific-domain divergence, or in
signal 2 if the new source collides with an existing club's venue id/domain.
