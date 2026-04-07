# Club Taxonomy Audit — TASK-1033

**Date**: 2026-04-07
**Scope**: Classify all 49 venue scrapers along two axes (data source type, process type), identify mismatches, and evaluate Club model metadata changes.

---

## 1. Complete Classification

### Venue Scrapers (implementations/venues/)

| # | Directory | Club Name | Data Source Type | Process Type | Ticketing Platform |
|---|-----------|-----------|-----------------|--------------|-------------------|
| 1 | `annoyance` | Annoyance Theatre | `external_api` (ThunderTix JSON) | single | ThunderTix |
| 2 | `broadway_comedy_club` | Broadway Comedy Club | `html` + Tessera API enrichment | single | Tessera |
| 3 | `bushwick` | Bushwick Comedy Club | `external_api` (Wix Events) | single | Wix Events |
| 4 | `comedy_at_the_carlson` | Comedy @ The Carlson | `external_api` (OvationTix) | multi_step | OvationTix |
| 5 | `comedy_cellar` | Comedy Cellar | `external_api` (proprietary JSON) | single | Proprietary |
| 6 | `comedy_clubhouse` | Comedy Clubhouse | `html` (TicketSource) | single | TicketSource |
| 7 | `comedy_corner_underground` | Comedy Corner Underground | `rsc` (StageTime) | multi_step | StageTime |
| 8 | `comedy_key_west` | Comedy Key West | `rsc` (Punchup) | single | Punchup |
| 9 | `comedy_magic_club` | Comedy & Magic Club | `html` (rhp-events) | single | eTix |
| 10 | `comedy_mothership` | Comedy Mothership | `html` (Next.js) | single | SquadUP |
| 11 | `comedy_store` | The Comedy Store | `html` (PHP calendar) | multi_step | ShowClix |
| 12 | `creek_and_cave` | Creek and The Cave | `json_feed` (S3 bucket) | single | ShowClix |
| 13 | `csz_philadelphia` | CSz Philadelphia | `html` (VBO Tickets) | multi_step | VBO Tickets |
| 14 | `dynasty_typewriter` | Dynasty Typewriter | `external_api` (SquadUP v3) | single | SquadUP |
| 15 | `east_austin_comedy` | East Austin Comedy | `external_api` (Netlify) | single | Square |
| 16 | `esthers_follies` | Esther's Follies | `html` (VBO Tickets) | multi_step | VBO Tickets |
| 17 | `flappers` | Flappers Comedy Club | `html` (PHP calendar) | multi_step | Flappers (proprietary) |
| 18 | `four_day_weekend` | Four Day Weekend | `external_api` (OvationTix) | multi_step | OvationTix |
| 19 | `funny_bone` | Funny Bone | `html` (Rockhouse Partners) | single | Rockhouse Partners |
| 20 | `goofs` | Goofs Comedy Club | `rsc` (Next.js) | single | Proprietary |
| 21 | `gotham` | Gotham Comedy Club | `json_feed` (S3 bucket) | single | ShowClix |
| 22 | `grove_34` | Grove 34 | `json_ld` (Webflow) | multi_step | Webflow |
| 23 | `haha_comedy_club` | HAHA Comedy Club | `json_ld` + HTML time | single | Tixr |
| 24 | `ice_house` | Ice House | `external_api` (Tockify) | single | ShowClix |
| 25 | `improv` | Improv (multi-location) | `json_ld` | multi_step | Various |
| 26 | `improv_asylum` | Improv Asylum | `json_ld` (Tixr group) | multi_step | Tixr |
| 27 | `io_theater` | iO Theater Chicago | `external_api` (Crowdwork) | single | Crowdwork |
| 28 | `laugh_boston` | Laugh Boston | `external_api` (Pixl Calendar) | single | Tixr |
| 29 | `laugh_factory_covina` | Laugh Factory Covina | `json_ld` (Tixr group) | multi_step | Tixr |
| 30 | `laugh_factory_reno` | Laugh Factory Reno | `html` (CMS) | single | Punchup |
| 31 | `logan_square_improv` | Logan Square Improv | `external_api` (Crowdwork) | single | Crowdwork |
| 32 | `mccurdys_comedy_theatre` | McCurdy's Comedy Theatre | `html` (ColdFusion) | multi_step | Etix |
| 33 | `nicks_comedy_stop` | Nick's Comedy Stop | `external_api` (Wix Events) | single | Wix Events |
| 34 | `philly_improv_theater` | Philly Improv Theater | `external_api` (Crowdwork) | single | Crowdwork |
| 35 | `red_room` | RED ROOM Comedy Club | `external_api` (Wix Events) | single | Wix Events |
| 36 | `rodneys` | Rodney's Comedy Club | `html` + `json_ld` | multi_step | Eventbrite/22Rams |
| 37 | `setup_sf` | The Setup SF | `csv_feed` (Google Sheets) | single | Squarespace |
| 38 | `sports_drink` | Sports Drink | `html` (OpenDate) | single | OpenDate |
| 39 | `st_marks` | St. Marks Comedy Club | `html` → `json_ld` (Tixr) | multi_step | Tixr |
| 40 | `standup_ny` | StandUp NY | `graphql` (ShowTix4U) | multi_step | VenuePilot |
| 41 | `stevie_rays` | Stevie Ray's Improv | `html` (Theatre Manager, Playwright) | single | Theatre Manager |
| 42 | `sunset_strip` | Sunset Strip | `external_api` (SquadUP v3) | single | SquadUP |
| 43 | `the_rockwell` | The Rockwell | `external_api` (WordPress REST) | single | Tribe Events |
| 44 | `the_stand` | The Stand NYC | `json_ld` (Tixr) | multi_step | Tixr |
| 45 | `third_coast_comedy` | Third Coast Comedy | `html` (Vivenu Next.js) | single | Vivenu |
| 46 | `uncle_vinnies` | Uncle Vinnie's | `external_api` (OvationTix) | multi_step | OvationTix |
| 47 | `up_comedy_club` | UP Comedy Club | `graphql` + JSON | multi_step | Salesforce |
| 48 | `uptown_theater` | Uptown Theater | `json_ld` (Webflow) | multi_step | Webflow |
| 49 | `west_side` | West Side Comedy Club | `rsc` (Punchup) | single | Punchup |
| 50 | `zanies` | Zanies Comedy Club | `html` (WordPress rhp-events) | multi_step | eTix/Eventbrite |

