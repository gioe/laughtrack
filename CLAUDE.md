## StageTime Venues — Custom RSC Scraper

StageTime (stageti.me) is a Next.js ticketing platform used by venues like
The Comedy Corner Underground. Venues have a subdomain: `{slug}.stageti.me`.

**No generic scraper exists.** Build a custom venue scraper:
- `scraper = 'comedy_corner_underground'` (venue-specific key)
- `scraping_url = 'https://{slug}.stageti.me'`

**Data extraction approach:**
1. Fetch the listing page `https://{slug}.stageti.me/` — extract event slugs from
   `href="/v/{slug}/e/{event-slug}"` anchor links (BeautifulSoup).
2. For each event slug, fetch `https://{slug}.stageti.me/e/{event-slug}`.
   Event pages embed data in `self.__next_f.push([1,"..."])` RSC wire format segments:
   - JSON-decode the quoted string content
   - Split by newlines — each line is one RSC chunk (`XX:[...]` format)
   - Chunk containing `"occurrences":[` has: event name, isOpenMic, admissionType,
     occurrences[].startTime (UTC ISO), venue.timezone
   - Chunk with `"id":"event-jsonld"` has: performer names and ticket URL
     (in `dangerouslySetInnerHTML.__html` as a doubly-escaped JSON-LD string)
3. One `ComedyCornerEvent` per occurrence; skip `isOpenMic=true` and
   `admissionType='no_advance_sales'` events.

**Occurrence start times** are UTC ISO strings (`"2026-04-04T01:00:00.000Z"`).
Convert to local time via pytz: parse with `%Y-%m-%dT%H:%M:%S.%fZ`, localize to UTC,
then convert to `venue.timezone` (e.g. `"America/Chicago"`).

**Test fixtures:** RSC status fields are double-escaped in push segments. To patch
a published occurrence to cancelled in a test, use:
`html.replace('\\"status\\": \\"published\\"', '\\"status\\": \\"cancelled\\"', 1)`

**See:** `apps/scraper/src/laughtrack/scrapers/implementations/venues/comedy_corner_underground/`

## Prekindle Venues — Use Existing `json_ld` Scraper

When a venue sells tickets via **Prekindle** (`prekindle.com`), the events listing page
(`https://www.prekindle.com/events/{venue-slug}`) is server-rendered and embeds all
upcoming events as a single JSON array in a `<script type="application/ld+json">` block
with `@type=ComedyEvent`. The block may include a `wicketpath` attribute (Java Wicket
framework) which BeautifulSoup handles correctly.

**No new scraper code is needed.** Use the generic `json_ld` scraper:
- `scraper = 'json_ld'`
- `scraping_url = 'https://www.prekindle.com/events/{venue-slug}'`
  (the `{venue-slug}` appears in the venue's Prekindle events page URL)

**Rate-limiting:** Prekindle throttles rapid successive requests from the same IP —
repeated scrapes within a short window (< ~60s) return valid HTML but without the
JSON-LD block, triggering the "Page loaded but contained no JSON-LD events" warning.
This is expected under load testing or rapid review-agent runs. Nightly single-run
scrapes are unaffected. When investigating scraper reliability from logs, verify that
failures are not caused by rapid successive test runs before treating them as genuine
scraping failures.

## Humanitix Venues — Use Existing `json_ld` Scraper

When a venue sells tickets via **Humanitix** (`events.humanitix.com`), the host
page is server-rendered and embeds all upcoming events as
`<script type="application/ld+json">` blocks with `@type=Event`.

**No new scraper code is needed.** Use the generic `json_ld` scraper:
- `scraper = 'json_ld'`
- `scraping_url = 'https://events.humanitix.com/host/<slug>'`
  (the `<slug>` appears in the Humanitix host page URL)

The existing `JsonLdScraper` fetches the host page and extracts all events in
a single request — no per-event page visits needed. Ticket URLs follow the
pattern `https://events.humanitix.com/{event-slug}/tickets`.

**Note:** Humanitix has no public REST API for event listings — the host page
HTML is the only data source. No `humanitix_id` column exists; store the full
host URL in `scraping_url`.

## Ninkashi Venues — Use Existing `ninkashi` Scraper

When a venue sells tickets via **Ninkashi** (typically a subdomain like
`tickets.{venue}.com`), use the generic `ninkashi` scraper — no custom Python
code needed:
- `scraper = 'ninkashi'`
- `scraping_url = '<url_site>'` (the subdomain, e.g. `tickets.cttcomedy.com`)

**API endpoint** (no auth required):
  `GET https://api.ninkashi.com/public_access/events/find_by_url_site?url_site=<url_site>&page=1&per_page=100`

Response is a **root-level JSON array** of events. Key fields: `id`, `title`,
`starts_at` (ISO 8601 with UTC offset, e.g. `"2026-04-01T19:45:00.000-07:00"`),
`time_zone` (IANA string), `tickets_attributes` (array with `name`, `price`,
`sold_out`, `remaining_tickets`).

Ticket URL is constructed as `https://{url_site}/events/{id}`.

**Identification:** Look for a `tickets.{venue}.com` subdomain on the venue's
website. Playwright network inspection during TASK-746 identified this pattern
for Cheaper Than Therapy.

**See:** `apps/scraper/src/laughtrack/scrapers/implementations/api/ninkashi/`

## Tixr Venues — Use Existing `tixr` Scraper

When a venue's calendar page (its own website **or** a Tixr group page like
`tixr.com/groups/<slug>`) embeds Tixr event links in server-rendered HTML,
use the generic `tixr` scraper — no custom Python code needed:
- `scraper = 'tixr'`
- `scraping_url = '<venue calendar page URL>'`

The `TixrScraper` fetches the page, extracts all Tixr URLs (both short-form
`tixr.com/e/{id}` and long-form `tixr.com/groups/*/events/*-{id}`) via
`TixrExtractor`, then batch-resolves each to a `TixrEvent` via `TixrClient`.

**When to use a custom scraper instead:** If the venue's Tixr group page
triggers DataDome bot-detection (returns 403 or empty results when fetched
via `fetch_html`), use a Covina-style venue scraper that calls
`tixr_client._fetch_tixr_page(url)` instead — this uses a bare curl_cffi
session with no application headers, bypassing DataDome.

**Smoke test pattern:** venue-specific smoke tests for `tixr` scraper venues
instantiate `TixrScraper(club)`, mock `TixrScraper.fetch_html` (not
`_fetch_tixr_page`), and verify `TixrPageData` is returned with ≥1 event.

## Wix Sites with "Events Calendar" Widget — Eventbrite Backend

Some Wix-hosted venues embed the "Events Calendar" widget (inffuse.eventscalendar.co)
rather than Wix's native events app. This widget is backed by Eventbrite — the event
data comes from the Eventbrite organizer, not from a Wix API.

**Identification via Playwright network inspection:**
Look for a POST to `https://inffuse.eventscalendar.co/js/v0.1/calendar/data` and
a GET to `https://broker.eventscalendar.co/api/eventbrite/events?calendar=<id>`.
The `calendar=` parameter **is the Eventbrite organizer ID**.

**Implementation:** use `scraper='eventbrite'` with the organizer ID — no Wix access
token needed. The `EventbriteClient` routes 11-digit IDs to `/organizers/{id}/events/`
automatically.

## Scraper Smoke Tests — Ticketmaster Venues: Patch TicketmasterClient in Sync Pipeline Tests

`TicketmasterEventTransformer.transform_to_show()` instantiates `TicketmasterClient(self.club)`
on every event, and the constructor raises `ValueError` when `TICKETMASTER_API_KEY` is absent.
CI (`scraper-ci.yml`) does **not** set this env var, so the sync pipeline tests
(`test_transformation_pipeline_produces_shows`, `test_transformation_pipeline_preserves_event_name`)
will pass locally but fail in every CI run — producing 0 shows and failing the `len(shows) > 0`
assertion.

