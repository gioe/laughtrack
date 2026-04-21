---
name: adopt-scraper
description: "Standard process to research a venue, identify its ticketing platform, and build/configure the correct scraper. Usage: /adopt-scraper <club name>"
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, WebSearch, WebFetch, Agent
trigger: automatically invoked by /tusk when working on an "Onboard <club>" task
---

# Adopt Scraper

Standardized process for onboarding a comedy club scraper. Given a club name (and
optionally city/state from the task description), this skill walks through platform
discovery, scraper selection, migration creation, and verification.

## Usage

```
/adopt-scraper Punch Line Sacramento
```

Or invoked automatically when `/tusk` picks up a task whose summary starts with "Onboard".

## Arguments

- Club name (required) — the venue to onboard
- City/state context is pulled from the task description if available

## Guiding Principle: Club Website First

**Always prefer scraping from the club's own website over aggregator APIs.**

Even if a venue has a Ticketmaster, SeatEngine, or Eventbrite presence, check the
club's website first. If the site has structured event data (JS calendar widgets,
JSON-LD, embedded ticket listings), build a scraper that fetches from the club's
site. This ensures:

- `show_page_url` points to the club's own site, driving traffic to the venue
- We support the club's direct sales rather than sending users to an aggregator
- The club benefits from the exposure we provide

**Only fall back to aggregator APIs** (`live_nation`, `eventbrite`, `seatengine`) when:
- The club has no website or the website is down
- The website has no event/calendar page
- The website only links out to the aggregator with no local event data
- The website's event data is insufficient (e.g., no dates, no ticket links)

The ticket `purchase_url` (on the Ticket entity) can still point to the third-party
platform for checkout — it's the `show_page_url` on the Show that must point to the
club's site whenever possible.

## Step 0: Look Up Existing Club Data

If the club already exists in the database (e.g., triage tasks), fetch its current
record first — this gives you the scraper type, platform IDs, website, and location
without guessing column names:

```bash
make -C "$(git rev-parse --show-toplevel)/apps/scraper" club CLUB='<Club Name>'
# or by ID:
make -C "$(git rev-parse --show-toplevel)/apps/scraper" club ID=<club_id>
```

Use this output to inform your research — e.g., check the existing `seatengine_id`,
`eventbrite_id`, or `scraping_url` before searching the web.

## Step 0a: Regression Fast-Path (Existing Scraper Only)

If Step 0 showed the club **already has a working scraper** (non-null `scraper`
column, non-null `scraping_url`), this is most likely a nightly-triage regression
task — not a new-venue onboarding. Before launching the full discovery flow,
reproduce the failure:

```bash
cd apps/scraper && make scrape-club CLUB='<Club Name>' 2>&1 | tail -30
```

- **Scraper returns shows locally** → do NOT close as transient yet. A local
  pass only proves the scraper works from a residential IP; the nightly runs
  on GHA datacenter IPs, which DataDome / Cloudflare / Tixr's WAFs treat very
  differently. Confirm against GHA before closing:

  ```bash
  gh workflow run scraper-verify.yml -f club_id=<club_id>
  gh run list --workflow=scraper-verify.yml --limit 3
  gh run watch <run_id> --exit-status
  gh run download <run_id> -n "scraper-verify-club-<club_id>-<run_id>" -D /tmp/verify-<club_id>
  tail -3 /tmp/verify-<club_id>/scrape-output.log     # look for "Scraped N shows"
  ```

  - **GHA returns shows** → the nightly failure was transient. Mark criteria
    done with a `--note` citing BOTH the local baseline AND the GHA run ID,
    then close via `tusk abandon <id> --reason wont_do --session <sid>`.
    Skip Steps 1–5.
  - **GHA returns 0 shows** → the failure is GHA-specific (datacenter-IP
    block, TLS fingerprint, etc.). Proceed to Step 1 with the full
    rediscovery flow, and focus on bot-bypass fixes (Playwright fallback,
    TLS impersonation, proxy) rather than platform migration.