### Platform/API Scrapers (implementations/api/)

These are **generic scrapers** that serve multiple clubs via config, not per-venue code:

| Scraper | Data Source Type | Process Type | Clubs Using |
|---------|-----------------|--------------|-------------|
| `crowdwork` | `external_api` | single | iO Theater, Logan Square, PHIT |
| `eventbrite` | `external_api` | single | CIC Theater, Comedy on Collins, + others |
| `eventbrite_national` | `external_api` | single | National discovery |
| `ninkashi` | `external_api` | single | (Ninkashi venues) |
| `seatengine` / `seatengine_v3` | `external_api` | single | (SeatEngine venues) |
| `seatengine_national` / `seatengine_v3_national` | `external_api` | single | National discovery |
| `squarespace` | `external_api` | single | (Squarespace venues) |
| `ticketmaster` / `ticketmaster_national` | `external_api` | single | (Ticketmaster venues) |
| `tixr` | `external_api` + `json_ld` | multi_step | Tixr venues |
| `tour_dates` | `external_api` | single | Comedian tour dates |

---

## 2. Data Source Type Distribution

| Data Source Type | Count | Venues |
|-----------------|-------|--------|
| `external_api` | 17 | Annoyance, Bushwick, Carlson, Comedy Cellar, Dynasty Typewriter, East Austin, Four Day Weekend, Ice House, iO Theater, Laugh Boston, Logan Square, Nick's, PHIT, RED ROOM, Sunset Strip, The Rockwell, Uncle Vinnie's |
| `html` | 14 | Broadway, Clubhouse, Magic Club, Mothership, Comedy Store, CSz Philly, Esther's, Flappers, Funny Bone, Laugh Factory Reno, McCurdy's, Rodneys, Sports Drink, Stevie Ray's, Zanies |
| `json_ld` | 7 | Grove 34, HAHA, Improv, Improv Asylum, Laugh Factory Covina, The Stand, Uptown Theater |
| `rsc` | 3 | Comedy Corner Underground, Comedy Key West, Goofs, West Side |
| `json_feed` | 2 | Creek and Cave (S3), Gotham (S3) |
| `graphql` | 2 | StandUp NY, UP Comedy Club |
| `csv_feed` | 1 | The Setup SF |

### Process Type Distribution

| Process Type | Count |
|-------------|-------|
| `single` | 28 |
| `multi_step` | 22 |

---

## 3. Mismatches & Observations

### Hybrid Data Sources
Several scrapers use **mixed** data source types, making single-label classification imperfect:

1. **Broadway** — HTML primary + Tessera JSON API enrichment → classified `html` but has API component
2. **HAHA Comedy Club** — JSON-LD for events + HTML for time extraction → classified `json_ld` (primary)
3. **Rodneys** — HTML scraping + JSON-LD fallback → classified `html` (primary)
4. **St. Marks** — HTML listing → Tixr JSON-LD per event → classified `multi_step` with `html` → `json_ld`
5. **The Stand** — HTML listing → horizontal pagination → Tixr enrichment → classified `json_ld`