**Fix**: patch `TicketmasterClient` in the transformer module for those two tests:

```python
from unittest.mock import MagicMock, patch

mock_client = MagicMock()
mock_client.create_show.return_value = _fake_show()
with patch(
    "laughtrack.scrapers.implementations.api.ticketmaster.transformer.TicketmasterClient",
    return_value=mock_client,
):
    shows = scraper.transformation_pipeline.transform(page_data)
```

This applies to **all** `live_nation` venue smoke test files. Do not copy the unpatched
Second City pattern — it has the same bug.

**`get_data` tests also need a separate patch.** `test_get_data_returns_page_data_with_events`
and `test_get_data_returns_non_transformable_when_api_returns_empty` call `get_data()`, which
instantiates `TicketmasterClient` directly in the scraper module (not the transformer). Patching
`TicketmasterClient.fetch_events` at the class level does not prevent the constructor from running.
**Fix**: patch `TicketmasterClient` at the **scraper** module level and configure `fetch_events`
as an `AsyncMock` on the returned instance:

```python
mock_client = MagicMock()
mock_client.fetch_events = AsyncMock(return_value=[_make_api_event()])
with patch(
    "laughtrack.scrapers.implementations.api.ticketmaster.scraper.TicketmasterClient",
    return_value=mock_client,
):
    result = await scraper.get_data(api_url)
```

Two patch targets, two test groups — never mix them:
- `transformer.TicketmasterClient` → `test_transformation_pipeline_*` tests
- `scraper.TicketmasterClient` → `test_get_data_*` tests

**Event IDs in smoke tests must be fake.** Use a clearly synthetic ID like `FAKE0000COBBS001`
or `FAKE0000PLSF001` — never a real Ticketmaster event ID. Real IDs are tied to specific show
dates and look stale once the event passes. The canonical pattern is `FAKE0000<VENUE_CODE>001`
where `<VENUE_CODE>` is a short uppercase abbreviation of the venue name (e.g. `COBBS`, `PLSF`,
`2CTY`).

## Scraper Smoke Tests — Always Include `test_transformation_pipeline_produces_shows`

Every venue smoke test file (`test_pipeline_smoke.py`) **must** include a
`test_transformation_pipeline_produces_shows` test. This test catches regressions where
`can_transform()` returns `False` for the venue's event type (e.g., due to a generic type
mismatch on `DataTransformer[T]`), causing `transform()` to silently return an empty list
with no error.

```python
def test_transformation_pipeline_produces_shows():
    club = _club()
    scraper = MyVenueScraper(club)
    events = [_make_event("Show A"), _make_event("Show B")]
    page_data = MyVenuePageData(event_list=events)

    shows = scraper.transformation_pipeline.transform(page_data)

    assert len(shows) > 0, (
        "transformation_pipeline.transform() returned 0 Shows — "
        "check can_transform() and that the transformer is registered "
        "with the correct generic type"
    )
    assert all(isinstance(s, Show) for s in shows)
```

This test must be present even when other `to_show()` unit tests exist — those tests
call `event.to_show()` directly and bypass the transformer registry entirely.

## Scraper Smoke Tests — Check for Unstaged Source Changes Before Committing

Before committing a `test_pipeline_smoke.py`, run:

```bash
git status --short apps/scraper/src/
```

Unstaged source changes (e.g. a new field on a PageData class) that a test
imports will be flagged as a must_fix during code review rather than caught
pre-commit.

## Scraper Smoke Tests — Verify SCRAPING_URL Against Current Migration for Existing Venues

When writing a `test_pipeline_smoke.py` for an **existing** venue (one that already has a
migration in `prisma/migrations/`), always verify the `DOMAIN`/`SCRAPING_URL` test constants
match the venue's current production `scraping_url`. A prior migration may have updated it
(e.g., `20260319000006_fix_bushwick_scraping_url` changed Bushwick to `bushwickcomedy.com`).

Quick check:
```bash
grep -r "scraping_url" apps/web/prisma/migrations/ | grep "<venue_scraper_key>"
```

A stale domain in a test constant is a silent bug — the test passes locally but exercises a
URL that no longer matches the DB record, and will be flagged as a must_fix in code review.

## Scraper Smoke Tests — Mock Complex HTML Extractors Directly

