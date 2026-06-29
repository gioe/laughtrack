# TASK-3511 — Re-triage of the dry-source unchained venues

**Date:** 2026-06-29
**Scope:** 54 unchained clubs (`chain_id IS NULL`) that have an **enabled** `scraping_sources`
row but **0 rows in `shows`**. (The task title says ~55; club 3971 `12605 NW 17th Ave`
was already retired under criterion 11550 in a prior session, leaving 54.)

**Owner's rule applied throughout:** real venues with real addresses are **KEPT**.
This is coverage recovery, not deletion. Each venue is dispositioned as one of:
**(a) fix config to light it up**, **(b) confirm dormant-but-real and leave**, or
**(c) retire** (only when confirmed not a real comedy venue).

## How each venue was triaged

For every venue the production run history (`scraper_run_clubs`) was joined to its
source config, then each was live-probed locally (`scrape_shows --club-id <id>`,
idempotent — identical to the nightly). The decisive signals were
`items_before_filter`, `http_status`, `bot_block_detected`, and the
`organizer feed produced N show(s) across M venue(s)` log line.

## Headline result

Coverage was **not** silently lost anywhere. The two large clusters are healthy:

- **Eventbrite (28): organizer feeds, dry by design.** Every dry eventbrite club's
  `source_url` is an organizer feed (`eventbrite.com/o/<id>`). In organizer mode the
  scraper routes each event to its **own per-venue club** (resolved from the event's
  Eventbrite venue), so the organizer club itself is legitimately 0-show — its shows
  live on the venue clubs. Verified live:
  - **Gold Coast Comedy Club (11449)** → 60 shows across **Bokampers Sports Bar &
    Grill (11450)** and **Ovivi's Restaurant (11451)** (`60 updates` — already persisted).
  - **BATS Improv (11133)** → 34 shows across **BATS Bayfront Theatre (11135)** and
    **BATS Improv Theatre (11134)**.
- **Etix (9): scraper healthy; the dry ones are DataDome-walled or empty.** The etix
  scraper produces hundreds of shows for the Funny Bone venues (Orlando 314, Columbus
  255, Tampa 251, …), so it is not broken. The 7 dry etix theatres use **direct
  `etix.com/ticket/v/<venue_id>` URLs that are DataDome-walled** (HTTP 403; capsolver
  rejects the solve with `blocked captcha url is not supported`) — this is the
  TASK-2858 problem, not a per-venue bug.

**One real coverage recovery:** **Liberty Funny Bone (11431)** had **never run**
(0 `scraper_run_clubs` rows) and was dry. Its source is the non-walled
`liberty.funnybone.com/shows/` subdomain (same pattern as Albany/Columbus/Orlando
Funny Bones). A live run **lit it up with 113 shows**, now persisted.

---

## Cluster 1 — Eventbrite (28) — criterion 11547

**Disposition: all 28 left as-is.** No stale/wrong `eventbrite_id` was found — every
organizer feed resolves (HTTP 200). These are organizer feeds whose coverage is
attributed to per-venue clubs (see headline). Sub-split by current feed activity:

### 1a. Active organizer feeds (17) — producing shows routed to venue clubs → **leave**
Last nightly run reported shows (`num_shows` in parens); those shows persist on the
event venue clubs, not the organizer club.

| club_id | organizer | last feed shows |
|--------:|-----------|----------------:|
| 11081 | The Spotlight Comedy (San Francisco, CA) | 250 |
| 11449 | Gold Coast Comedy Club (Fort Lauderdale, FL) | 60 |
| 8708 | The Comedy Bar - Pittsburgh (Pittsburgh, PA) | 42 |
| 11133 | BATS Improv (San Francisco, CA) | 36 |
| 8694 | Henceforth Comedy / Secret Society (Cleveland, OH) | 32 |
| 11089 | Comedy Oakland (Oakland, CA) | 28 |
| 8691 | Snowflake Comedy (Cleveland, OH) | 5 |
| 11287 | South Beach Comedy Club (Miami, FL) | 4 |
| 200 | Comedy on Collins (Miami Beach, FL) | 1–2 |
| 8697 | Puff Puff Laugh Comedy Show (Cleveland, OH) | 1 |
| 8701 | Pagliacci's Comedy Club (Irwin, PA) | 1 |
| 8733 | Lucky Haskin Productions (Willoughby, OH) | 1 |
| 9063 | Comedians You Should Know / CYSK (Chicago, IL) | 1 |
| 10950 | Lots of Laughs Comedy Lounge (North Andover, MA) | 1 |
| 11105 | Clayton Club Saloon (Clayton, CA) | 1 |
| 11108 | 硅谷脱口秀 Silicomedy (San Jose, CA) | 1 |
| 11319 | Pikes Punks Comedy Show (Colorado Springs, CO) | 1 |

### 1b. Empty organizer feeds (10) — dormant-but-real → **leave**
Ran successfully (HTTP 200, `items_before_filter=0`) — the organizer currently lists
no upcoming comedy. Real organizers/venues; will repopulate when they post events.

8700 The Rock Comedy Show Live · 10951 Bobby's Place Night Club · 10959 McCues Comedy
Club · 10960 Blend Comedy · 11090 The Lumpia Company · 11119 Deja Blue · 11121 Music
City Starfactory · 11122 San Francisco Comedy College · 11251 CBA Event Center ·
11252 HollyLou Entertainment

### 1c. Comedy-filtered (1) — dormant-but-real → **leave**
- **8690 Centennial Plaza (Canton, OH)** — feed returned 1 item that the comedy
  filter dropped (`items_before_filter=1`, 0 shows). Real venue; no current comedy.

---

## Cluster 2 — Etix (9) — criterion 11548 (coordinated with TASK-2858, not duplicated)