### Venue Scrapers That Could Be Platform Scrapers
These venue-specific scrapers implement logic that's duplicated across the platform scraper:

1. **Crowdwork venues** (iO Theater, Logan Square, PHIT) — all 3 have venue-specific dirs but share `CrowdworkClient`. Could use the generic `crowdwork` API scraper with just config.
2. **OvationTix venues** (Carlson, Four Day Weekend, Uncle Vinnie's) — share `OvationTixClient`. The `api/` dir doesn't have an OvationTix platform scraper yet.
3. **Wix Events venues** (Bushwick, Nick's, RED ROOM) — share `WixEventsClient`. No generic `wix` platform scraper exists.
4. **SquadUP venues** (Dynasty Typewriter, Sunset Strip) — share similar SquadUP API logic. No generic scraper.

### Scrapers Requiring Special Runtime
- **Stevie Ray's** — requires Playwright (headless browser) due to Theatre Manager's JS rendering. Only venue needing this.

---

## 4. Evaluation: Should the Club Model Get New Fields?

### Proposed Fields

| Field | Type | Purpose |
|-------|------|---------|
| `data_source_type` | Enum: `external_api`, `html`, `json_ld`, `rsc`, `json_feed`, `graphql`, `csv_feed` | How the scraper fetches data |
| `process_type` | Enum: `single`, `multi_step` | Whether scraping requires sequential page fetches |
| `ticketing_platform` | String (nullable) | The ticketing provider (Tixr, OvationTix, Eventbrite, etc.) |

### Assessment: **Documentation-only — do NOT add schema fields**

**Arguments against schema changes:**

1. **The `scraper` field already determines behavior.** The resolver uses `club.scraper` to select the scraper class. Adding `data_source_type` or `process_type` wouldn't change any runtime behavior — the scraper class already encapsulates both.

2. **Classification is ambiguous for hybrids.** 5+ scrapers use mixed data sources (HTML + API, JSON-LD + HTML). Forcing a single enum value loses information. A documentation table (like this audit) captures the full picture better than a DB column.

3. **Ticketing platform is already partially tracked.** `eventbrite_id`, `seatengine_id`, and `ticketmaster_id` exist as dedicated fields. A `ticketing_platform` string would duplicate this signal without adding queryability.

4. **Process type is an implementation detail.** Whether a scraper makes 1 or N HTTP calls is an internal concern. It doesn't affect the web app, API consumers, or end users.

5. **Maintenance burden.** Every new venue onboarding would require setting 2-3 extra fields that serve no runtime purpose. Enum values would need schema migrations whenever a new data source type appears.

6. **No consumer for the data.** The web app doesn't display scraper methodology to users. The nightly CI/CD pipeline doesn't route based on data source type. The only consumer would be developer documentation — which this audit document serves.

### What WOULD warrant schema changes

If in the future we want to:
- **Auto-select scraper class** based on `data_source_type` (e.g., all `json_ld` clubs use a generic JSON-LD scraper) → then `data_source_type` becomes load-bearing and belongs in the DB
- **Batch-run scrapers by platform** (e.g., "run all Eventbrite scrapers") → the existing `eventbrite_id IS NOT NULL` filter already enables this for tracked platforms
- **Display ticketing platform in the web UI** → then `ticketing_platform` earns its place

None of these use cases exist today.

---

## 5. Recommendation

1. **Keep this audit document** as the authoritative classification reference (`audit/club_taxonomy_audit.md`)
2. **Do not add `data_source_type`, `process_type`, or `ticketing_platform` to the Club model** — they would be documentation-only fields with maintenance cost and no runtime value
3. **Consider consolidating platform scrapers** in a future task:
   - OvationTix: 3 venues share `OvationTixClient` but have separate scraper dirs
   - Wix Events: 3 venues share `WixEventsClient` but have separate scraper dirs
   - SquadUP: 2 venues share similar API logic
4. **The existing `scraper` string field + platform ID fields (`eventbrite_id`, `seatengine_id`, `ticketmaster_id`)** are sufficient for current needs

### Should metadata drive scraper resolution?

**No, not at this time.** The current resolver design (string key → class) is simple, explicit, and works. A metadata-driven resolver (e.g., "use the generic Tixr scraper for any club where `data_source_type = 'external_api'` and `ticketing_platform = 'tixr'`") would:
- Require a more complex resolver with fallback logic
- Make it harder to handle venue-specific quirks (e.g., HAHA's JSON-LD + HTML time parsing)
- Not reduce code — venue-specific `data.py` and `transformer.py` would still be needed

The better path toward consolidation is **growing the platform scrapers** (in `implementations/api/`) and migrating compatible venues to use them, which is already happening organically (Eventbrite, SeatEngine, Crowdwork all have platform scrapers).