When an extractor requires specific CSS classes or container structure (e.g.
Comedy Cellar's `set-header` divs), do NOT build a minimal HTML fixture and
pass it through the real extractor — the fixture will miss required elements
and the extractor will return `None`. Instead, patch `extract_events` directly:

```python
monkeypatch.setattr(MyExtractor, "extract_events", staticmethod(lambda *a: [fake_event]))
```

This bypasses fragile HTML construction while still exercising the full
scraper → extractor call path.

## Scraper Manual Run — Use `make scrape-club`, Not `bin/scrape`

Use `make scrape-club CLUB='<venue name>'` to run a scrape for a specific club.
`bin/scrape` does not exist — the `bin/` directory only contains `migrate` and
`cleanup-stale-scrapers`. Task criteria and next-steps that say "run bin/scrape"
should be interpreted as `make scrape-club CLUB='<name>'`.

The Makefile lives in `apps/scraper/` — always run from that directory:

```bash
cd apps/scraper && make scrape-club CLUB="Esther's Follies"
cd apps/scraper && make scrape-club CLUB="Comedy Cellar"
```

## Scraper Venue PageData — Module Must Be Named `data.py`

All venue scraper PageData modules must be named `data.py` (not `page_data.py`
or any other name). Every existing venue scraper (Gotham, St. Marks, Rockwell, etc.)
follows this convention. Importing from `.data` in `scraper.py` will fail if the
file is named differently.

```python
# In scraper.py — always import from .data
from .data import MyVenuePageData   # ✓ file is data.py
# from .page_data import ...        # ✗ breaks the import
```

## Scraper Bin Tests — Monkeypatch SCRAPER_ROOT for --apply Tests

Scripts that call `path.relative_to(SCRAPER_ROOT)` in print/display code (e.g., `delete_directory()`)
will raise `ValueError` in tests when paths are in `tmp_path`, because `tmp_path` is not under
`SCRAPER_ROOT`. Always monkeypatch `SCRAPER_ROOT` to an ancestor of your test paths:

```python
monkeypatch.setattr(_mod, "SCRAPER_ROOT", tmp_path)
```

This applies to any bin script test that uses `tmp_path` for directories that the script displays
relative to the project root.

## Scraper Documentation — Verify API Endpoints from Client Source

When writing or updating SCRAPERS.md (or any documentation about scraper API
endpoints), always read the actual client file directly:
  apps/scraper/src/laughtrack/core/clients/{platform}/client.py

Do NOT rely on explore-agent summaries for endpoint URLs — agents can conflate
platform details (e.g., Squarespace GetItemsByMonth vs. Wix paginated-events).
A 30-second file read avoids a review-cycle correction.

## Tixologi — No Public Events API (HTML Scraping Required)

Tixologi (tixologi.com) is a ticketing platform used by Laugh Factory Reno
(partner ID 690).  The Tixologi **public** API has no events endpoint:

- `GET https://api-v2.tixologi.com/public/users/partners/690` → partner metadata
  (name, punchup_id UUID) — works without auth
- `GET https://api-v2.tixologi.com/public/users/partners/690/events` → 401 Unauthorized
- `GET https://api-v2.tixologi.com/public/users/partners/690/embed-script` → embed JS
  (looks for `.tixologi-button[data-event-id]` DOM elements, but LF Reno does NOT
  use this — it uses a custom `.reno-ticket-button[data-punchupid]` system)

**Workaround**: Scrape shows from the Laugh Factory CMS page
(`https://www.laughfactory.com/reno`).  Shows are server-rendered as
`.show-sec.jokes` divs.  Ticket links follow the pattern:
  `https://www.laughfactory.club/checkout/show/{punchup_id}`

The `TixologiClient` fetches the CMS HTML page; `LaughFactoryRenoEventExtractor`
parses the `.show-sec.jokes` divs (date span, timing span, ticket anchor, title h4,
figcaption comedian names).  See `apps/scraper/src/laughtrack/core/clients/tixologi/`.

**Date format**: The `.shedule span.date` contains a non-breaking space (`\xa0`)
between the weekday abbreviation and the "Mon DD" string, e.g. `"Wed\xa0Apr 10"`.
Strip the weekday prefix on `\xa0`, then infer year (current if future, else next).

## Tixr `--{id}` URL Format — No JSON-LD, Won't-Fix

Tixr uses two distinct SSR page templates:

1. **Single-dash format** (`/events/{slug}-{id}`): Server-renders a full JSON-LD
   `@type=Event` block. `TixrClient.get_event_detail_from_url()` extracts it correctly.
2. **Double-dash format** (`/events/{slug}--{id}`): The SSR HTML only embeds
   `window.pageSetup = { eventId: {id} }` — no JSON-LD, no date, no performers.
   The event data is loaded client-side from `https://www.tixr.com/api/events/{id}`.

The `www.tixr.com/api/events/{id}` endpoint requires a DataDome CAPTCHA-solved JS
session (cookie set by running JS challenge on page load). curl_cffi's Chrome
impersonation passes the TLS fingerprint check for page HTML fetches but NOT for
the API endpoint — even with the DataDome cookie from a prior page fetch, the API
returns a CAPTCHA redirect (HTTP 403).

**Won't-fix**: No practical fallback without running a full Playwright browser per
event (not feasible for nightly batch scrapers). The `--{id}` events are silently
skipped. `TixrClient` logs a specific warning distinguishing these from genuine
extraction failures:
> "Tixr special-event page (--ID format) has no JSON-LD; data requires JS execution — skipping: {url}"

Affects: Laugh Factory Covina and potentially other Tixr venues.

## rhp-events WordPress Plugin — All Pagination URLs Serve Identical Content

The `rhp-events` WordPress plugin (used by venues like The Comedy & Magic Club)
emits `/events/page/2/`, `/events/page/3/`, etc. links in its HTML, but every
pagination URL returns the **same set of events** as page 1. Do NOT implement
multi-page pagination for venues using this plugin — only fetch the base
`/events/` URL. Deduplication via upsert handles accidental double-fetches, but
unnecessary pages waste HTTP requests.

Identification: look for CSS classes `rhpSingleEvent`, `eventWrapper`, and
`rhp-event__title--list` in the page HTML.

**Single-show page quirk**: The `class = "eventStDate"` attribute on
single-show detail pages uses spaces around `=` (i.e. `class = "..."`, not
`class="..."`). Regex patterns targeting class attributes on these pages must
use `class\s*=\s*"` rather than `class="` to match correctly.

## Playwright MCP — Chrome Already Open Conflict

When the Playwright MCP browser fails with:
  "Opening in existing browser session" / process exits immediately

Chrome is already running with a conflicting profile. Options:
1. Close Chrome manually, then retry `browser_navigate`.
2. Fall back to WebFetch if the page is server-rendered (not a JS widget).
   Playwright is only needed when WebFetch returns misleading/empty results —
   e.g., a 403, missing API calls, or content that requires JS execution.

The Playwright pattern below is specifically for JS-heavy embedded widgets
(Crowdwork, SeatGeek, Wix). For standard HTML pages, WebFetch is sufficient.

## Scraper Implementation — JS-Rendered Pages Returning HTTP 200 with Shell Content

When a ticketing page returns **HTTP 200** but only a JavaScript shell (no event rows in
the HTML), `BaseScraper.fetch_html()` will NOT trigger the automatic Playwright fallback —
that fallback only activates on 403 / empty response / bot-block signatures. The scraper
will silently extract zero events with no error.

**Identification:** curl_cffi returns 200 with a large HTML payload (~100–200KB) but
BeautifulSoup finds no event containers. Playwright browser inspection shows the event rows
populated after DOMContentLoaded — they are injected by JS, not server-rendered into the
initial payload.

**Implementation pattern:** override `get_data()` and add a `_fetch_html_with_js()` method
that uses the shared `_get_js_browser()` singleton — never instantiate `PlaywrightBrowser()`
directly (it leaks a Chromium process on every call):

```python
async def _fetch_html_with_js(self, url: str) -> Optional[str]:
    try:
        from laughtrack.foundation.infrastructure.http.client import _get_js_browser
        browser = _get_js_browser()
        if browser is None:
            Logger.warn(f"MyScraper: Playwright unavailable for {url}", self.logger_context)
            return None
        return await browser.fetch_html(url)
    except Exception as e:
        Logger.warn(f"MyScraper: Playwright fetch failed for {url}: {e}", self.logger_context)
        return None

async def get_data(self, url: str) -> Optional[MyPageData]:
    html = await self._fetch_html_with_js(url)
    if not html:
        return None
    events = MyExtractor.extract_events(html)
    ...
```

**Note on wait strategy:** `PlaywrightBrowser` uses `wait_until='domcontentloaded'`. If event
rows are server-side rendered into the initial JS bundle (common with AudienceView/Theatre
Manager), this is sufficient — verify with a live scrape. Only use `networkidle` if events
are loaded via a post-DOMContentLoaded XHR.

**Playwright install:** ensure Chromium is available before the first scrape:
```bash
cd apps/scraper && .venv/bin/playwright install chromium
```

## Venue Scraper Discovery — Playwright Network Inspection for JS-Heavy Sites

When a venue's show listing is powered by a JavaScript widget (e.g., embedded
Fourthwall/Crowdwork, SeatGeek, or similar), WebFetch may return misleading
results (e.g., claiming a domain blocks 403, or missing the actual API calls).
Use Playwright browser navigation + `browser_network_requests` instead:

1. Navigate to the venue homepage with `browser_navigate`.
2. Wait 2–3 seconds for JS to execute (`browser_wait_for time: 3`).
3. Capture `browser_network_requests (includeStatic: false)`.
4. Look for non-static, non-analytics API calls — the show-data API is usually
   a GET to a JSON endpoint that returns event data.

This pattern discovered the PHIT Crowdwork API:
  `https://crowdwork.com/api/v2/{theatre}/shows`
where `{theatre}` comes from a `data-theatre` attribute on the embed script tag.

## Loading Extension-Less Bin Scripts in Tests — Use SourceFileLoader

`importlib.util.spec_from_file_location()` returns `None` for files without a
`.py` extension (e.g. `bin/migrate`). Use `SourceFileLoader` directly instead:

```python
import importlib.machinery, importlib.util

loader = importlib.machinery.SourceFileLoader("bin_migrate", str(_BIN_PATH))
spec   = importlib.util.spec_from_loader("bin_migrate", loader)
mod    = importlib.util.module_from_spec(spec)
loader.exec_module(mod)
```

Do NOT use `spec_from_file_location(name, path)` for extension-less scripts —
it silently returns `None`, causing `AttributeError` on `spec.loader`.

## React SSR `initial*` Props — Seed useState, Don't OR with State

When a Server Component passes an `initial*` value (e.g. `initialZipCapTriggered`) to a Client
Component that tracks derived state, always seed `useState(initialValue)` — never combine the
prop with mutable state via `||` in render:

```tsx
// ✗ Wrong — initialProp never changes after mount, so the hint permanently stays on
const showHint = initialZipCapTriggered || zipCapTriggered;

// ✓ Correct — seed useState with the initial value; state is updated by subsequent fetches
const [zipCapTriggered, setZipCapTriggered] = useState(initialZipCapTriggered ?? false);
```

This applies to any `useInfiniteSearch`-style hook that accepts an `initial*` option:
pass the SSR value into the hook so it can seed its own state, reset on param change,
and overwrite on each fetch — rather than leaving a static prop to dominate the render.

## Makefile Multi-line Python — Use printf Pipe, Not -c with Backslash Continuations