The etix scraper is healthy (Funny Bones produce hundreds of shows). The dry etix
venues fall into three buckets; **none is a scraper bug**.

| club_id | venue | disposition |
|--------:|-------|-------------|
| 8715 | Robins Theatre (Warren, OH) | DataDome-403 walled — **defer to TASK-2858** |
| 8730 | The Original Pittsburgh Winery (Pittsburgh, PA) | DataDome-403 walled — **defer to TASK-2858** |
| 9070 | The Laughing Tap (Milwaukee, WI) | DataDome-403 walled — **defer to TASK-2858** |
| 9072 | Des Plaines Theatre (Des Plaines, IL) | DataDome-403 walled — **defer to TASK-2858** |
| 9073 | Raue Center For The Arts (Crystal Lake, IL) | DataDome-403 walled — **defer to TASK-2858** |
| 9074 | The Vixen (McHenry, IL) | DataDome-403 walled — **defer to TASK-2858** |
| 10971 | Nashua Center for the Arts (Nashua, NH) | DataDome-403 walled — **defer to TASK-2858** |
| 10976 | Colonial Theatre Laconia (Laconia, NH) | Empty feed (no block) — dormant-but-real, **leave** |
| 11431 | **Liberty Funny Bone (Liberty Township, OH)** | **LIT UP — 113 shows** (was never-run; `liberty.funnybone.com/shows/` is not walled) |

**Why the 7 walled venues are deferred, not "fixed":** they use direct
`etix.com/ticket/v/<venue_id>` URLs. Locally and on GHA these return HTTP 403 and the
Playwright/capsolver fallback fails with `blocked captcha url is not supported`
(their production run history shows the same 403). They are independent theatres with
no non-etix fallback source, so there is no config switch available — recovery is
exactly the auto-reprobe/readopt work tracked by **TASK-2858**. Do not duplicate it here.

**Liberty Funny Bone follow-up (optional hygiene):** it is a Funny Bone but is
unchained (`chain_id=NULL`); the other Funny Bones are `chain_id=3`. Chaining it would
stop it resurfacing in future "unchained" audits. Left out of this task to avoid
scope creep on identity/dedup; coverage is already recovered.

---

## Cluster 3 — Singletons (17) — criterion 11549

Each was live-probed. **All 17 are dormant-but-real → leave.** Every scraper ran
cleanly (no bot-block, HTTP 200/none) and the source feed simply has no current
comedy — none is a scraper crash or a feed that returns data we then drop.

| club_id | venue | scraper | probe result | disposition |
|--------:|-------|---------|--------------|-------------|
| 8841 | ComedySportz (Burbank, CA) | vbo_tickets | 0 shows, clean | dormant — leave |
| 8901 | KeyBank State Theatre (Cleveland, OH) | playhouse_square | 0 shows, clean | dormant — leave |
| 9087 | Moonlight Theatre (St. Charles, IL) | modern_events_calendar | 0 shows, clean | dormant — leave |
| 10980 | Playhouse on Park (West Hartford, CT) | tix_com | 0 shows, clean | dormant — leave |
| 11120 | The Stage at Burke Junction (Cameron Park, CA) | ticketspice | 1 item filtered, 0 valid | dormant — leave |
| 11123 | Continental Club (Oakland, CA) | ticket_tailor | 0 shows, clean | dormant — leave |
| 11299 | Curtis Park Comedy (Denver, CO) | ticket_tailor | 0 shows, clean | dormant — leave |
| 11323 | Nowhere Pizza & Pub • Copper (Frisco, CO) | multipass | 0 shows, clean | dormant — leave |
| 11325 | Apotheosis Comics and Lounge (St. Louis, MO) | do314 | 0 shows, clean | dormant — leave |
| 11438 | The Dinner Detective St. Paul (St. Paul, MN) | json_ld | 0 shows, clean | dormant — leave |
| 10965 | Loft Comedy Club (Westfield, MA) | seatengine | `no events found for venue 312` | dormant — leave |
| 456 | SuperNova Comedy (Los Angeles, CA) | seatengine_classic | 0 shows, clean | dormant — leave |
| 9066 | Laugh And Enjoy Comedy Club (West Chicago, IL) | seatengine_v3 | 0 shows, clean | dormant — leave |
| 8827 | Tao Comedy Studio (Los Angeles, CA) | the_events_calendar | 0 shows, clean | dormant — leave |
| 8838 | Yeah Mon Comedy Lounge (Los Angeles, CA) | the_events_calendar | 0 shows, clean | dormant — leave |
| 8727 | The Columbus Athenaeum (Columbus, OH) | ticketmaster_comedy | 0 shows, clean | dormant — leave |
| 11111 | Grindhouse Comedy (Sacramento, CA) | wix_events | 0 shows, clean | dormant — leave |

Two probes are mildly worth a future spot-check if these stay dry long-term (the
source id may need re-verification against the live site), but neither is broken now:
**11120** (ticketspice returned exactly 1 non-comedy item) and **10965** (seatengine
venue 312 has no events).

---

## Summary of actions taken

- **3971** — already retired (criterion 11550, prior session).
- **11431 Liberty Funny Bone** — **coverage recovered (113 shows persisted)** via a
  live run; source config was already correct, it had simply never run.
- **28 eventbrite** — confirmed organizer-feed-by-design (coverage on venue clubs);
  left as-is. No stale ids found.
- **7 etix direct-URL theatres** — confirmed DataDome-walled; deferred to TASK-2858.
- **1 etix (Colonial Laconia) + 17 singletons** — confirmed dormant-but-real; left as-is.

No venues were retired in this pass beyond the pre-resolved 3971: every remaining
venue is a real venue with a real address, per the owner's keep rule.
