---
name: tour-date-club-onboarding
description: Pop the next tour_dates-only club by id and investigate how to onboard it onto a real scraper/source, including web search, venue page inspection, existing chain/source checks, and Eventbrite/Ticketmaster fallback.
allowed-tools: Bash, Read, Glob, Grep, WebSearch, WebFetch, Task, Edit, Write
---

# Tour Date Club Onboarding

Use this when asked to onboard venues discovered from comedian tour pages, process the `tour_dates` backlog, or determine the correct scraper/source for a `tour_dates`-only club.

Goal: take the next active club whose only enabled scraping source is `tour_dates`, identify its real ticket/calendar backend, and either onboard it with an existing generic scraper/chain default or produce a precise implementation task for a new scraper.

## Ground Rules

- Process exactly one club at a time unless the user explicitly asks for a batch.
- Use club `id` ascending as the queue order.
- Treat `tour_dates` as a temporary discovery placeholder, not the final scrape source.
- Do not trust plain `requests`/`urllib` fetchability checks for HTML pages. Use the scraper HTTP stack or Playwright browser fallback described in `AGENTS.md`.
- For platform decisions, read `apps/scraper/SCRAPERS.md` first; it is the local source of truth.
- For API response counts or structures, use direct Python HTTP/client calls, not summarized web fetches.
- Do not mutate DB rows until you have verified the platform and can state the exact source fields to write.
- A `tour_dates` club may be a duplicate of an existing canonical club. Always check for duplicates before onboarding a new source, and when resolving a duplicate, add verified aliases to `club_aliases` so future discovery maps the duplicate name/location to the canonical club.

## Step 1: Pop the Next Club

From `apps/scraper`, load `.env` and query the next active, visible, `tour_dates`-only club:

```bash
cd apps/scraper
set -a && source .env && set +a
.venv/bin/python - <<'PY'
import os, psycopg2, psycopg2.extras

dsn = os.environ.get("DATABASE_URL") or (
    f"postgresql://{os.environ['DATABASE_USER']}:{os.environ['DATABASE_PASSWORD']}"
    f"@{os.environ['DATABASE_HOST']}:{os.environ.get('DATABASE_PORT','5432')}"
    f"/{os.environ['DATABASE_NAME']}?sslmode=require"
)

sql = """
WITH enabled_per_club AS (
    SELECT
        ss.club_id,
        BOOL_OR(ss.platform <> 'tour_dates') AS has_non_tour_date,
        MIN(ss.created_at) FILTER (WHERE ss.platform = 'tour_dates') AS tour_date_created_at
    FROM scraping_sources ss
    WHERE ss.enabled = TRUE
    GROUP BY ss.club_id
)
SELECT
    c.id, c.name, c.address, c.city, c.state, c.website, c.chain_id,
    epc.tour_date_created_at
FROM clubs c
JOIN enabled_per_club epc ON epc.club_id = c.id
WHERE epc.has_non_tour_date = FALSE
  AND epc.tour_date_created_at IS NOT NULL
  AND COALESCE(c.visible, TRUE) = TRUE
  AND c.status = 'active'
ORDER BY c.id ASC
LIMIT 1
"""

with psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        print(dict(cur.fetchone() or {}))
PY
```

If no row is returned, report that the `tour_dates` onboarding queue is empty.

## Step 2: Snapshot Existing DB Context

Before web research, query the selected club's current source/chain context:

```sql
SELECT c.id, c.name, c.website, c.chain_id, ch.name AS chain_name
FROM clubs c
LEFT JOIN chains ch ON ch.id = c.chain_id
WHERE c.id = <club_id>;

SELECT id, platform, scraper_key, source_url, priority, enabled,
       eventbrite_id, ticketmaster_id, seatengine_id, seatengine_v3_id,
       wix_event_id, ovationtix_id, squadup_id, metadata
FROM scraping_sources
WHERE club_id = <club_id>
ORDER BY enabled DESC, priority ASC, id ASC;

SELECT csd.id, csd.chain_id, ch.name AS chain_name, csd.platform,
       csd.scraper_key, csd.priority, csd.enabled, csd.metadata
FROM clubs c
JOIN chains ch ON ch.id = c.chain_id
JOIN chain_scraping_defaults csd ON csd.chain_id = ch.id
WHERE c.id = <club_id>
ORDER BY csd.enabled DESC, csd.priority ASC, csd.id ASC;
```

If there is already an enabled non-`tour_dates` source or an enabled chain default that applies, stop and report that the club is already onboarded or chain-backed.

Also check whether the selected club duplicates an existing canonical club before doing deeper platform work. Search by normalized venue name variants, city/state, website domain, and any ticket/calendar URLs found in `tour_dates.metadata.event_urls`:

```sql
SELECT c.id, c.name, c.city, c.state, c.website, c.chain_id, c.visible, c.status,
       ss.id AS source_id, ss.platform, ss.scraper_key, ss.source_url, ss.enabled,
       ss.eventbrite_id, ss.ticketmaster_id, ss.seatengine_id, ss.seatengine_v3_id,
       ss.metadata
FROM clubs c
LEFT JOIN scraping_sources ss ON ss.club_id = c.id
WHERE c.id <> <club_id>
  AND c.status = 'active'
  AND COALESCE(c.visible, TRUE) = TRUE
  AND (
      (c.city = <city> AND c.state = <state> AND lower(c.name) LIKE <name_pattern>)
      OR lower(c.website) LIKE <website_or_domain_pattern>
      OR lower(ss.source_url) LIKE <website_or_domain_pattern>
  )
ORDER BY c.id, ss.enabled DESC, ss.priority ASC, ss.id ASC;
```