Make collapses backslash-continued lines into a single line before passing them to the shell.
This means any Python with indented blocks (`with`, `if`, `for`, `def`) **cannot** be written
via `-c "line1 \\\n    line2"` — it produces a `SyntaxError` at runtime.

Use `printf '%s\n'` piped to the Python binary instead:

```makefile
# ✗ Wrong — Make collapses continuations; 'with' block becomes one unindented line
	@$(PYTHON) -c "\
import sys; ...; \
with get_connection() as conn: \
    with conn.cursor() as cur: \
        cur.execute(...)"

# ✓ Correct — printf emits a real newline per argument; indentation is preserved
	@printf '%s\n' \
		'import sys; ...' \
		'with get_connection() as conn:' \
		'    with conn.cursor() as cur:' \
		'        cur.execute(...)' \
		| $(PYTHON)
```


## Scraper `bin/migrate` — Assemble DATABASE_URL from .env Components Locally

`bin/migrate` requires a full `DATABASE_URL` env var, but `apps/scraper/.env` stores
the connection as individual components (`DATABASE_HOST`, `DATABASE_USER`,
`DATABASE_PASSWORD`, `DATABASE_NAME`, `DATABASE_PORT`).  When `DATABASE_URL` is not
set, assemble it from components and pass it inline:

```bash
cd apps/scraper && DATABASE_URL="postgresql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT:-5432}/${DATABASE_NAME}?sslmode=require" \
  .venv/bin/python bin/migrate
```

Or with a one-liner using Python to read the .env:

```bash
cd apps/scraper && DATABASE_URL=$(python3 -c "
from dotenv import dotenv_values
v = dotenv_values('.env')
print(f\"postgresql://{v['DATABASE_USER']}:{v['DATABASE_PASSWORD']}@{v['DATABASE_HOST']}:{v.get('DATABASE_PORT','5432')}/{v['DATABASE_NAME']}?sslmode=require\")
") .venv/bin/python bin/migrate
```

## Scraper Venue Scrapers — Test Concurrent Shows for Multi-Room Venues

When scraping a venue with multiple rooms (e.g., Main Room, Belly Room, Original Room),
always include a test that exercises **two shows starting at the same time in different
rooms**.  A dedup bug that keys on date/time only — rather than the full unique show
identifier — will silently drop one show with no error.

```python
# Example: two concurrent shows at 8 PM in different rooms
async def test_concurrent_shows_same_time_different_rooms(monkeypatch):
    html = _day_html([
        {"slug": "2026-04-01t200000-0700-show-a", "title": "Show A", "room": "Main Room", ...},
        {"slug": "2026-04-01t200000-0700-show-b", "title": "Show B", "room": "Belly Room", ...},
    ])
    result = await scraper.get_data(url)
    assert len(result.event_list) == 2, "Both concurrent shows must be extracted"
```

This applies to any extractor that uses a set or dict to deduplicate extracted events.
Always use the full unique show identifier as the dedup key — not just the datetime portion.

## Scraper Entity `from_dict()` — Test Compact Time/Date Formats Upfront

When implementing `from_dict()` for a scraper entity that normalizes time or date
strings, write unit tests for compact formats (e.g., `"9PM"`, `"11AM"` — no colon
or space separator) **before** running a live scrape. Sites frequently store time
data in non-standard forms that only surface when hitting the real endpoint; a unit
test for the normalization function catches this without a round-trip to production.

```python
# Example: always test both canonical and compact forms
def test_compact_time_normalised():
    html = _make_rsc_html([_show(time="9PM")])
    events = MyExtractor.extract_shows(html)
    assert events[0].time == "9:00 PM"
```

## Scraper Alerting Tests — Mock MonitoringConfig

Any test that exercises `_check_and_alert` (or any method that calls
`MonitoringConfig.default()` internally) must mock `MonitoringConfig.default()`
— otherwise the test will silently pass or fail depending on whether Discord is
configured in the local environment.

Pattern:
```python
mock_config = MagicMock()
mock_config.get_configured_channels.return_value = ["discord"]
mock_config.is_discord_configured.return_value = True
mock_config.discord_webhook_url = "https://discord.example/webhook"
with patch('laughtrack.infrastructure.config.monitoring_config.MonitoringConfig') as MockConfig:
    MockConfig.default.return_value = mock_config
    svc._check_and_alert(summary)
```

## Scraper pytest PATH — Pre-existing Failure Checks

`pytest` is not in PATH in the scraper project. When running pre-existing failure checks
in `apps/scraper/`, use the venv-local binary with an absolute path:

```bash
cd /Users/mattgioe/Desktop/projects/laughtrack/apps/scraper && .venv/bin/pytest --tb=no -q
```

Do not use `python3 -m pytest` — it also fails without venv activation.

**`tusk commit` test context:** `tusk commit` runs its test suite as `cd apps/scraper && python3 -m pytest`.
When reproducing a `tusk commit` test failure manually, always run from `apps/scraper/` — not from
the repo root. Running `python3 -m pytest` from the repo root uses `apps/scraper/` as a path prefix,
which doubles it in collection paths and produces spurious errors (e.g., 122 errors instead of 0).

## Creating New Files — Always Use Absolute Paths or the Write Tool

When creating new files (e.g., `__init__.py`, test stubs, migration files), always use either:
- The **Write tool** with an absolute `file_path` argument, or
- `touch /absolute/path/to/file` in Bash

Never use `touch relative/path` when the shell's CWD might be a subdirectory (e.g., `apps/scraper/`).
Using a path like `touch apps/scraper/tests/...` from within `apps/scraper/` silently creates the file
at `apps/scraper/apps/scraper/tests/...` — the doubled path is invisible until a later step fails.

## Wix Events Scraper — Finding the Events Widget compId

When onboarding a new Wix venue, the events widget `compId` is NOT in the page
source directly. Find it via Playwright browser evaluation:

1. Navigate to the venue homepage in Playwright.
2. Run this JS to walk up from an event's "More info" button to its `comp-` container:

```js
(() => {
  const btn = document.querySelector('[data-hook^="more-info-link-"]');
  let el = btn;
  const ids = [];
  while (el && el !== document.body) {
    const id = el.id || el.getAttribute('data-comp-id') || '';
    if (id.startsWith('comp-')) ids.push({ id, cls: el.className.substring(0, 60) });
    el = el.parentElement;
  }
  return ids;
})()
```

3. The innermost `comp-xxxx` result is the events widget compId. Use it as `compId=<value>`
   in the `collect_scraping_targets()` params.

Note: `categoryId` is NOT required if the venue has no Wix event categories configured.
Applying a Bushwick-specific `categoryId` to a different Wix site returns HTTP 400.

## Venue Onboarding — Always Use HTTPS for Website URL

When writing a migration for a new venue, always use `https://` for the `website`
column — even if the task description or source page shows `http://`. Most modern
venues serve over HTTPS, and storing `http://` causes a redirect (or mixed-content
warning) in production.

Quick check before writing the migration:
```bash
curl -sI https://www.example.com | head -1   # should return 200, not 301
```

The migration runs before code review; a stale `http://` URL requires a corrective
UPDATE migration that cannot be merged until after the original one lands.

## Ticketmaster Scraper — 0 Events Diagnosis

When a Ticketmaster-backed scraper returns 0 events, the first thing to check is
whether the stored `ticketmaster_id` is the correct **Discovery API venue ID** (format:
alphanumeric, e.g. `KovZ917ARvk`) — NOT a numeric ID from another system.

Verify by searching the Discovery API directly:
```bash
curl -s "https://app.ticketmaster.com/discovery/v2/venues.json?apikey=<KEY>&keyword=<venue name>&countryCode=US" | python3 -c "import sys,json; [print(v['id'], v['name']) for v in json.load(sys.stdin).get('_embedded',{}).get('venues',[])]"
```

Only investigate `classificationName` filters *after* confirming the venue ID returns
events at all (query without any classification filter first).

## Eventbrite Scraper — Organizer ID vs Venue ID