- **Scraper returns 0 shows or errors locally** → the failure is reproducible
  on any IP. Proceed to Step 1 with the full rediscovery flow.

For genuinely new venues (no existing scraper), skip this step.

## Step 1: Research the Venue

### 1a. Find the Club Website

Search the web for the club's official website:

```
WebSearch: "<club name>" comedy club official site
```

Look for the **official venue website** (not a Yelp listing, not a Facebook page).
Record:
- **Website URL** (use `https://` — see CLAUDE.md rule on HTTPS)
- **Address** (street address from the website or Google)
- **City, State, Zip** (confirm against the task description)

If the club appears to be **permanently closed** (website down, Google says "Permanently
closed", no social media activity in 6+ months), invoke `/close-club <club_id>` to mark
the row as `status='closed'`, `visible=false`, `closed_at=NOW()` and generate the
corresponding migration. Commit the migration on the task's feature branch, then report:

> This venue is permanently closed. Closed via `/close-club` and migration committed.

Do NOT use `/hide-club` for confirmed-defunct venues — it only flips `visible` and
leaves `status='active'`, which pollutes downstream reporting. `/hide-club` is for
reversible hiding (duplicates pending merge, data-quality pulls).

### 1a-2. Check if This Is a Production Company, Not a Venue

If the research reveals the entity is a **comedy production company** (produces shows
at third-party venues, has no dedicated physical space), it should be modeled as a
`ProductionCompany`, not a `Club`. Signs include:

- Website says "we produce shows at..." or lists multiple unrelated venues
- No fixed address — shows happen at rotating locations
- Eventbrite/ticketing presence is under an "organizer" profile, not a venue

**If this is a production company:**

1. Hide the club record (`visible = false`) — it's not a venue
2. Create a `ProductionCompany` record via migration:

```sql
-- Hide club record (not a venue)
UPDATE clubs SET visible = false WHERE id = <club_id>;

-- Create as production company
INSERT INTO production_companies (name, slug, website, scraping_url, visible, show_name_keywords)
VALUES (
    '<Name>',
    '<slug>',
    'https://<website>',
    '<scraping_url>',
    true,
    ARRAY['comedy', 'stand-up', 'standup', 'stand up', 'improv', 'open mic', 'open-mic',
          'comedian', 'comic', 'laugh', 'humor', 'jokes']
)
ON CONFLICT (name) DO NOTHING;
```

3. If any of the venues the company produces at are already in our DB, link them:
```sql
INSERT INTO production_company_venues (production_company_id, club_id)
VALUES (<prod_co_id>, <club_id>)
ON CONFLICT DO NOTHING;
```

4. Apply the migration, commit, and skip to Step 5 (report). No scraper verification
   needed — production company scraping is handled separately.

Use the existing Laff House record (`production_companies` id=1) as a reference for
field values like `show_name_keywords`.

### 1a-3. Check if This Is a Seasonal Festival on Hiatus

If the venue is a **comedy festival** (annual multi-day event, multi-venue) and the
homepage explicitly states it is skipping a year (e.g., "Taking 2026 off", "See you
in 2027", "We'll be back next year"), treat this as a hiatus — not a closure.

Signs of a festival (vs. a regular club):

- Name includes "Festival", "Fest", or "Sketchfest"
- `club_type = 'festival'` on the existing row
- Website lists multiple partner venues the festival runs shows at
- Social media posts reference annual editions (e.g., "Year 12")

**If the festival is on hiatus** (taking a year off but not defunct):

```sql
-- Mark festival as on hiatus — active but not currently running
UPDATE clubs
SET status = 'hiatus',
    website = 'https://<festival_domain>'
WHERE id = <club_id>;
```

Keep `visible = false` (nothing to show this year). Apply the migration, commit,
and skip to Step 5 — no scraper needed. Note: `hiatus` is a new status value that
won't match existing `active`/`closed` filters; downstream code that assumes a
two-value enum may need updates (flag as a follow-up task if you encounter such
code during the research).

If the festival is permanently cancelled (organizers announce it's over), use
`status = 'closed'` instead and follow the normal closure pattern.

### 1a-4. Check if This Is a Festival With Fragmented Multi-Venue Ticketing

Some festivals are actively running (not on hiatus, not closed) but sell tickets
through **many different platforms per show** — e.g., one show on Crowdwork, another
on exploretock, others on Don't Tell Comedy / Humanitix / Next Stop Comedy — with
no single aggregator API or widget on the festival's own site. The tickets page is
just static HTML with hand-authored links to each per-event platform.

Signs:

- `club_type = 'festival'`
- Tickets page links to 3+ distinct ticketing domains
- No iframe, widget, or JSON API ties them together
- Main partner venues (e.g., the comedy-club host) are already onboarded as
  separate clubs and will capture their festival-week shows through their own
  scrapers

**Action:** update metadata (current website, clear stale platform IDs) and keep
`visible = false`. Set `scraper = NULL` (no unified scraper applies). Note in a
`tusk progress` message that festival improv/standup shows are captured via the
host venue's scraper. Do not hide or close — `status` stays `active`.

### 1b. Find the Events/Shows Page

From the website, locate the page that lists upcoming shows. This is usually linked as
"Shows", "Events", "Calendar", "Tickets", or "Schedule" in the navigation.

Record the **events page URL** — this is the page we'll analyze for platform detection.

If the venue has **no events page** and only links to external ticket sellers (e.g.,
"Buy tickets on Ticketmaster"), note the external platform and skip to Step 2.

## Step 2: Identify the Ticketing Platform

**Remember: club website first.** The goal is to find the best way to scrape event
data directly from the club's own site. Only resort to aggregator APIs when the
club's site doesn't provide enough structured data.

Fetch the events page and inspect its content:

```
WebFetch: <events page URL>
```

### 2a. Check for Scrapable Data on the Club's Own Site

First, look for structured event data embedded directly in the club's website HTML
or JavaScript. These patterns let us scrape from the club's site (keeping
`show_page_url` pointed at the venue):

| Pattern in page | Platform | Scraper |
|----------------|----------|---------|
| `var all_events = [...]` JS array + `tw-plugin-calendar` | TicketWeb (WordPress plugin) | `ticketweb` (generic) |
| `<script type="application/ld+json">` with `"@type": "Event"` | JSON-LD | `json_ld` (generic) |
| `rhpSingleEvent` / `rhp-event__title--list` CSS classes | rhp-events (WordPress) | `comedy_magic_club` (generic) |
| `self.__next_f.push` RSC segments + `stageti.me` | StageTime | venue-specific |
| `app.opendate.io` / `confirm-card` divs | OpenDate | venue-specific |
| `eventRow` / `dateTime` / `event-btn` CSS classes | TicketSource | venue-specific |
| `events.humanitix.com/host/` links | Humanitix | `json_ld` (generic) |
| `showpass.com/widget/` iframe or `showpass.com` buy links | Showpass | venue-specific (ref: `comedy_cave`) |
| `app.showslinger.com` iframe / `promo_widget_v3` embed | ShowSlinger | venue-specific |

If a match is found, skip to Step 3. The scraper will fetch from the club's URL.

### 2b. Check for Third-Party Platform Links (Aggregator Fallback)

Only if Step 2a found no scrapable data on the club's site, look for aggregator
platform links. These scrapers use the platform's API directly — `show_page_url`
will point to the aggregator, not the club:

| Pattern in page | Platform | Scraper |
|----------------|----------|---------|
| `ticketmaster.com` buy link or embed | Ticketmaster | `live_nation` (generic) |
| `eventbrite.com` buy link or embed | Eventbrite | `eventbrite` (generic) |
| `seatengine.net` buy link | SeatEngine | `seatengine` / `seatengine_v3` (generic) |
| `thundertix.com` buy link | ThunderTix | venue-specific (new code) |
| `tixr.com` buy link | Tixr | venue-specific (new code) |
| `prekindle.com` buy link | Prekindle | `json_ld` (generic) |

If a match is found, skip to Step 3.

### 2c. Check for Platform APIs (JS-Heavy Sites)

If no patterns were found in the HTML source, the site may use an embedded widget
that loads data via JavaScript. Use Playwright to check network requests:

```
browser_navigate → <events page URL>
browser_network_requests
```

Look for these API calls (ordered by preference — club-hosted APIs first):

| Network request pattern | Platform | Scraper | Data source |
|------------------------|----------|---------|-------------|
| `/wp-json/tribe/events/v1/events` | Tribe Events (WordPress) | `the_rockwell` (generic) | Club site |
| `/api/open/GetItemsByMonth` | Squarespace | venue-specific | Club site |
| `crowdwork.com/api/v2` | Crowdwork | venue-specific | Club site |
| `tockify.com/api/` | Tockify | venue-specific | Club site |
| `plugin.vbotickets.com` | VBO Tickets | venue-specific | Club site |
| `/.netlify/functions/` | Netlify Functions | venue-specific | Club site |
| `editmysite.com/app/store/api/` | Square Online (Weebly) | venue-specific | Club site |
| `api.ninkashi.com` | Ninkashi | `ninkashi` (generic) | Third-party |
| `vivenu` | Vivenu | `vivenu` (generic) | Third-party |
| `showpass.com/api/public/venues/` | Showpass | venue-specific (ref: `comedy_cave`) | Third-party |

If Playwright fails (Chrome conflict), fall back to reading the page source via
WebFetch and looking for `<script>` tags, `data-` attributes, or embedded iframes.

### 2d. Check Page Source for Additional Markup Patterns

If no API calls match, inspect the page HTML for remaining widget patterns:

| Source pattern | Platform | Scraper |
|---------------|----------|---------|
| `data-compId` on Wix widget / `wixstatic.com` | Wix Events | venue-specific |
| `squadup = { userId:` in JS | SquadUP | venue-specific |

### 2e. No Match — Mandatory Deep Inspection Before Giving Up

**CRITICAL: Before concluding a platform is unsupported or recommending hide/close,
you MUST run `/investigate-site` on the venue's events page URL.** This opens the page
in Playwright MCP, captures all network requests, inspects page source for widget
patterns, and reports any detected platform and API endpoints.

```
/investigate-site <events page URL>
```

The skill returns a structured report with detected platform, API URLs, and a
recommendation. Use that report to inform your decision.

If `/investigate-site` detects a platform or API endpoint, use its recommendation to
proceed with Step 3 (configure the appropriate scraper).

**Only after `/investigate-site` confirms no scrapable API exists**, proceed:
- Check if the venue uses a **tour_dates / Bandsintown** widget — these are NOT
  sufficient for a dedicated scraper (per project feedback). Note this in the task.
- If the site is purely static HTML with show listings, a custom HTML scraper may
  be needed — flag as higher complexity.
- If the venue has **no online ticket sales** at all, recommend closing the task.

**Important: Cloudflare 403 does NOT mean a site is unscrapable.** The scraper's
`HttpClient.fetch_html` automatically falls back to a headless Playwright browser
when it detects Cloudflare challenges ("Just a moment..."), DataDome, or other
bot-block signatures. Always test fetchability using the scraper's own stack
(see CLAUDE.md rule), not plain `requests`/`urllib`. If Playwright fallback
succeeds, generic scrapers like `json_ld` will work normally.

## Step 3: Configure or Build the Scraper

Based on the platform identified in Step 2, follow ONE of the two paths below.

### Path A: Generic Scraper (No New Code)

For platforms with existing generic scrapers (`ticketweb`, `json_ld`, `the_rockwell`,
`comedy_magic_club`, `live_nation`, `eventbrite`, `seatengine`, `seatengine_v3`,
`ninkashi`, `vivenu`):

**3A-1. Extract the Platform ID**

**3A-1b. Verify the Platform ID Returns Data**

Before creating the migration, hit the platform API directly to confirm the ID
returns actual event data (not just a valid profile with 0 events). For Eventbrite,
use the scraper's auth token to call the organizer/venue events endpoint and check
`pagination.object_count > 0`. For SeatEngine, check the venue API returns a valid
response. If the API returns 0 events and the venue website is also down, the
platform ID may be stale — consider hiding the club instead of switching scrapers.

Each generic scraper needs a platform-specific identifier:

| Scraper | ID to extract | How to find it |
|---------|--------------|----------------|
| `ticketweb` | `scraping_url` | The club's calendar/events page URL containing the TicketWeb WordPress plugin (`var all_events` JS array + `tw-plugin-calendar` classes) |
| `live_nation` | `ticketmaster_id` | Search Discovery API: `curl -s "https://app.ticketmaster.com/discovery/v2/venues.json?apikey=$TICKETMASTER_API_KEY&keyword=<name>&countryCode=US"` — use the alphanumeric `id` field (e.g., `KovZpZAJalFA`), NOT a numeric ID |
| `eventbrite` | `eventbrite_id` | Extract organizer ID (11 digits) or venue ID (8-9 digits) from the Eventbrite URL |
| `seatengine` | `seatengine_id` | Numeric ID from `{venue}.seatengine.net` URL (1-700 range). **If the stored ID returns 0 events**, fetch the venue's events page (`<slug>.seatengine.com/events` or `/calendar`) and grep for `files.seatengine.com/styles/logos/(\d+)/` — the real venue_id is often embedded in the logo path and is present even when 0 shows are on sale. **Always verify a logo-derived ID against `GET https://services.seatengine.com/api/v1/venues/<id>` (header `x-auth-token: $SEATENGINE_AUTH_TOKEN`) and confirm the returned `name` matches the venue being researched** — festival/pop-up subdomains can display a producing venue's logo (e.g., `showemcomedyfestival-com.seatengine.com` serves logo `204` = "Off The Hook Comedy Club", but the festival's real venue is `216`). As a fallback, fetch a live show page (`<slug>.seatengine.com/shows/<show_id>`) and grep for `venue_id` in the HTML (e.g., `"venue_id":366`). The stored ID may be stale after SeatEngine migrations. |
| `seatengine_v3` | `seatengine_id` | UUID from `v-{uuid}.seatengine.net` URL |
| `json_ld` | `scraping_url` | The events page URL containing JSON-LD Event markup |
| `the_rockwell` | `scraping_url` | The Tribe Events REST API base URL |
| `comedy_magic_club` | `scraping_url` | The events page URL with rhp-events markup |
| `ninkashi` | `scraping_url` | The tickets subdomain (e.g., `tickets.myvenue.com`) |
| `vivenu` | `scraping_url` | The Vivenu seller page root URL |

**3A-2. Check for Duplicate Club Names**

Before creating a migration, verify the intended club name doesn't already exist in
the database (venues sometimes rebrand, and a second record may already be onboarded
under the new name):

```bash
make -C "$(git rev-parse --show-toplevel)/apps/scraper" club CLUB='<New Club Name>'
```

If a match is found, the venue is a **duplicate** — hide the old record instead of
creating a new one. Write a migration that sets `visible = false` on the old club ID
and skip the INSERT below.

**3A-3. Create the Migration**

Create a Prisma migration file:

```bash
# Generate timestamp
TIMESTAMP=$(date -u +%Y%m%d%H%M%S)
MIGRATION_DIR="apps/web/prisma/migrations/${TIMESTAMP}_onboard_<snake_case_club_name>"
mkdir -p "$MIGRATION_DIR"
```

Write `migration.sql`:

```sql
-- Onboard <Club Name> (<City>, <State>)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM "clubs" WHERE name = '<Club Name>') THEN
        INSERT INTO "clubs" (
            name, address, website, scraping_url, scraper,
            visible, zip_code, timezone,
            city, state, <platform_id_column>
        )
        VALUES (
            '<Club Name>',
            '<Street Address>',
            'https://<website>',
            '<scraping_url or platform/id>',
            '<scraper_key>',
            true,
            '<zip_code>',
            '<timezone>',
            '<City>',
            '<State>',
            '<platform_id_value>'
        );
    END IF;
END $$;
```

Key rules:
- Always use `https://` for the website URL
- Use the correct IANA timezone (e.g., `America/New_York`, `America/Chicago`)
- Set `visible = true`
- Use `DO $$ BEGIN ... IF NOT EXISTS ... END $$;` for idempotency

Skip to Step 4.

### Path B: Venue-Specific Scraper (New Code Required)

For platforms that need a new scraper implementation (Tockify, Squarespace, Crowdwork,
Tixr, ThunderTix, VBO Tickets, Wix, SquadUP, TicketSource, StageTime, OpenDate,
Netlify Functions, or custom HTML):

**3B-1. Find the Reference Implementation**

Read `apps/scraper/SCRAPERS.md` for the platform section — it names the reference
scraper to copy from. Common references:

| Platform | Copy from |
|----------|-----------|
| Tockify | `venues/ice_house/` |
| Squarespace | existing Squarespace venue |
| Crowdwork | `venues/philly_improv_theater/` |
| Tixr | `venues/the_stand_nyc/` or `venues/haha_comedy_club/` |
| ThunderTix | `venues/annoyance/` |
| VBO Tickets | `venues/esthers_follies/` |
| SquadUP | `venues/sunset_strip/` |
| TicketSource | `venues/comedy_clubhouse/` |
| StageTime | `venues/comedy_corner_underground/` |
| OpenDate | `venues/sports_drink/` |

**3B-2. Create the Venue Scraper Directory**

```
apps/scraper/src/laughtrack/scrapers/implementations/venues/<venue_snake_name>/
    __init__.py
    scraper.py      — main scraper class (key = "<venue_snake_name>")
    extractor.py    — parse HTML/JSON → event objects
    data.py         — PageData dataclass (MUST be named data.py)
    transformer.py  — convert events to Show/Ticket entities
```

Read the reference implementation files first, then adapt:
- Change the `key` in `scraper.py` to match the new venue
- Update `collect_scraping_targets()` with the correct URL/API endpoint
- Adapt `extractor.py` to parse the venue's specific response format
- Update `data.py` with the correct event type imports
- `transformer.py` usually inherits from `DataTransformer` with minimal changes

**3B-3. Create the Event Entity (if needed)**

If the platform's event format differs from existing entities, create:
```
apps/scraper/src/laughtrack/core/entities/event/<venue_snake_name>.py
```

**3B-4. Register the Scraper**

Check how existing scrapers are registered/discovered. The scraper `key` must be unique
and will be stored in the `scraper` column of the clubs table.

**3B-5. Create the Migration**

Same as Path A Step 3A-2, but set `scraper = '<venue_snake_name>'` instead of a
generic scraper key.

**3B-6. Write Tests**

Create a test file following the project's test patterns (see `apps/scraper/CONTRIBUTING.md`):
```
apps/scraper/tests/scrapers/implementations/venues/<venue_snake_name>/
    __init__.py
    test_scraper.py
```

### Path C: Platform Identified but No Scraper Exists

If research confirms the real ticketing platform (e.g., TicketLeap, a niche custom API)
but the codebase has no matching scraper AND building a full Path B scraper exceeds
this task's complexity, use this hand-off pattern:

1. Write a migration that updates the club's verified metadata (address, city, state,
   zip, timezone, website, scraping_url). Point `scraping_url` at the correct platform
   URL so the follow-up task inherits it. Keep `visible=false` and leave the existing
   (broken) scraper value in place as a placeholder.
2. Create a follow-up task titled "Build <Platform> platform scraper and onboard
   <Club Name> (club <id>)". In the description, include:
   - Platform details (listing URL format, detail URL format, where the event data
     lives — e.g., `window.dataLayer.push` IDs + per-event JSON-LD).
   - A sketch of the scraper design (two-step crawl, reference implementations to copy).
   - A note that club metadata is already set and the scraper-build task only needs
     to flip `scraper` + `visible` when the scraper verifies shows.
3. Commit the metadata migration, mark the "research" criterion done, and
   `--skip-verify` the remaining conditional criteria with rationale logged via
   `tusk progress` (venue is active but scraper is deferred to the follow-up task).

## Step 4: Deploy and Verify

### 4a. Apply the Migration

`npx prisma migrate deploy` cannot run locally (see CLAUDE.md — local `.env.local` points to
localhost, not Neon). Apply the migration SQL directly using the scraper's DB connection, then
record it in the Prisma migrations table:

```bash
cd apps/scraper && .venv/bin/python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
import psycopg2

conn = psycopg2.connect(
    host=os.environ['DATABASE_HOST'],
    user=os.environ['DATABASE_USER'],
    password=os.environ['DATABASE_PASSWORD'],
    dbname=os.environ['DATABASE_NAME'],
    port=int(os.environ.get('DATABASE_PORT', '5432')),
    sslmode='require'
)
conn.autocommit = True
cur = conn.cursor()
cur.execute(open('../web/prisma/migrations/<MIGRATION_DIR>/migration.sql').read())
cur.execute('''
INSERT INTO _prisma_migrations (id, checksum, migration_name, logs, started_at, finished_at, applied_steps_count)
VALUES (gen_random_uuid(), '', '<MIGRATION_DIR>', NULL, now(), now(), 1)
ON CONFLICT DO NOTHING;
''')
conn.close()
print('Migration applied and recorded')
"
```

Replace `<MIGRATION_DIR>` with the actual migration directory name (e.g., `20260408201527_onboard_the_lost_church`).

Verify the club was inserted:

```bash
make -C "$(git rev-parse --show-toplevel)/apps/scraper" club CLUB='<Club Name>'
```

### 4b. Run a Test Scrape

```bash
cd apps/scraper && make scrape-club CLUB='<Club Name>'
```

Check the output for:
- Events extracted (non-zero count)
- Valid ticket URLs
- Comedian names parsed (if available)
- No errors or warnings

If the scraper returns **0 events**, investigate:
- Is the venue currently listing shows? (check website manually)
- Is the platform ID correct? (re-verify from Step 3)
- Is the API returning data? (test the endpoint directly — see CLAUDE.md on using
  direct HTTP calls instead of WebFetch for API inspection)

If shows are genuinely not on sale yet, note this in the task and mark the
verification criteria as blocked (same pattern as TASK-663, TASK-685, etc.).

### 4c. Commit

Commit the migration (and scraper code if Path B) on a feature branch:

```bash
git checkout -b feature/TASK-<id>-onboard-<venue-snake-name>
git add <migration files> <scraper files if any>
git commit -m "[TASK-<id>] Onboard <Club Name> (<scraper_type> scraper)"
```

## Step 5: Report Results

Present a summary:

```
Adopt Scraper Results
━━━━━━━━━━━━━━━━━━━━
Club:       <Club Name>
Location:   <City>, <State>
Website:    <URL>
Platform:   <platform name>
Scraper:    <scraper_key> (generic|venue-specific)
Club ID:    <DB id>
Shows found: <count> (or "blocked — not yet on sale")
```

Mark task criteria as done via `tusk criteria done` as each is verified.