If the selected club is a duplicate:

- Verify the canonical club has a working source or chain default; do not merely match on a similar name.
- Check dependent rows (`shows`, `tagged_clubs`, `email_subscriptions`, `processed_emails`, `production_company_venues`) before deciding whether to hide, merge, or delete the duplicate.
- Add or update `club_aliases` rows for the duplicate display name(s) and city/state, pointing to the canonical `club_id`, with `verified = TRUE`. Use the table's unique key `(normalized_alias_name, normalized_city, normalized_state)` and include a concise `source` note naming the migration/task.
- Disable or annotate the duplicate `tour_dates` source only after the canonical source has been verified.

## Step 3: Find the Venue Site

Use the club name and city/state:

- Start with `"<club name>" "<city>" comedy club official website`.
- Also search `"<club name>" tickets`, `"<club name>" events`, and `"<club name>" calendar`.
- Prefer the official venue domain over aggregators.
- If the DB `website` is blank or wrong, note the candidate replacement but do not update it yet.

Open the official page and look for:

- Calendar/events page URL.
- Buy-ticket links.
- Embedded iframe/widget script URLs.
- Page-source markers and network/API URLs.

For JS-heavy widgets, use Playwright or the scraper's own browser stack rather than plain HTTP.

## Step 4: Classify the Platform

Read `apps/scraper/SCRAPERS.md` and match the page against the decision flow. Check in this order:

1. Existing chain default for the club's `chain_id`.
2. Existing generic scraper support in `apps/scraper/src/laughtrack/scrapers/implementations/`.
3. Existing venue-specific scraper that can be generalized or copied.
4. Eventbrite or Ticketmaster fallback.
5. New custom scraper needed.

Search existing implementation keys and nearby examples:

```bash
rg -n "key = \"<candidate_key>\"|scraper_key=.*<candidate_key>|platform.*<candidate_platform>" apps/scraper/src apps/scraper/scripts apps/scraper/sql
```

For platform-specific onboarding notes, use the matching section in `apps/scraper/SCRAPERS.md`.

## Step 5: Eventbrite/Ticketmaster Fallback

If the official site does not expose a known backend, check whether tickets are managed externally:

- Search: `"<club name>" "<city>" site:eventbrite.com`
- Search: `"<club name>" "<city>" site:ticketmaster.com`
- Search: `"<club name>" "<city>" site:livenation.com`

Eventbrite:

- Prefer organizer URL `https://www.eventbrite.com/o/<slug>-<organizer_id>`.
- If only event URLs are found, inspect event pages for organizer and venue IDs.
- Confirm the organizer/venue returns relevant upcoming events before recommending the source.

Ticketmaster:

- Use `TICKETMASTER_API_KEY` from `apps/scraper/.env`.
- Search Discovery API venues by club name and city/state.
- Confirm the selected venue ID has upcoming relevant events before recommending `platform='ticketmaster'`, `scraper_key='live_nation'`, and `ticketmaster_id=<id>`.

## Step 6: Decide the Onboarding Action

Use the least custom option that will scrape the venue correctly:

- **Duplicate of an existing club:** write a guarded migration that preserves or migrates dependent data as needed, hides/closes or deletes the duplicate row according to local precedent, disables/annotates the duplicate `tour_dates` source, and inserts verified `club_aliases` rows pointing duplicate names to the canonical club.
- **Chain-backed:** attach the club to an existing chain or add a chain default only if the venue truly belongs to that chain and the default fits.
- **Existing generic source:** write a migration or SQL patch that adds/enables a real `scraping_sources` row for the club.
- **Existing scraper needs copied config:** follow the pattern in `SCRAPERS.md` and nearby migrations.
- **New scraper needed:** create a tusk task or implementation plan with the detected API/page structure, sample URLs, expected fields, and tests.
- **No usable source:** document what was checked and leave the club on `tour_dates` with a follow-up task or disposition metadata if appropriate.

Do not disable the `tour_dates` source until the replacement source is verified with a successful scrape or a reviewed migration plan explicitly covers the transition.

## Step 7: Verify Before Calling It Done

For an existing scraper/source:

```bash
cd apps/scraper
make scrape-club CLUB="<club name>"
```

For fetchability checks, use the Playwright browser pattern from `AGENTS.md`, not plain `requests`.

For a new/modified scraper, run focused tests and a targeted manual scrape. If the scrape returns zero events, diagnose whether the venue really has no upcoming comedy events before treating it as a failure.

## Report Format

End with:

```markdown
Club: <id> — <name> (<city>, <state>)
Official site: <url>
Calendar/tickets URL: <url>
Detected platform: <platform or unknown>
Existing chain/source: <what exists, or none>
Duplicate/alias handling: <canonical club id/source and club_aliases changes, or none>
Recommended action: <exact DB/source/scraper change or task needed>
Verification: <commands run and result>
Open questions: <only if blocked>
```