When onboarding a new Eventbrite venue, check whether the Eventbrite ID is a
**venue ID** (typically 8–9 digits, e.g. `253402413`) or an **organizer ID**
(typically 11 digits, e.g. `30460267696`).

The `eventbrite_id` field stores both types. The `EventbriteClient` tries
`/venues/{id}/events/` first; if that returns 404 (None), it automatically falls
back to `/organizers/{id}/events/`.

**Finding the ID:**
- Organizer ID: from the Eventbrite organizer page URL —
  `https://www.eventbrite.com/o/<slug>-<organizer_id>`
- Venue ID: inspect an individual event's JSON — look for `"venue_id"` in the
  page source or Eventbrite API response.

**Migration `scraping_url`:** Always use the full organizer URL including the slug:
  `'https://www.eventbrite.com/o/<slug>-<organizer_id>'`
not just `'https://www.eventbrite.com/o/<organizer_id>'` — the slug is required
for consistency with existing venues.

**For multi-location chains:** guessing the organizer page URL using a known
sibling location's ID always redirects to the primary organizer. Instead:
1. Fetch the venue's show listing page (e.g. `laughfactory.com/long-beach`).
2. Grab any Eventbrite event ID from the embedded widget JS
   (look for `eventId: '<digits>'` in the page source).
3. Fetch `https://www.eventbrite.com/e/<event_id>` — the organizer URL
   (`/o/<slug>-<organizer_id>`) appears in the page data.

**Diagnosis:** If a scrape returns 0 events with a 404 warning on the venues
endpoint, the stored ID is likely an organizer ID — but the auto-fallback should
handle it transparently. Verify by checking the Eventbrite URL format.

## SeatEngine v3 Platform — Identifying UUID-Based Venues

When onboarding a new SeatEngine venue, check the subdomain before scanning
numeric IDs. The `v-{uuid}.seatengine.net` subdomain pattern (e.g.
`v-cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3.seatengine.net`) means the venue
is on the **v3 platform** — a GraphQL API with UUID venue identifiers.
Scanning numeric IDs 1–700 will find nothing.

**Identification checklist:**
1. Check the page footer for "Powered by Seat Engine" + the banner/contact link.
2. If the linked domain matches `v-*.seatengine.net` → v3 platform (UUID).
3. If there is no `v-` subdomain → v1 platform (numeric ID, REST API).

**v3 setup:** use `scraper='seatengine_v3'` and store the UUID in `seatengine_id`.
The venue UUID is in the page's JSON-LD `<script>` as `"identifier": "..."`.

**v1 setup:** use `scraper='seatengine'` and store the numeric ID in `seatengine_id`.
Use `seatengine_national` to discover v1 venue IDs via enumeration.

**Classic setup:** some SeatEngine venues use the legacy HTML-rendered platform
(`cdn.seatengine.com` assets, domains like `*.seatengine-sites.com` or
`*.seatengine.com/calendar`). These do **not** respond to the REST API — use
`scraper='seatengine_classic'` with `scraping_url` pointing to the events page.
The numeric venue ID (for `seatengine_id`) is embedded in the logo URL:
`https://files.seatengine.com/styles/logos/{id}/original/` — check the page
source for this pattern rather than scanning via `seatengine_national`.
Identification: `cdn.seatengine.com/assets/application` in the page's `<script>`
tags (vs. `cdn-new.seatengine.com` for v1/v3).

## curl_cffi + DataDome — Header Fingerprint Debugging

When a curl_cffi request with `impersonate='chrome124'` succeeds with no custom headers
but returns 403 with your application headers, DataDome is detecting a specific header
combination. The trigger is never a single header — it's a combination (commonly
`Accept-Language + Cache-Control + Pragma` together).

**Diagnostic approach:**
1. Test with no headers → confirm 200
2. Binary search: split your header dict in half and test each half
3. Narrow down to the triggering combo (usually 2–3 headers together)

**Fix pattern:** bypass `BaseApiClient.fetch_html` (which always sends `self.headers`)
and use a bare `AsyncSession.get(url)` — curl_cffi's impersonation fingerprint alone
is enough and does not trigger DataDome:

```python
async with AsyncSession(impersonate=self._get_impersonation_target(url)) as session:
    response = await session.get(url)  # no extra headers
```

Note: `BaseApiClient.fetch_html(headers=None)` falls back to `self.headers` (via
`headers or self.headers`) — passing `None` or `{}` both result in API headers being
sent. A separate fetch method is needed to send zero application headers.

## Tixr Venue Scrapers — Short URL Format

Tixr event pages appear in two URL formats:

1. **Long form**: `https://www.tixr.com/groups/{group}/events/{slug}-{id}`
   (e.g., The Stand links use this format)
2. **Short form**: `https://tixr.com/e/{id}`
   (e.g., HAHA Comedy Club links use this format)

`TixrClient.get_event_detail_from_url()` handles **both formats** transparently —
curl_cffi follows the redirect from the short URL to the full event page, then
extracts JSON-LD structured data. No redirect pre-resolution is needed.

When writing an extractor for a new Tixr venue, check which format its calendar
page uses. The short form regex is: `r"https?://(?:www\.)?tixr\.com/e/(\d+)"`.
The long form regex (used by The Stand) is: `r"https?://[^\s\"]*tixr\.com/[^\s\"]*/events/[^\s\"]*"`.

## Squarespace Venues — GetItemsByMonth API Pattern

When onboarding a venue whose site is built on Squarespace, event data is served by:
  `GET /api/open/GetItemsByMonth?month=MM-YYYY&collectionId=<id>`

**Key non-obvious details:**
1. The response is a **JSON array** at the root level (`[{...}, ...]`), not a dict.
   `fetch_json()` will return a `list` — handle accordingly in the extractor.
2. The `collectionId` may be in the SSR HTML: check `Static.SQUARESPACE_CONTEXT`
   in the page source — WebFetch on the events page often includes it embedded as
   a JSON blob. If not found there, fall back to Playwright network inspection:
   navigate to the events page, wait 3s, then capture `browser_network_requests`
   and look for a `GetItemsByMonth` call.
   **Two-collection trap:** Some Squarespace sites have a calendar-block collection
   (type 10, e.g. `/shows`) separate from the actual event-items collection
   (e.g. `/all-shows`). If `GetItemsByMonth` returns `[]` for the ID found on the
   listing page, fetch an individual event's page (`/all-shows/<slug>`) and read
   its `Static.SQUARESPACE_CONTEXT` — the `collection.id` there is the correct ID
   to use in the scraping URL.
3. The `crumb` query parameter seen in browser requests is **not required** for the
   `/api/open/` endpoint — omit it in the scraper.
4. The API only returns events for one calendar month. The scraper must iterate over
   the current month + N months ahead to collect upcoming shows.
5. Each event's `startDate` and `endDate` are Unix timestamps in **milliseconds**.
6. Ticket URLs: Squarespace venues often use embedded ticketing widgets (e.g.,
   SquadUp). There is no external ticket URL — use the event's `fullUrl` (prepend
   the base domain) as the show page URL and ticket fallback.

**Identification:** `WebFetch` on the events page returns a Squarespace HTML shell
with no event data (JavaScript-rendered). When `browser_network_requests` shows a
`GetItemsByMonth` call, the venue is on Squarespace.

## Tockify Calendar Venues — API Discovery and Event Data Structure

When a venue's show listing is powered by a **Tockify** embedded calendar widget,
the event data is available via the Tockify REST API — no Playwright needed after
initial discovery.

**Identification:** `browser_network_requests` will show a GET to
  `https://tockify.com/api/tagoptions/<calname>`
The `<calname>` is the venue's Tockify calendar identifier (e.g., `theicehouse`).

**API endpoint:**
  `GET https://tockify.com/api/ngevent?calname=<calname>&max=200&startms=<now_ms>`

**Key response fields per event:**
- `eid.uid` — unique event identifier
- `content.summary.text` — event title
- `when.start.millis` — start timestamp in **milliseconds** (not seconds)
- `when.start.tzid` — timezone string (e.g., `"America/Los_Angeles"`)
- `content.customButtonLink` — ticket URL (often `embed.showclix.com/event/...`)
- `content.tagset.tags.default[0]` — room name (e.g., `"California-Room"`)

**URL normalization:** `embed.showclix.com/event/slug` → `www.showclix.com/event/slug`

**Pagination:** `metaData.hasNext` signals more results. Use `max=200` for single-request
fetches; add `startms=<now_ms>` (current Unix milliseconds) to filter to upcoming events only.

## Scraper Codebase Scope — src/ and web/ Both Count

When auditing scraper methods for unused/dead code, always search **both**:
- `apps/scraper/src/` — core library code
- `apps/scraper/web/` — companion Flask/FastAPI tools (e.g., `seatengine_api_tool/`)

Searches scoped only to `src/` will miss callers in `web/` and produce false "unused" findings.

```bash
# ✗ Wrong — misses web/ callers
grep -r "fetch_venue_details" apps/scraper/src/

# ✓ Correct — full scraper scope
grep -r "fetch_venue_details" apps/scraper/src/ apps/scraper/web/
```

## Scraper Logger — Context Dict Not Visible in Console Output

`Logger.warn(message, context_dict)` passes `context_dict` as `extra` to Python's
logging module. The console format string is:

    %(levelname)s | ... | %(message)s

Extra fields are **NOT** rendered — they are silently dropped at the terminal.
Always embed key debugging info directly in the message string:

```python
# ✗ Wrong — key/class names invisible in console output
Logger.warn("Duplicate key", {"key": k, "kept": kept_cls, "ignored": ignored_cls})

# ✓ Correct — all info in the message itself
Logger.warn(f"Duplicate key '{k}': keeping {kept_cls}, ignoring {ignored_cls}")
```

## VCR Cassette Refresh — Instagram / TikTok Social Tests

Cassette tests in `apps/scraper/tests/core/entities/test_social_refresh_vcr.py`
use `record_mode="none"`, which replays pre-recorded HTTP responses. When Instagram
or TikTok changes their API schema, cassettes must be re-recorded.

**Prerequisites:** Run locally (not from CI/cloud). Both platforms block datacenter
IPs. No extra credentials are needed for these public endpoints, but a residential
IP or VPN may be required if your network is flagged.

**Steps:**
1. Change `record_mode` in the `_vcr` instance from `"none"` to `"new_episodes"`.
   To force a full re-record of a specific cassette, delete its YAML from
   `tests/core/entities/cassettes/` first.
2. Run: `cd apps/scraper && python -m pytest tests/core/entities/test_social_refresh_vcr.py -v`
3. Review `git diff tests/core/entities/cassettes/` — confirm changed keys match
   the known schema update. Unexpected changes (redirects, auth challenges) should
   be investigated before committing.
4. Reset `record_mode` back to `"none"`.
5. Re-run tests to confirm replay-only mode passes, then commit the cassette YAMLs:
   `git add tests/core/entities/cassettes/ && git commit -m "Update VCR cassettes: <reason>"`

## Prisma orderBy Field Names — Verify Against Schema

Invalid field names in `orderBy` arrays cause `PrismaClientKnownRequestError` at runtime
(not a compile-time error), because helpers like `getGenericClauses` return loosely-typed
objects rather than `Prisma.*OrderByWithRelationInput`. Before adding a field to any `orderBy`
clause, verify it exists on the target model in `apps/web/prisma/schema.prisma`.

This applies equally to tiebreaker entries — they receive no extra type-checking:
```ts
// ✗ Wrong — Show has no totalShows field; crashes at runtime
orderBy: [{ popularity: "desc" }, { totalShows: "desc" }, { name: "asc" }]

// ✓ Correct — all fields exist on Show
orderBy: [{ popularity: "desc" }, { name: "asc" }]
```

## Prisma Select Consts — Avoid `new Date()` at Module Level

Never include `new Date()` in a module-level `as const` Prisma select object (e.g., inside a
`where: { date: { gt: new Date() } }` filter). The date is captured once at server startup,
not per request — causing stale date filters over long-lived server processes.

Instead, build the select object inside the query function body so `new Date()` is evaluated
fresh per request:

```ts
// ✗ Wrong — stale after server startup
const SELECT = { _count: { select: { items: { where: { date: { gt: new Date() } } } } } } as const;

// ✓ Correct — fresh per request
function buildSelect() {
    return { _count: { select: { items: { where: { date: { gt: new Date() } } } } } } as const;
}
```


## Prisma DIRECT_URL — Migration-Only, Not a Runtime Dependency

`DIRECT_URL` in `schema.prisma` (`directUrl = env("DIRECT_URL")`) is consumed
exclusively by the Prisma migration CLI (`prisma migrate deploy/dev`). The runtime
`PrismaClient` (and the `@prisma/adapter-neon` Pool) use only `DATABASE_URL`.

Do NOT add a module-level guard for `DIRECT_URL` in `lib/db.ts` or any other
runtime module — it will crash app servers and CI build jobs in environments
that run the app but not migrations.

## Prisma Interactive Transactions (Neon Serverless)

`db.$transaction(async (tx) => { ... })` **works correctly** with this project's Neon setup.
The project uses `@prisma/adapter-neon` with `@neondatabase/serverless` Pool (WebSocket
protocol), which connects directly to the Neon compute endpoint — not through PgBouncer.
The PgBouncer transaction-mode limitation (which blocks interactive transactions) does NOT
apply here.

When setting a specific isolation level, use the Prisma enum:
```ts
db.$transaction(async (tx) => { ... }, {
    isolationLevel: Prisma.TransactionIsolationLevel.RepeatableRead,
})
```

## Prisma Migrations

`prisma migrate dev` **cannot be run locally** in this project for two reasons:
1. The local PostgreSQL database is always empty (no tables); the real data lives in Neon serverless.
2. The shadow database validation fails on migration `20260308000000_set_email_scraper_fields` which contains a data-dependent operation requiring "Gotham Comedy Club" to exist.

**Workaround for new migrations**: Write the migration SQL manually, create the migration directory under `prisma/migrations/<timestamp>_<name>/migration.sql`, and commit both the schema and the migration file. The migration will be applied to the real DB via `prisma migrate deploy` in the deployment environment.

**After deploying UPDATE migrations**: `prisma migrate deploy` exits 0 even when a WHERE clause matches 0 rows — always verify the row count was non-zero after applying any migration that uses `UPDATE ... WHERE ...`. Query the DB or check the scraper behavior immediately after deploy to confirm the update took effect.

## Vitest Route Tests — Mocking the rateLimit Chain

Any route test that imports a handler using `@/lib/rateLimit` will transitively
load `@/auth` → `next-auth` → `next/server` (without .js), which fails in Node ESM.
Fix by adding this mock before the route import:

```ts
vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() => ({ allowed: true, limit: 100, remaining: 99, resetAt: 0 })),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { publicRead: {}, publicReadAuth: {} },
    rateLimitHeaders: vi.fn(() => ({})),
    rateLimitResponse: vi.fn(),
}));
```

## Vitest Route Tests — Auth/Authz Coverage

When writing tests for an auth-required route, always include at minimum:
- A test where `auth()` returns `null` → expect 401
- A test where `session.profile` is absent → expect 422
- A test where a user-scoped resource is requested with a mismatched userId → expect 403

Also: `mockAuth.mockResolvedValue(null as any)` — the `as any` cast is required because
`auth` is typed as `NextMiddleware`, which does not accept `null` directly.

## Public GET Routes — Rate Limiting

Use `applyPublicReadRateLimit(request, "<route-prefix>")` for all public GET API routes.
It automatically grants higher limits to authenticated users (keyed by user ID) vs anonymous
callers (keyed by IP), consistent with every other public GET route in the codebase.
Do NOT call `checkRateLimit` with `RATE_LIMITS.publicRead` directly in route handlers.

Also note: when mocking `@/lib/rateLimit` in Vitest, export `applyPublicReadRateLimit` as well:
```ts
applyPublicReadRateLimit: vi.fn(() => Promise.resolve({ allowed: true, limit: 60, remaining: 59, resetAt: 0 })),
```

## Python Test Directory Naming

Venue scraper test directories (under `tests/scrapers/implementations/venues/<venue>/`)
**must** have an `__init__.py`. Every existing venue directory has one; without it pytest
throws `import file mismatch` when multiple `test_pipeline_smoke.py` files exist across
venues. Always create it (empty is fine) alongside the test file.

Do NOT add `__init__.py` to test directories whose path segments match Python stdlib
module names OR source package names (e.g., a directory named `email/` or `scripts/`
under `tests/`). pytest's rootdir-based import mode works without `__init__.py`; adding
it causes the test package to shadow the real package, producing `ModuleNotFoundError`
at collection time for any test that imports from that package.

Also check for same-name collisions across test subtrees before adding `__init__.py`.
If two directories in different parts of `tests/` share the same leaf name (e.g.
`tests/core/clients/ticketmaster/` and `tests/scrapers/.../api/ticketmaster/`), adding
`__init__.py` to both causes pytest to assign the same package name `ticketmaster` to
both → `ModuleNotFoundError: No module named 'ticketmaster.test_pipeline_smoke'` in
the full suite. Fix: leave the second directory without `__init__.py`. If the missing
`__init__.py` would cause an `import file mismatch` collision, add `__init__.py` only
to the *other* directories involved in the collision (e.g. the `*_national` sibling).

## Testing RateLimiter Delay Calculations

When patching `random.uniform` in tests for `_calculate_anti_detection_delay`,
use `side_effect=lambda a, b: a` (returns the lower bound) rather than
`return_value=0.0`. The `return_value` form ignores the distribution bounds
entirely — so `min_delay=2.0` still produces `base=0.0`. Combined with the
`max(delay, 1.0)` floor, this makes all zero-min_delay configs produce 1.0,
masking multiplier effects:

```python
# Wrong — return_value ignores min_delay/max_delay args
with patch("...random.uniform", return_value=0.0): ...

# Correct — returns lower bound; base = min_delay, jitter = -0.5
with patch("...random.uniform", side_effect=lambda a, b: a): ...
```

## Tailwind Content Array — New Directories Under apps/web/ui/

When creating a new subdirectory under `apps/web/ui/` (e.g. `ui/util/`, `ui/hooks/`),
add a matching glob to the `content` array in `apps/web/tailwind.config.ts`:

    "./ui/<new-dir>/**/*.{js,ts,jsx,tsx}"

Without this, Tailwind's JIT purger will strip all classes from files in that directory
in production builds.

## Scraper Test Module Stubs — Use sys.modules.setdefault()

When writing a `_stub()` helper in scraper test files to register fake modules,
always use `sys.modules.setdefault(name, m)` — NOT `sys.modules[name] = m`.
Direct assignment overwrites any real package already loaded, causing test-ordering
failures: tests that run after the stub file see a plain ModuleType instead of the
real package, producing errors like "No module named 'laughtrack.foundation.models'".

```python
# Wrong — overwrites real packages loaded by earlier tests
def _stub(name, **attrs):
    m = ModuleType(name)
    sys.modules[name] = m   # ← always clobbers
    return m

# Correct — safe; skips if the real package is already registered
def _stub(name, **attrs):
    m = ModuleType(name)
    sys.modules.setdefault(name, m)   # ← no-op when already present
    return m
```

## Scraper Test Stubs — as_package=True Requires Real __path__

When a `_stub()` helper supports `as_package=True`, setting `__path__ = []` (empty list)
causes the same submodule-blocking problem as a plain module without `__path__`. Python
cannot find subpackages in an empty path, so later imports like
`from laughtrack.core.entities.tag.model import Tag` fail with `ModuleNotFoundError`
even though the stub is correctly registered via `setdefault`.

Always compute `__path__` from the real source directory:

```python
# ✗ Wrong — empty __path__ blocks submodule discovery for ALL later tests
def _stub(name, as_package=False, **attrs):
    m = ModuleType(name)
    if as_package:
        m.__path__ = []   # ← never do this

# ✓ Correct — real path lets Python find submodules on disk
def _stub(name, as_package=False, **attrs):
    m = ModuleType(name)
    if as_package:
        m.__path__ = [str(_SCRAPER_ROOT / "src" / name.replace(".", "/"))]
        m.__package__ = name
```

This is especially important for namespace packages (no `__init__.py`, e.g.
`laughtrack.core.entities`) and for any package whose submodules may be needed by
later test files in the same pytest run.

## Scraper Tests — patch.object for Dynamically Loaded Modules

When patching an attribute (e.g. `Logger`) on a module loaded via `_load_module()` /
`importlib.util.spec_from_file_location()`, always use `patch.object(module_obj, "attr")`
— **never** the string form `patch("laughtrack.core.entities.club.service_direct.attr")`.

The string form resolves the dotted path by walking the real `laughtrack.core.entities`
package. If any prior test in the session has imported that real package, Python finds it
in `sys.modules` and looks for a `club` attribute on it — which doesn't exist — raising
`AttributeError`. The isolated test run passes; the full suite run fails.

```python
# ✗ Wrong — breaks when the real laughtrack.core.entities package is in sys.modules
with patch("laughtrack.core.entities.club.service_direct.Logger") as mock_logger:
    service.find_club_by_name("...")

# ✓ Correct — patches the attribute directly on the loaded module object
with patch.object(_club_service_mod, "Logger") as mock_logger:
    service.find_club_by_name("...")
```

This applies to any attribute on any module loaded under a dotted name that shares a
prefix with a real package in the codebase.

## Scraper Tests — Mock RateLimiter Singleton via monkeypatch

`RateLimiter()` is a singleton. **Never** mock its methods via direct instance assignment:

```python
# ✗ Wrong — mutates singleton.__dict__, leaks mock to all subsequent tests
scraper.rate_limiter.await_if_needed = fake_fn

# ✓ Correct — monkeypatch restores the attribute after each test
monkeypatch.setattr(scraper.rate_limiter, "await_if_needed", fake_fn)
```

Direct assignment persists after the test ends, causing unrelated test classes to call
your fake function instead of the real one. Symptom: tests like `TestResetDomain` that
call `await rl.await_if_needed(...)` find `_sessions` empty and fail with confusing
`AssertionError: assert 'domain' in {}`.

## Testing Concurrent asyncio Races

`AsyncMock` operations resolve in a single event-loop turn with no suspension.
A test using `asyncio.gather(coroutine_a(), coroutine_b())` may pass even when
a TOCTOU race bug is present, because one coroutine completes entirely before
the other begins — the race window never opens.

To properly force a race, use `asyncio.Event` + a `side_effect` that does
`await asyncio.sleep(0)` at the critical point to yield control to competing
coroutines. Example:

```python
entered = asyncio.Event()
async def slow_side_effect(*args, **kwargs):
    entered.set()            # signal we are inside the critical section
    await asyncio.sleep(0)   # yield so the competing coroutine can run
    return mock.return_value
mock.side_effect = slow_side_effect
```

## React Component and Hook Tests — Vitest Setup

The project uses `happy-dom` + `@testing-library/react` for React unit tests.
Add this docblock to any test file that renders React or calls hooks:

```
/**
 * @vitest-environment happy-dom
 */
```

Key mocking patterns:
- Mock `@/hooks/useUrlParams` (not `next/navigation` directly) to isolate hooks that read/write URL params.
- Mock heavy child components by path (e.g. `@/ui/components/params/sort`) to avoid their `next/navigation` dependency chain.
- Use `container.querySelector(...)` for scoped element queries when multiple renders exist in the same test — `getByTestId` queries the full document body and will throw on multiple matches.

Do NOT install `@vitejs/plugin-react` for test JSX support — it conflicts with vitest's bundled vite version.
The `esbuild.jsx: "automatic"` setting in `vitest.config.ts` handles JSX transform without a plugin.

## Vitest `vi.mock` Factories — Use `vi.hoisted()` for Shared Mock Variables

`vi.mock()` factories are hoisted to the top of the file before module-level `const`/`let`
variables are initialized. If a factory captures a variable defined in the module body,
it will throw `ReferenceError: Cannot access '<name>' before initialization`.

Fix: declare shared mock state with `vi.hoisted()`, which runs before hoisting:

```ts
const { mockFn } = vi.hoisted(() => ({ mockFn: vi.fn() }));

vi.mock("some-module", () => ({ fn: mockFn })); // ✓ safe
```

## `tusk commit` With New Test Directories — Verify Files Are Staged

When creating a new test directory (e.g., `tests/scrapers/.../the_rockwell/`) and calling
`tusk commit` with specific file paths, the commit output can be obscured by grep filters or
truncated output. If the files are untracked (not yet `git add`-ed), `tusk commit` may fail
silently on the `git add` step while still marking criteria done.

**Before calling `tusk criteria done --skip-verify`**, always verify all intended files are
either staged or committed:

```bash
git status --short apps/scraper/tests/   # confirms untracked test files
```

If files show as `??` (untracked) after a `tusk commit` call, stage and commit them manually:

```bash
git add <file1> <file2> && git commit -m "[TASK-<id>] <message>" \
  --trailer "Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

## OvationTix Venues — Two Scraper Patterns

OvationTix venues use `https://web.ovationtix.com/trs/api/rest/Production({id})/performance?`
(with `clientId` header) to fetch performance data. Two patterns exist based on how the
venue organizes its OvationTix productions:

**Pattern 1 — Calendar-based (e.g. Uncle Vinnies)**
- Many production IDs, each representing a single recurring show series
- Discover production IDs by scraping the venue's HTML calendar pages (look for
  anchor links like `class="tickets-button"` pointing to `ci.ovationtix.com/.../production/{id}`)
- For each production, fetch only `performanceSummary.nextPerformance` (one upcoming date)
- `scraper = 'uncle_vinnies'`

**Pattern 2 — Direct productions (e.g. Four Day Weekend Comedy)**
- Few production IDs on a static buy-tickets page, each with many upcoming performances
- Discover production IDs by fetching the venue's buy-tickets page and extracting
  `ci.ovationtix.com/{clientId}/production/{id}` links
- For each production, use the full `performances[]` array (all upcoming dates)
- `scraper = 'four_day_weekend'` (reuse this key for new venues following this pattern)

**Both patterns** use `Production({id})/performance?` with `clientId` and `newCIRequest: true`
headers. The client/org ID appears in the production URL on the venue's buy page.
Ticket pricing is fetched via a separate `Performance({id})` call per upcoming show.
The response `sections[].ticketTypeViews` provides per-tier pricing. Format the ticket
`type` field as `f"{ticketGroupName} - {name}"` (e.g. `"General - Adult"`) to match
`OvationTixClient._extract_ticket_data()` and avoid dedup key mismatches.

## OpenDate Venues — SSR HTML Scraping Pattern

When a venue sells tickets via **OpenDate** (`app.opendate.io`), the listing page is
server-rendered HTML — no public API is available.

**Listing URL format:**
  `https://app.opendate.io/v/{venue-slug}?per_page=500`

The `?per_page=500` parameter is **required** — the default returns only ~50 events per
page and does not paginate automatically. With `per_page=500` all upcoming events load
in a single request.

**Identification:** Playwright network inspection shows only analytics/Stripe requests —
no JSON API calls. WebFetch on the listing page returns full event HTML.

**HTML structure per event card (`div.confirm-card`):**

```html
<div class="card confirm-card">
  <div class="card-body">
    <!-- title + ticket URL -->
    <p class="mb-0 text-dark">
      <a class="text-dark stretched-link" href="https://app.opendate.io/e/{slug}">
        <strong>{Title}</strong>
      </a>
    </p>
    <!-- date string, e.g. "March 29, 2026" -->
    <p class="mb-0" style="color: #1982c4; ...">April 03, 2026</p>
    <!-- time string, e.g. "Doors: 6:30 PM - Show: 7:00 PM" -->
    <p class="mb-0" style="color: #1982c4; ...">Doors: 6:30 PM - Show: 7:00 PM</p>
    <!-- venue name line -->
    <p class="mb-0 text-truncate" ...>VENUE NAME • City, ST</p>
  </div>
</div>
```

**Key extraction notes:**
1. The stretched-link `<a>` gives both the event URL (for tickets) and the title (via `<strong>`).
2. The blue `p.mb-0` paragraphs are identified by the `color: #1982c4` inline style — the first
   is the date string, the second is the time string. Exclude `text-dark` and `text-truncate`
   paragraphs to avoid false matches.
3. Extract the **show time** from the time string via regex: `Show:\s*(\d{1,2}:\d{2}\s*[AP]M)`.
   Normalize compact format (`"8:30PM"`) to spaced format (`"8:30 PM"`) before `strptime`.
4. Date format: `"%B %d, %Y"` (e.g. `"March 29, 2026"`).
5. The event URL doubles as the ticket purchase URL — no separate ticket endpoint needed.
6. Use `per_page=500` as the single scraping target; `collect_scraping_targets()` returns only
   this one URL.

**Scraper key:** use `scraper = 'sports_drink'` as a reference implementation for new OpenDate
venues, adapting the venue slug and club details.

## TicketSource Venues — HTML Scraping Pattern

When a venue sells tickets via **TicketSource** (`ticketsource.com/{venue}`), the listing
page is server-rendered HTML — no JS widget or API needed.

**Identification:** The venue's website links to `ticketsource.us/{slug}` or
`ticketsource.com/{slug}`. WebFetch returns full event HTML (not a JS shell).

**HTML structure per event card (`div.eventRow`):**

```
div.eventRow[data-id="..."]
  div.eventTitle > a[itemprop="url", href="/slug/event-title/e-XXXXX"]
    span[itemprop="name"]                      ← show title
  div.dateTime[content="2026-03-28T19:30"]     ← ISO local datetime (no timezone)
    time                                       ← human-readable fallback (not used)
  div.event-btn > a[href="/booking/init/XXXX"] ← ticket purchase path
```

**Key implementation notes:**
1. Use `div.dateTime[content]` attribute for datetime — it gives a clean ISO string
   (`"YYYY-MM-DDTHH:MM"`) that can be parsed with `strptime(dt_str, "%Y-%m-%dT%H:%M")`
   and localized with `pytz.timezone(club.timezone).localize(naive)`.
2. Use `urllib.parse.urljoin(TICKETSOURCE_BASE, href)` — not string concatenation —
   for all URL construction. TicketSource hrefs are relative paths; `urljoin` handles
   both relative and absolute hrefs safely.
3. The `scraping_url` for the club should point to `https://www.ticketsource.com/{slug}`.
4. No pagination — all upcoming events appear on a single page.

**WebFetch rate-limiting:** TicketSource returns HTTP 429 on rapid WebFetch calls.
Use `browser_evaluate` to extract the raw HTML from an already-loaded Playwright page
if you need to inspect the DOM structure during discovery.

## Scraper Extractor Regexes — Generalize for Multi-Location Venues

When reusing an existing scraper for a second venue location (e.g., Comedy Store
La Jolla reusing `comedy_store`), check the extractor's URL pattern regexes for
hard-coded path prefixes that may differ between locations.

For example, `^/calendar/show/\d+/(.+)$` only matches West Hollywood hrefs —
it must be generalized to `^(?:/[^/]+)?/calendar/show/\d+/(.+)$` before it can
handle `/la-jolla/calendar/show/...`.

Before implementing a second location, fetch one day's HTML from the new location
and verify that every regex in the extractor matches the new URL structure.
