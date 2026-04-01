# SCRAPERS.md — Platform Decision Guide

A developer onboarding a new comedy club should be able to pick the right scraper in under 5 minutes using this guide. Start at the **Decision Flowchart**, confirm with the **Platform Sections**, then follow the DB setup instructions.

---

## Decision Flowchart

```
Is there a Ticketmaster widget or ticketmaster.com buy link?
  └── YES → platform: Ticketmaster → scraper: live_nation
              DB: ticketmaster_id = Discovery API venue ID (e.g. KovZpZAJalFA)

Is there an Eventbrite widget or eventbrite.com buy link?
  └── YES → platform: Eventbrite → scraper: eventbrite
              DB: eventbrite_id = organizer ID (11 digits) or venue ID (8-9 digits)

Is there a SeatEngine buy link?
  └── Check the subdomain in the link:
      v-{uuid}.seatengine.net → scraper: seatengine_v3
                                 DB: seatengine_id = UUID from page JSON-LD "identifier"
      (no v- prefix)          → scraper: seatengine  (or seatengine_classic for legacy)
                                 DB: seatengine_id = numeric venue ID (1–700 range)

Is there a buy link to `{venue}.thundertix.com`?
  └── YES → platform: ThunderTix → new venue-specific scraper required
              (see ThunderTix section — use annoyance scraper as reference)

Is there a tixr.com buy link?
  └── YES → platform: Tixr → new venue-specific scraper required
              (see Tixr section — short/long URL format matters)

Check browser network requests (browser_navigate + browser_network_requests):
  └── tockify.com/api/tagoptions/<calname>   → platform: Tockify
                                                → new venue-specific scraper required
  └── /api/open/GetItemsByMonth              → platform: Squarespace
                                                → new venue-specific scraper required
  └── crowdwork.com/api/v2/<theatre>/shows   → platform: Crowdwork
                                                → new venue-specific scraper required
  └── plugin.vbotickets.com                  → platform: VBO Tickets
                                                → new venue-specific scraper required
  └── /.netlify/functions/availability       → platform: Netlify Functions
                                                → new venue-specific scraper required
  └── /wp-json/tribe/events/v1/events        → platform: Tribe Events Calendar (WordPress)
                                                → scraper: the_rockwell (generic; set scraping_url)

Check page source:
  └── squadup = { userId: [<id>] ... } in page JS
        → platform: SquadUP → new venue-specific scraper required
  └── <script type="application/ld+json"> with "@type": "Event"
        → platform: JSON-LD → scraper: json_ld (generic; set scraping_url)
  └── CSS classes: rhpSingleEvent / eventWrapper / rhp-event__title--list
        → platform: rhp-events (WordPress) → scraper: comedy_magic_club (generic; set scraping_url)
  └── data-compId on Wix event widget / wixstatic.com assets
        → platform: Wix Events → new venue-specific scraper required
  └── CSS classes: eventRow / dateTime (with content attr) / event-btn
        → platform: TicketSource → new venue-specific scraper required
              (see TicketSource section — use comedy_clubhouse scraper as reference)
  └── events.humanitix.com/host/<slug> in buy links
        → platform: Humanitix → scraper: json_ld (generic; set scraping_url to host URL)
  └── tickets.{venue}.com subdomain + api.ninkashi.com network requests
        → platform: Ninkashi → scraper: ninkashi (generic; set scraping_url to subdomain)

None of the above → custom HTML scraper required
  (StageTime: self.__next_f.push RSC segments at {slug}.stageti.me — see StageTime section)
  (OpenDate: server-rendered confirm-card divs at app.opendate.io — see OpenDate section)
```

---

## Platform Sections

### Ticketmaster

| | |
|---|---|
| **Scraper key** | `live_nation` |
| **DB field** | `ticketmaster_id` |
| **Value format** | Alphanumeric Discovery API venue ID, e.g. `KovZpZAJalFA` — NOT a numeric ID |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Ticketmaster widget embedded on the venue page
- Buy links pointing to `ticketmaster.com`
- Discovery API returns JSON-LD `@type=Event` blocks

**Finding the venue ID:**
```bash
curl -s "https://app.ticketmaster.com/discovery/v2/venues.json?apikey=<KEY>&keyword=<venue name>&countryCode=US" \
  | python3 -c "import sys,json; [print(v['id'], v['name']) for v in json.load(sys.stdin).get('_embedded',{}).get('venues',[])]"
```

**Diagnosis — 0 events returned:**
When a Ticketmaster-backed scraper returns 0 events, first verify the stored `ticketmaster_id` is the correct **Discovery API venue ID** (alphanumeric, e.g. `KovZ917ARvk`) — NOT a numeric ID from another system. Query without any classification filter first to confirm events exist for the venue ID at all; only investigate `classificationName` filters *after* confirming the ID works.

**DB setup:**
```sql
UPDATE clubs SET scraper = 'live_nation', ticketmaster_id = 'KovZpZAJalFA' WHERE name = 'My Club';
```

---

### Eventbrite

| | |
|---|---|
| **Scraper key** | `eventbrite` |
| **DB field** | `eventbrite_id` |
| **Value format** | Organizer ID (11 digits, from `/o/<slug>-<id>` URL) or venue ID (8-9 digits) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Eventbrite widget embedded on the venue page
- Buy links pointing to `eventbrite.com`
- Organizer URL: `eventbrite.com/o/<slug>-<organizer_id>`

**Finding the ID:**
1. **Organizer ID**: extract from `eventbrite.com/o/<slug>-<organizer_id>` URL
2. **Venue ID**: grab any event ID from the embedded widget JS (`eventId: '<digits>'`), fetch `eventbrite.com/e/<event_id>`, find the organizer link

The scraper tries `/venues/{id}/events/` first; if that 404s, it auto-falls back to `/organizers/{id}/events/`.

**Organizer ID vs Venue ID:**
- Organizer ID: typically 11 digits, from `/o/<slug>-<id>` URL — auto-routed to `/organizers/{id}/events/`
- Venue ID: typically 8–9 digits, from an individual event's JSON `"venue_id"` field — auto-routed to `/venues/{id}/events/`
The scraper tries the venue endpoint first and auto-falls back to the organizer endpoint on 404.

**`scraping_url` format:** Always use the full organizer URL including the slug:
  `'https://www.eventbrite.com/o/<slug>-<organizer_id>'`
The slug is required for consistency with existing venues.

**Multi-location chains:** Don't guess the organizer URL using a sibling location's ID (always redirects to the primary organizer). Instead:
1. Fetch the venue's show listing page (e.g. `laughfactory.com/long-beach`)
2. Grab any Eventbrite event ID from the embedded widget JS (`eventId: '<digits>'` in page source)
3. Fetch `https://www.eventbrite.com/e/<event_id>` — the organizer URL appears in the page data

**Wix + Eventbrite backend:** Some Wix-hosted venues use the "Events Calendar" widget (inffuse.eventscalendar.co) backed by Eventbrite. Identify via Playwright network inspection:
- POST to `https://inffuse.eventscalendar.co/js/v0.1/calendar/data`
- GET to `https://broker.eventscalendar.co/api/eventbrite/events?calendar=<id>`
The `calendar=` parameter **is the Eventbrite organizer ID** — use `scraper='eventbrite'` with that ID. No Wix access token needed.

**DB setup:**
```sql
UPDATE clubs SET scraper = 'eventbrite', eventbrite_id = '30460267696' WHERE name = 'My Club';
```

---

### SeatEngine — Identification Checklist

When onboarding a new SeatEngine venue, check the subdomain before assuming which platform variant it uses:

1. Check the page footer for "Powered by Seat Engine" + the banner/contact link
2. If the linked domain matches `v-{uuid}.seatengine.net` → **v3 platform** (UUID-based, GraphQL API). Scanning numeric IDs 1–700 will find nothing.
3. If page source contains `cdn.seatengine.com/assets/application` in `<script>` tags → **Classic platform** (HTML-rendered, no REST API). The numeric venue ID is embedded in the logo CDN URL: `https://files.seatengine.com/styles/logos/{id}/original/`.
4. If none of the above → **v1 platform** (numeric ID, REST API). Use `seatengine_national` to discover IDs via enumeration.

⚠️ **CDN file IDs ≠ API venue IDs.** The `files.seatengine.com/styles/logos/{ID}/` CDN path embeds a classic-platform file storage ID — this is NOT the same namespace as the new-platform API (`services.seatengine.com/api/v1/venues/{id}`).

---

### SeatEngine v1

| | |
|---|---|
| **Scraper key** | `seatengine` (or `seatengine_classic` for legacy endpoints) |
| **DB field** | `seatengine_id` |
| **Value format** | Numeric ID, typically in the 1–700 range |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Buy links pointing to a seatengine.net domain **without** the `v-{uuid}` prefix
- Footer: "Powered by Seat Engine" with a non-UUID link
- Page footer or contact link uses a plain subdomain (e.g., `myvenue.seatengine.net`)

**Finding the ID:** Use the `seatengine_national` discovery scraper, or enumerate via the SeatEngine REST API.

**DB setup:**
```sql
UPDATE clubs SET scraper = 'seatengine', seatengine_id = '123' WHERE name = 'My Club';
```

---

### SeatEngine Classic (Legacy)

| | |
|---|---|
| **Scraper key** | `seatengine_classic` |
| **DB field** | `scraping_url` (runtime) · `seatengine_id` (metadata only) |
| **Value format** | `scraping_url`: full venue calendar URL · `seatengine_id`: numeric (may be NULL) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**⚠️ Important: `seatengine_id` is NOT used at runtime.**
`seatengine_classic` fetches events from `scraping_url` directly — `seatengine_id` is stored for
record-keeping only and never appears in any URL or API call. The field name is misleading; do NOT
enumerate or look up numeric IDs for `seatengine_classic` venues. If `seatengine_id` is NULL, the
scraper still works correctly as long as `scraping_url` is set.

**⚠️ CDN file IDs ≠ API venue IDs.**
`files.seatengine.com/styles/logos/{ID}/` CDN URLs embed a numeric ID, but this is the
classic-platform **file storage ID** — it is NOT the same namespace as the new-platform API
(`services.seatengine.com/api/v1/venues/{id}`). The new platform recycles numeric IDs as venues
migrate or deactivate, so the same number may point to a completely different venue in the API.
Do not use CDN URL extraction to recover or verify SeatEngine API venue IDs.

**Detection signals:**
- Same as SeatEngine v1, but the venue's calendar is served at a custom URL path rather than via
  the standard SeatEngine REST API
- `scraping_url` is set; `seatengine_id` may be NULL or present as a reference value

**DB setup:**
```sql
UPDATE clubs SET scraper = 'seatengine_classic', scraping_url = 'https://myvenue.seatengine.net/shows' WHERE name = 'My Club';
-- seatengine_id may be set for record-keeping but is ignored at runtime
```

---

### SeatEngine v3

| | |
|---|---|
| **Scraper key** | `seatengine_v3` |
| **DB field** | `seatengine_id` |
| **Value format** | UUID, e.g. `cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3` |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Buy links or contact link uses `v-{uuid}.seatengine.net` subdomain
- Footer: "Powered by Seat Engine" + banner/contact link with `v-` prefix
- Page JSON-LD `<script>` contains `"identifier": "<uuid>"`

**Finding the UUID:** Inspect the page's JSON-LD `<script>` for `"identifier"`.

**DB setup:**
```sql
UPDATE clubs SET scraper = 'seatengine_v3', seatengine_id = 'cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3' WHERE name = 'My Club';
```

---

### Tixr

| | |
|---|---|
| **Scraper key** | Venue-specific (e.g. `the_stand_nyc`, `haha_comedy_club`, `st_marks`) |
| **DB field** | `scraping_url` |
| **Generic?** | ❌ Requires a new venue-specific scraper |

**Detection signals:**
- Buy buttons linking to `tixr.com/groups/{group}/events/{slug}-{id}` (long form)
- Buy buttons linking to `tixr.com/e/{id}` (short form)

**URL format matters:**
| Format | Example | Support |
|---|---|---|
| Long form (`-{id}`) | `tixr.com/groups/foo/events/show-name-12345` | ✅ Full — JSON-LD extracted |
| Short form (`/e/{id}`) | `tixr.com/e/12345` | ✅ Full — redirect followed, JSON-LD extracted |
| Double-dash (`--{id}`) | `tixr.com/groups/foo/events/show-name--12345` | ❌ Silently skipped — no JSON-LD in SSR |

**Implementation pattern:** Copy an existing Tixr scraper (e.g. `the_stand_nyc`) and adjust the calendar URL and pagination logic. `TixrClient.get_event_detail_from_url()` handles both URL formats transparently.

**Generic `tixr` scraper (server-rendered calendar pages):**
When a venue's calendar page (own website or a Tixr group page like `tixr.com/groups/<slug>`) embeds Tixr event links in server-rendered HTML, use the generic `tixr` scraper — no custom Python code needed:
- `scraper = 'tixr'`
- `scraping_url = '<venue calendar page URL>'`

The `TixrScraper` fetches the page, extracts all Tixr URLs (both short-form and long-form) via `TixrExtractor`, then batch-resolves each to a `TixrEvent` via `TixrClient`.

**When to use a custom scraper instead:** If the venue's Tixr group page triggers DataDome bot-detection (returns 403 or empty results when fetched via `fetch_html`), use a Covina-style venue scraper that calls `tixr_client._fetch_tixr_page(url)` instead — this uses a bare curl_cffi session with no application headers, bypassing DataDome.

**Short URL format:** Tixr event links appear in two formats:
1. **Long form**: `https://www.tixr.com/groups/{group}/events/{slug}-{id}` — regex: `r"https?://[^\s\"]*tixr\.com/[^\s\"]*/events/[^\s\"]*"`
2. **Short form**: `https://tixr.com/e/{id}` — regex: `r"https?://(?:www\.)?tixr\.com/e/(\d+)"`

`TixrClient.get_event_detail_from_url()` handles both formats transparently — curl_cffi follows the redirect from short URLs to the full event page.

**Double-dash format (`--{id}`) — Won't-Fix:**
The `--{id}` URL format (`/events/{slug}--{id}`) only embeds `window.pageSetup = { eventId: {id} }` in SSR HTML — no JSON-LD, no date, no performers. Event data requires a DataDome CAPTCHA-solved JS session to fetch from the client-side API, which curl_cffi impersonation cannot provide. These events are silently skipped with a specific warning:
> "Tixr special-event page (--ID format) has no JSON-LD; data requires JS execution — skipping: {url}"

**Smoke test pattern:** venue-specific tests for `tixr` scraper venues instantiate `TixrScraper(club)`, mock `TixrScraper.fetch_html` (not `_fetch_tixr_page`), and verify `TixrPageData` is returned with ≥1 event.

---

### Tockify

| | |
|---|---|
| **Scraper key** | Venue-specific (e.g. `ice_house`) |
| **DB field** | `scraping_url` (optional override) |
| **Generic?** | ❌ Requires parameterization — the `calname` is hardcoded per venue |

**Detection signals (via Playwright network inspection):**
```
GET https://tockify.com/api/tagoptions/<calname>
```
The `<calname>` is the venue's Tockify calendar identifier (e.g., `theicehouse`).

**API endpoint:**
```
GET https://tockify.com/api/ngevent?calname=<calname>&max=200&startms=<now_ms>
```

**Key implementation details:**
- Timestamps are in **milliseconds** (not seconds)
- Ticket URLs: normalize `embed.showclix.com/event/{slug}` → `www.showclix.com/event/{slug}`
- Paginate via `metaData.hasNext` + `startms`
- `when.start.tzid` gives the timezone string

**To onboard a new Tockify venue:**
1. Use Playwright to find the `calname` in network requests
2. Create a new scraper directory (copy `ice_house/`) and replace `theicehouse` with the new calname
3. Verify the `customButtonLink` ticket URL format
4. Set `scraping_url` in the DB (optional — only needed if overriding the hardcoded URL)

---

### Squarespace

| | |
|---|---|
| **Scraper key** | `squarespace` |
| **DB field** | `scraping_url` (full GetItemsByMonth URL including `collectionId` query param) |
| **Generic?** | ✅ Generic — a second venue needs only a DB row |

**Detection signals:**
- `WebFetch` returns an HTML shell with no event data (JS-rendered)
- Playwright `browser_network_requests` shows:
  ```
  GET /api/open/GetItemsByMonth?month=MM-YYYY&collectionId=<id>
  ```

**Key implementation details:**
- Response is a **root-level JSON array** (not a dict) — handle accordingly
- `collectionId` is NOT in page source; find it via Playwright network inspection
- The `crumb` param seen in browser requests is NOT required for `/api/open/` — omit it
- Timestamps are in **milliseconds**
- API returns one month at a time — iterate current month + N months ahead
- No external ticket URL — use `fullUrl` (prepend base domain) as the show page / ticket fallback

**Two-collection trap:** Some Squarespace sites have a calendar-block collection (type 10, e.g. `/shows`) separate from the actual event-items collection (e.g. `/all-shows`). If `GetItemsByMonth` returns `[]` for the ID found on the listing page, fetch an individual event's page (`/all-shows/<slug>`) and read its `Static.SQUARESPACE_CONTEXT` — the `collection.id` there is the correct ID to use in the scraping URL.

**To onboard a new Squarespace venue:**
1. Navigate in Playwright → capture `browser_network_requests` → find `GetItemsByMonth` call
2. Extract `collectionId` from the network request URL
3. Insert a DB row with `scraper='squarespace'` and `scraping_url='https://<domain>/api/open/GetItemsByMonth?collectionId=<id>'`
4. No Python changes needed

---

### Wix Events

| | |
|---|---|
| **Scraper key** | Venue-specific (e.g. `bushwick`) |
| **DB field** | `scraping_url` |
| **Generic?** | ❌ Requires parameterization — `compId` is hardcoded per venue |

**Detection signals:**
- `wixstatic.com` assets loaded
- Event widget has `data-compId` attributes
- Footer: "Powered by Wix"

**Finding the `compId`** (Playwright required):
```javascript
// Run this in browser_evaluate after navigating to the venue homepage
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
The innermost `comp-xxxx` result is the `compId`.

**Key implementation details:**
- `categoryId` is NOT required unless the venue uses Wix event categories
- API: `POST /_api/wix-one-events-server/web/paginated-events/viewer?compId=<compId>` — paginated event list
- Requires an OAuth access token fetched first from `/_api/v1/access-tokens`

---

### Crowdwork

| | |
|---|---|
| **Scraper key** | Venue-specific (e.g. `philly_improv_theater`) |
| **DB field** | `scraping_url` |
| **Generic?** | ❌ Requires parameterization — theatre slug is hardcoded per venue |

**Detection signals (via Playwright network inspection):**
```
GET https://crowdwork.com/api/v2/<theatre>/shows
```
The `<theatre>` value comes from the `data-theatre` attribute on the embedded script tag.

**To onboard a new Crowdwork venue:**
1. Navigate in Playwright → capture `browser_network_requests` → find the API call
2. Extract the `<theatre>` slug from the URL
3. Create a new scraper directory and replace the theatre slug

---

### VBO Tickets

| | |
|---|---|
| **Scraper key** | Venue-specific (e.g. `esthers_follies`) |
| **DB field** | `scraping_url` (venue tickets page URL) |
| **Generic?** | ❌ Requires a new venue-specific scraper |

**Detection signals:**
- Network requests to `plugin.vbotickets.com`
- Ticketing iframe loads `plugin.vbotickets.com/plugin/loadplugin?siteid=<UUID>`

**Session flow:** VBO uses a session-based iframe — there is no unauthenticated public JSON API.
The scraper must:
1. `GET plugin.vbotickets.com/plugin/loadplugin?siteid=<SITE_ID>&page=ListEvents`
   → Returns a small HTML page with the session UUID embedded in inline JS
2. Extract the UUID — VBO uses **unquoted JS object keys**, not JSON:
   ```python
   _SESSION_RE = re.compile(
       r'value["\s:]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
       re.IGNORECASE,
   )
   ```
   A quoted-key regex (`"value"\s*:\s*"uuid"`) will silently return no match.
3. `GET plugin.vbotickets.com/v5.0/controls/events.asp?a=load_eventdate_slider&eid=<EID>&s=<SESSION>`
   → Returns server-rendered HTML with upcoming show dates (~6 week window)

**Finding `SITE_ID` and `EID`:** `SITE_ID` is in the loadplugin URL. `EID` is in the seatmap inline JS (`LoadEvent('<EID>', ...)` onclick handlers).

**Ticket URLs:** Per-show VBO URLs are session-dependent and non-shareable. Use the venue's stable tickets page as the ticket URL fallback.

**Troubleshooting HTTP 401 errors:** When a VBO scraper returns 401, the session key stored in `scraping_url` has rotated. The static page JS (e.g. Squarespace `var s = "..."`) shows the **old** key. The real working key only appears in live Playwright network requests — skip static inspection and go straight to:
```bash
# Use Playwright MCP: navigate to the venue's /calendar page, then call browser_network_requests
# Look for: GET plugin.vbotickets.com/Plugin/events/showevents?...&s=<NEW_KEY>
# Update clubs SET scraping_url = '...?s=<NEW_KEY>' WHERE name = '<Venue>';
```

**Esther's Follies (Austin, TX) — venue-specific constants:**
- `SITE_ID`: `5D695E7C-1246-4F54-BF57-B1D92D1E6B83`
- `EID`: `39242`
- Stable ticket URL: `https://www.esthersfollies.com/tickets`
- Shows run **Thu–Sat nights** at 7 PM and 9 PM (~6 week window returned by date slider)

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...) VALUES (..., 'esthers_follies', 'https://www.esthersfollies.com/tickets', ...);
```

---

### Tribe Events Calendar (WordPress)

| | |
|---|---|
| **Scraper key** | `the_rockwell` |
| **DB field** | `scraping_url` |
| **Generic?** | ✅ Already generic — works for any Tribe Events Calendar venue |

**Detection signals:**
- Network requests to `/wp-json/tribe/events/v1/events`
- WordPress site with The Events Calendar plugin

**DB setup:** Set `scraping_url` to the base REST API URL:
```sql
UPDATE clubs SET scraper = 'the_rockwell', scraping_url = 'https://myvenue.com/wp-json/tribe/events/v1/events' WHERE name = 'My Club';
```

---

### rhp-events (WordPress Plugin)

| | |
|---|---|
| **Scraper key** | `comedy_magic_club` |
| **DB field** | `scraping_url` |
| **Generic?** | ✅ Already generic — works for any rhp-events venue |

**Detection signals (page source):**
```
rhpSingleEvent    eventWrapper    rhp-event__title--list
```

**Important:** Do NOT implement pagination — all `/events/page/N/` URLs return identical content. Fetch only the base `/events/` URL. Deduplication via upsert handles any double-fetches.

**Single-show page quirk:** The `class = "eventStDate"` attribute on single-show detail pages uses spaces around `=` (i.e. `class = "..."`, not `class="..."`). Regex patterns targeting class attributes on these pages must use `class\s*=\s*"` rather than `class="` to match correctly.

**DB setup:**
```sql
UPDATE clubs SET scraper = 'comedy_magic_club', scraping_url = 'https://myvenue.com/events/' WHERE name = 'My Club';
```

---

### JSON-LD (Generic Fallback)

| | |
|---|---|
| **Scraper key** | `json_ld` |
| **DB field** | `scraping_url` |
| **Generic?** | ✅ Already generic — works for any page with JSON-LD Event markup |

**Detection signals (page source):**
```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Event", ...}
</script>
```

**DB setup:**
```sql
UPDATE clubs SET scraper = 'json_ld', scraping_url = 'https://myvenue.com/events/' WHERE name = 'My Club';
```

---

### SquadUP

| | |
|---|---|
| **Scraper key** | venue-specific (e.g. `sunset_strip`) |
| **DB field** | `scraping_url` (display URL only; API URL is hard-coded in scraper) |
| **Generic?** | ❌ Venue-specific — `user_id` differs per venue |

**Detection signals:**
- Page JS contains `squadup = { userId: [<id>], ... }` (inline script on the events page)
- SquadUP embed CSS/JS loaded from `embed.squadup.com`
- Ticket links go to `squadup.com/events/<slug>`

**API endpoint:**
```
GET https://www.squadup.com/api/v3/events
    ?user_ids=<id>&page_size=100&include=custom_fields&page=<N>
```

**Key non-obvious details:**
1. The `userId` array in the page JS (e.g. `userId: [9086799]`) is the value to pass as `user_ids`.
2. The API is Cloudflare-protected. Use a **bare `AsyncSession.get(url)`** with `impersonate="chrome124"` and **no extra headers** — adding application headers triggers a 403.
3. Pagination: `meta.paging.total_pages` in the first response tells you how many pages to fetch.
4. `start_at` is ISO 8601 with UTC offset (e.g. `"2026-03-26T20:00:00-05:00"`). Parse directly with `datetime.fromisoformat()`.
5. Ticket URL: use the `url` field (e.g. `"https://squadup.com/events/comedy-gold-51"`).
6. Shows at SquadUP venues are often recurring showcases with rotating lineups — comedian names are typically not pre-announced in the API data. Use the show title heuristic (generic title regex → `[]` performers) rather than expecting a dedicated performers field.

**To onboard a new SquadUP venue:**
1. Fetch the venue events page and search the HTML for `userId:` to extract the numeric ID.
2. Create a new scraper dir under `scrapers/implementations/venues/<venue>/`.
3. Hard-code `_SQUADUP_USER_ID` in the scraper; set `scraper='<key>'` in the DB.
4. Use bare `AsyncSession(impersonate="chrome124")` with no extra headers in `_fetch_events_page()`.

---

### Tixologi (Laugh Factory CMS)

| | |
|---|---|
| **Scraper key** | `laugh_factory_reno` |
| **DB field** | `scraping_url` |
| **Generic?** | ❌ Venue-specific — the CMS page URL is hardcoded |

**Detection signals:**
- Ticket links follow the pattern `laughfactory.club/checkout/show/{punchup_id}`
- Shows are server-rendered as `.show-sec.jokes` divs on a Laugh Factory CMS page
- Note: `api-v2.tixologi.com/public/users/{partner_id}/events` returns 401 — HTML scraping required

The `TixologiClient` fetches the CMS HTML page; `LaughFactoryRenoEventExtractor` parses the `.show-sec.jokes` divs (date span, timing span, ticket anchor, title h4, figcaption comedian names).

**API limitations:**
- `GET https://api-v2.tixologi.com/public/users/partners/{partner_id}/events` → 401 Unauthorized
- `GET https://api-v2.tixologi.com/public/users/partners/{partner_id}` → partner metadata only (works without auth)
- HTML scraping of the Laugh Factory CMS page is required; there is no public events API

**Date format quirk:** The `.shedule span.date` contains a non-breaking space (`\xa0`) between the weekday abbreviation and the date string, e.g. `"Wed\xa0Apr 10"`. Strip the weekday prefix on `\xa0`, then infer year (current if future, else next).

**Reference implementation:** `apps/scraper/src/laughtrack/core/clients/tixologi/`

---

### Netlify Functions (East Austin Comedy)

| | |
|---|---|
| **Scraper key** | `east_austin_comedy` |
| **DB field** | `scraping_url` (venue homepage, unused at runtime) |
| **Generic?** | ❌ Venue-specific — API endpoints are hardcoded |

**Detection signals:**
- Network requests to `eastaustincomedy.com/.netlify/functions/availability`
- Ticket purchase is handled via an embedded Square modal on the homepage (no per-show URL)

**API endpoints:** One endpoint per weekday name — 7 total calls per scrape run:
```
GET https://eastaustincomedy.com/.netlify/functions/availability?showDay={day}&offset=0
```
where `{day}` is one of: `monday tuesday wednesday thursday friday saturday sunday`.

Each response is a JSON array of upcoming dates for that day-of-week with show times and seat
availability. The scraper queries all 7 endpoints and deduplicates on `(date, time)`.

**Key non-obvious details:**
1. **No comedian lineups** — the website never publishes performer names. All shows are titled
   "Live Stand-Up Comedy"; the lineup is always an empty list.
2. **No per-show ticket URL** — tickets are sold via an embedded Square modal on the homepage.
   The ticket URL is always the homepage anchor: `https://eastaustincomedy.com/#shows`.
3. **Show volume:** weekday evenings typically have 1–2 shows; Fri/Sat/Sun have up to 3 shows
   (e.g. 6 PM / 8 PM / 10 PM).
4. The `scraping_url` DB field is unused at runtime — the scraper ignores it and always hits
   the Netlify function directly.

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...) VALUES (..., 'east_austin_comedy', 'https://eastaustincomedy.com/#shows', ...);
```

---

### Vivenu

| | |
|---|---|
| **Scraper key** | `vivenu` |
| **DB field** | `scraping_url` (Vivenu seller page root URL) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Venue sells tickets through a custom subdomain (e.g. `tickets.thirdcoastcomedy.club`)
- The seller page is a Next.js app — page source contains `<script id="__NEXT_DATA__" type="application/json">`
- `__NEXT_DATA__` has `props.pageProps.sellerPage.events[]`

**Key implementation details:**
- Event data path: `props.pageProps.sellerPage.events[]` in `__NEXT_DATA__` JSON
- Ticket URL pattern: `{base_url}/event/{event.url}` where `base_url` is derived from `scraping_url`
- Start times: ISO 8601 UTC strings (e.g. `"2026-04-15T00:00:00.000Z"`) — convert via the event's `timezone` field
- HTTP: uses `fetch_html_bare` (no application headers) to avoid Cloudflare bot-detection
- Only upcoming events are returned (start > now)

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'vivenu', 'https://tickets.thirdcoastcomedy.club/', ...);
```

**Example — Third Coast Comedy Club (Nashville, TN):**
```sql
UPDATE clubs SET scraper = 'vivenu', scraping_url = 'https://tickets.thirdcoastcomedy.club/'
WHERE name = 'Third Coast Comedy Club';
```

---

### Prekindle

| | |
|---|---|
| **Scraper key** | `json_ld` |
| **DB field** | `scraping_url` (full Prekindle events page URL) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Venue's website links to `prekindle.com/events/{slug}`
- The Prekindle events page is server-rendered HTML with a `<script type="application/ld+json">` block
- JSON-LD `@type` is `ComedyEvent`

**Key implementation details:**
- Uses the existing `json_ld` scraper — no new code needed
- The `{venue-slug}` appears in the venue's Prekindle events page URL: `prekindle.com/events/{slug}`
- All upcoming events are embedded in a single JSON-LD block on the listing page
- **Rate-limiting:** rapid successive fetches (< ~60s) return HTML without the JSON-LD block,
  triggering "Page loaded but contained no JSON-LD events". Nightly single-run scrapes are unaffected.
- The Prekindle events page may include a `wicketpath` attribute on the JSON-LD `<script>` tag (Java Wicket framework). BeautifulSoup handles this correctly — no special handling needed.

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'json_ld', 'https://www.prekindle.com/events/{venue-slug}', ...);
```

**Example — Hyena's Comedy Nightclub:**
```sql
UPDATE clubs SET scraper = 'json_ld', scraping_url = 'https://www.prekindle.com/events/hyenas-comedy-nightclub'
WHERE name = 'Hyena''s Comedy Nightclub';
```

---

### ThunderTix

| | |
|---|---|
| **Scraper key** | venue-specific (e.g. `annoyance`) |
| **DB field** | `scraping_url` |
| **Value format** | `https://{venue-slug}.thundertix.com` |
| **Generic?** | ❌ New venue-specific scraper required |

**Detection signals:**
- Buy links or calendar pages at `{venue-slug}.thundertix.com`
- Network requests to `{venue-slug}.thundertix.com/reports/calendar`

**API pattern:**
```
GET https://{venue-slug}.thundertix.com/reports/calendar?week=0&start={ts}&end={ts+7d}
```
Returns a JSON array of performance objects, one per show. A single request covers a 7-day window.
The `annoyance` scraper generates 12 weekly URLs starting from the current Sunday.

**Key fields in each performance object:**
- `title` — show name
- `start` — datetime string with UTC offset (e.g. `"2026-03-24 20:00:00 -0500"`)
- `order_products_url` — relative ticket purchase path (prepend base URL)
- `truncated_url` — relative show page path (prepend base URL)
- `publicly_available` — skip when `False`
- `is_sold_out` — mark ticket as sold out when `True`

**Filtering rules (verify per venue):**
- Skip events where `publicly_available` is `False`
- Skip events whose title starts with training/class prefixes (venue-specific — check live data)

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/venues/annoyance/`

**To onboard a new ThunderTix venue:**
1. Confirm the venue slug from the buy page URL: `{slug}.thundertix.com` (e.g. `theannoyance`)
2. Copy the `annoyance/` scraper directory as the reference implementation
3. Update `_BASE_URL`, `_TITLE_SKIP_PREFIXES`, scraper `key`, and class names
4. Add a DB migration setting `scraper` and `scraping_url`

**DB setup:**
```sql
INSERT INTO clubs (name, scraper, scraping_url, ...)
VALUES ('My Venue', 'my_venue', 'https://myslug.thundertix.com', ...);
```

---

### TicketSource

| | |
|---|---|
| **Scraper key** | venue-specific (e.g. `comedy_clubhouse`) |
| **DB field** | `scraping_url` |
| **Value format** | `https://www.ticketsource.com/{venue-slug}` |
| **Generic?** | ❌ New venue-specific scraper required |

**Detection signals:**
- Buy links or redirects to `ticketsource.com/{slug}` or `ticketsource.us/{slug}`
- Page source contains CSS classes `eventRow`, `dateTime`, `event-btn`
- Server-rendered HTML — no JS required; `WebFetch` returns full event data

**HTML structure per event card:**
```
div.eventRow[data-id="..."]
  div.eventTitle > a[itemprop="url", href="/slug/event-title/e-XXXXX"]
    span[itemprop="name"]                      ← show title
  div.dateTime[content="2026-03-28T19:30"]     ← ISO local datetime (no timezone)
  div.event-btn > a[href="/booking/init/XXXX"] ← ticket purchase path
```

**Key implementation details:**
- Use `div.dateTime[content]` for datetime — parse with `strptime(dt_str, "%Y-%m-%dT%H:%M")`
  and localize with `pytz.timezone(club.timezone).localize(naive_dt)`
- Use `urllib.parse.urljoin(TICKETSOURCE_BASE, href)` for all URL construction — TicketSource
  hrefs are relative paths; `urljoin` handles both relative and absolute hrefs safely
- All upcoming events appear on a single page — no pagination needed
- **Rate-limiting:** TicketSource returns HTTP 429 on rapid successive WebFetch calls

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/venues/comedy_clubhouse/`

**To onboard a new TicketSource venue:**
1. Confirm the venue slug from the buy page URL: `ticketsource.com/{slug}`
2. Copy the `comedy_clubhouse/` scraper directory as the reference implementation
3. Update `SCRAPING_URL` constant, scraper `key`, and class names
4. Add a DB migration setting `scraper` and `scraping_url`

**DB setup:**
```sql
INSERT INTO clubs (name, scraper, scraping_url, ...)
VALUES ('My Venue', 'my_venue', 'https://www.ticketsource.com/my-venue', ...);
```

---

### Humanitix

| | |
|---|---|
| **Scraper key** | `json_ld` |
| **DB field** | `scraping_url` (full Humanitix host page URL) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Venue's website links to `events.humanitix.com/host/<slug>`
- The host page embeds `<script type="application/ld+json">` blocks with `@type=Event`

**Key implementation details:**
- Uses the existing `json_ld` scraper — no new code needed
- The `<slug>` appears in the Humanitix host page URL
- The `JsonLdScraper` fetches the host page and extracts all events in a single request — no per-event page visits needed
- Ticket URLs follow the pattern `https://events.humanitix.com/{event-slug}/tickets`
- **No public REST API** — the host page HTML is the only data source
- No `humanitix_id` column exists; store the full host URL in `scraping_url`

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'json_ld', 'https://events.humanitix.com/host/my-venue', ...);
```

---

### Ninkashi

| | |
|---|---|
| **Scraper key** | `ninkashi` |
| **DB field** | `scraping_url` (the `url_site` subdomain, e.g. `tickets.cttcomedy.com`) |
| **Generic?** | ✅ Already generic — no code needed for new venues |

**Detection signals:**
- Venue has a `tickets.{venue}.com` subdomain
- Network requests to `api.ninkashi.com/public_access/events/find_by_url_site`

**API endpoint** (no auth required):
```
GET https://api.ninkashi.com/public_access/events/find_by_url_site?url_site=<url_site>&page=1&per_page=100
```

Response is a **root-level JSON array** of events. Key fields: `id`, `title`, `time_zone` (IANA string), `tickets_attributes`, `event_dates_attributes`.

**Pagination behavior:**
- The client requests `per_page=100` per page and increments `page` until a stop condition is met.
- **Stop condition:** a page whose length is less than the first page's actual response size (not the hardcoded `PER_PAGE=100`). This handles APIs that return fewer items on the first page and ensures the loop terminates correctly even if the first page is a partial page.
- **Hard cap:** `MAX_PAGES=50` — pagination stops regardless of page size once 50 pages have been fetched, with a warning logged.
- **Past-event filtering:** The client filters events client-side using `_is_future_event()`. Each event's `event_dates_attributes[0].starts_at` is compared to `datetime.now(UTC)`. Events with a start time in the past are discarded before returning. Events with a missing or unparseable start time are included (fail-open to avoid silent drops).

**Important API quirks:**
- `starts_at` is **NOT** at the top level — it is nested under `event_dates_attributes[0].starts_at` (format: `"2026-04-01 19:45:00 -0700"`, space-separated with 4-digit offset, no colon). Parse with `strptime("%Y-%m-%d %H:%M:%S %z")`.
- Ticket tier name is in the `description` field (not `name`) of each `tickets_attributes` entry
- Ticket `price` is in **cents** (e.g. `2500` = $25.00) — divide by 100 to get dollars

Ticket URL is constructed as `https://{url_site}/events/{id}`.

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/api/ninkashi/`

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'ninkashi', 'tickets.myvenue.com', ...);
```

---

### StageTime

| | |
|---|---|
| **Scraper key** | Venue-specific (e.g. `comedy_corner_underground`) |
| **DB field** | `scraping_url` |
| **Value format** | `https://{slug}.stageti.me` |
| **Generic?** | ❌ Custom venue scraper required |

StageTime (stageti.me) is a Next.js ticketing platform. Venues have a subdomain: `{slug}.stageti.me`.

**Data extraction approach:**
1. Fetch the listing page `https://{slug}.stageti.me/` — extract event slugs from `href="/v/{slug}/e/{event-slug}"` anchor links (BeautifulSoup).
2. For each event slug, fetch `https://{slug}.stageti.me/e/{event-slug}`. Event pages embed data in `self.__next_f.push([1,"..."])` RSC wire format segments:
   - JSON-decode the quoted string content
   - Split by newlines — each line is one RSC chunk (`XX:[...]` format)
   - Chunk containing `"occurrences":[` has: event name, isOpenMic, admissionType, occurrences[].startTime (UTC ISO), venue.timezone
   - Chunk with `"id":"event-jsonld"` has: performer names and ticket URL (in `dangerouslySetInnerHTML.__html` as a doubly-escaped JSON-LD string)
3. One event per occurrence; skip `isOpenMic=true` and `admissionType='no_advance_sales'` events.

**Occurrence start times** are UTC ISO strings (`"2026-04-04T01:00:00.000Z"`). Convert to local time via pytz: parse with `%Y-%m-%dT%H:%M:%S.%fZ`, localize to UTC, then convert to `venue.timezone`.

**Test fixtures:** RSC status fields are double-escaped in push segments. To patch a published occurrence to cancelled in a test:
`html.replace('\\"status\\": \\"published\\"', '\\"status\\": \\"cancelled\\"', 1)`

**Reference implementation:** `apps/scraper/src/laughtrack/scrapers/implementations/venues/comedy_corner_underground/`

**DB setup:**
```sql
INSERT INTO clubs (..., scraper, scraping_url, ...)
VALUES (..., 'comedy_corner_underground', 'https://comedycornerunderground.stageti.me', ...);
```

---

### OvationTix

| | |
|---|---|
| **Scraper key** | `uncle_vinnies` (calendar-based) or `four_day_weekend` (direct productions) |
| **DB field** | `scraping_url` |
| **Generic?** | ❌ Venue-specific — production IDs differ per venue |

**Detection signals:**
- Ticket buy links go to `ci.ovationtix.com/{clientId}/production/{id}`
- Network requests to `web.ovationtix.com/trs/api/rest/Production({id})/performance?`

**Two patterns based on how the venue organizes its productions:**

**Pattern 1 — Calendar-based (e.g. Uncle Vinnies)**
- Many production IDs, each representing a single recurring show series
- Discover IDs by scraping the venue's HTML calendar pages (look for `class="tickets-button"` anchors pointing to `ci.ovationtix.com/.../production/{id}`)
- For each production, fetch only `performanceSummary.nextPerformance` (one upcoming date)
- `scraper = 'uncle_vinnies'`

**Pattern 2 — Direct productions (e.g. Four Day Weekend Comedy)**
- Few production IDs on a static buy-tickets page, each with many upcoming performances
- Discover IDs by fetching the venue's buy-tickets page and extracting `ci.ovationtix.com/{clientId}/production/{id}` links
- For each production, use the full `performances[]` array (all upcoming dates)
- `scraper = 'four_day_weekend'` (reuse this key for new venues following this pattern)

**Both patterns** use `Production({id})/performance?` with `clientId` and `newCIRequest: true` headers. The client/org ID appears in the production URL on the venue's buy page.

**Ticket pricing:** fetched via a separate `Performance({id})` call per upcoming show. Response `sections[].ticketTypeViews` provides per-tier pricing. Format the ticket `type` as `f"{ticketGroupName} - {name}"` (e.g. `"General - Adult"`) to match `OvationTixClient._extract_ticket_data()` and avoid dedup key mismatches.

---

### OpenDate

| | |
|---|---|
| **Scraper key** | venue-specific (ref: `sports_drink`) |
| **DB field** | `scraping_url` |
| **Value format** | `https://app.opendate.io/v/{venue-slug}?per_page=500` |
| **Generic?** | ❌ New venue-specific scraper required |

**Detection signals:**
- Venue sells tickets via `app.opendate.io`
- Playwright network inspection shows only analytics/Stripe requests — no JSON API calls
- WebFetch on the listing page returns full event HTML (server-rendered)

**Listing URL format:**
```
https://app.opendate.io/v/{venue-slug}?per_page=500
```
The `?per_page=500` parameter is **required** — the default returns only ~50 events per page with no auto-pagination.

**HTML structure per event card (`div.confirm-card`):**
```html
<div class="card confirm-card">
  <div class="card-body">
    <p class="mb-0 text-dark">
      <a class="text-dark stretched-link" href="https://app.opendate.io/e/{slug}"><strong>{Title}</strong></a>
    </p>
    <p class="mb-0" style="color: #1982c4; ...">April 03, 2026</p>   <!-- date -->
    <p class="mb-0" style="color: #1982c4; ...">Doors: 6:30 PM - Show: 7:00 PM</p>   <!-- time -->
    <p class="mb-0 text-truncate" ...>VENUE NAME • City, ST</p>
  </div>
</div>
```

**Key extraction notes:**
1. The stretched-link `<a>` gives both the event URL (tickets) and title (via `<strong>`)
2. Blue `p.mb-0` paragraphs identified by `color: #1982c4` inline style — first is date, second is time. Exclude `text-dark` and `text-truncate` paragraphs.
3. Extract show time via regex: `Show:\s*(\d{1,2}:\d{2}\s*[AP]M)`. Normalize compact format (`"8:30PM"`) to `"8:30 PM"` before strptime.
4. Date format: `"%B %d, %Y"` (e.g. `"March 29, 2026"`)
5. Event URL doubles as the ticket purchase URL

**To onboard a new OpenDate venue:**
1. Find the venue slug from their OpenDate page URL: `app.opendate.io/v/{slug}`
2. Copy the `sports_drink/` scraper directory as the reference implementation
3. Update the venue slug constant

---

## Implementation Patterns

### Playwright Network Inspection for JS-Heavy Sites

When a venue's show listing is powered by a JavaScript widget (e.g., embedded Crowdwork, SeatGeek, or Tixr), WebFetch may return misleading results (403, missing API calls, or JS-shell content). Use Playwright browser navigation + `browser_network_requests` instead:

1. Navigate to the venue homepage: `browser_navigate`
2. Wait 2–3 seconds for JS to execute: `browser_wait_for time: 3`
3. Capture: `browser_network_requests (includeStatic: false)`
4. Look for non-static, non-analytics API calls — the show-data API is usually a GET to a JSON endpoint

This pattern discovered the PHIT Crowdwork API: `https://crowdwork.com/api/v2/{theatre}/shows`

---

### JS-Rendered Pages Returning HTTP 200 with Shell Content

When a ticketing page returns HTTP 200 but only a JavaScript shell, `BaseScraper.fetch_html()` will NOT trigger the automatic Playwright fallback (that only activates on 403 / empty response / bot-block signatures). The scraper will silently extract zero events.

**Identification:** curl_cffi returns 200 with a large HTML payload (~100–200KB) but BeautifulSoup finds no event containers. Playwright shows event rows populated after DOMContentLoaded — injected by JS.

**Implementation pattern:** override `get_data()` and use the shared `_get_js_browser()` singleton — never instantiate `PlaywrightBrowser()` directly (it leaks a Chromium process per call):

```python
async def _fetch_html_with_js(self, url: str) -> Optional[str]:
    try:
        from laughtrack.foundation.infrastructure.http.client import _get_js_browser
        browser = _get_js_browser()
        if browser is None:
            return None
        return await browser.fetch_html(url)
    except Exception as e:
        Logger.warn(f"MyScraper: Playwright fetch failed for {url}: {e}")
        return None
```

`PlaywrightBrowser` uses `wait_until='domcontentloaded'`. Only use `networkidle` if events are loaded via a post-DOMContentLoaded XHR.

---

### curl_cffi + DataDome — Header Fingerprint Debugging

When a curl_cffi request with `impersonate='chrome124'` succeeds with no custom headers but returns 403 with application headers, DataDome is detecting a specific header combination (never a single header — commonly `Accept-Language + Cache-Control + Pragma` together).

**Diagnostic approach:**
1. Test with no headers → confirm 200
2. Binary search: split your header dict in half and test each half
3. Narrow down to the triggering combo (usually 2–3 headers)

**Fix pattern:** bypass `BaseApiClient.fetch_html` (which always sends `self.headers`) and use a bare `AsyncSession.get(url)`:
```python
async with AsyncSession(impersonate=self._get_impersonation_target(url)) as session:
    response = await session.get(url)  # no extra headers
```
Note: `BaseApiClient.fetch_html(headers=None)` falls back to `self.headers` — passing `None` or `{}` still sends API headers. A separate fetch method is needed to send zero application headers.

---

### Multi-Location Venues — Generalizing Extractor Regexes

When reusing an existing scraper for a second venue location (e.g., Comedy Store La Jolla reusing `comedy_store`), check the extractor's URL pattern regexes for hard-coded path prefixes that may differ between locations.

For example, `^/calendar/show/\d+/(.+)$` only matches West Hollywood hrefs — it must be generalized to `^(?:/[^/]+)?/calendar/show/\d+/(.+)$` before it can handle `/la-jolla/calendar/show/...`.

Before implementing a second location, fetch one day's HTML from the new location and verify every regex in the extractor matches the new URL structure.

---

## Generic vs. Parameterized Summary

| Platform | Scraper Key | Needs Code? | Just set DB fields |
|---|---|---|---|
| Ticketmaster | `live_nation` | No | `ticketmaster_id` |
| Eventbrite | `eventbrite` | No | `eventbrite_id` |
| SeatEngine v1 | `seatengine` | No | `seatengine_id` (numeric) |
| SeatEngine v1 legacy | `seatengine_classic` | No | `seatengine_id` (numeric) |
| SeatEngine v3 | `seatengine_v3` | No | `seatengine_id` (UUID) |
| Tribe Events (WordPress) | `the_rockwell` | No | `scraping_url` |
| rhp-events (WordPress) | `comedy_magic_club` | No | `scraping_url` |
| JSON-LD (generic) | `json_ld` | No | `scraping_url` |
| Prekindle | `json_ld` | No | `scraping_url` |
| Humanitix | `json_ld` | No | `scraping_url` (Humanitix host URL) |
| Ninkashi | `ninkashi` | No | `scraping_url` (tickets subdomain URL) |
| Vivenu | `vivenu` | No | `scraping_url` |
| Tixr | venue-specific | **Yes** — new scraper dir | `scraping_url` |
| Tockify | venue-specific | **Yes** — replace calname | `scraping_url` |
| Squarespace | venue-specific | **Yes** — replace collectionId | `scraping_url` |
| Wix Events | venue-specific | **Yes** — replace compId | `scraping_url` |
| Crowdwork | venue-specific | **Yes** — replace theatre slug | `scraping_url` |
| VBO Tickets | venue-specific | **Yes** — replace UUID | `scraping_url` |
| SquadUP | venue-specific | **Yes** — replace user_id | `scraping_url` |
| Netlify Functions | venue-specific | **Yes** — new scraper dir | `scraping_url` (unused) |
| ThunderTix | venue-specific | **Yes** — new scraper dir (ref: `annoyance`) | `scraping_url` |
| TicketSource | venue-specific | **Yes** — new scraper dir (ref: `comedy_clubhouse`) | `scraping_url` |
| StageTime | venue-specific | **Yes** — new scraper dir | `scraping_url` |
| OvationTix (calendar) | `uncle_vinnies` | **Yes** — replace production IDs | `scraping_url` |
| OvationTix (direct) | `four_day_weekend` | **Yes** — replace production IDs | `scraping_url` |
| OpenDate | venue-specific | **Yes** — ref: `sports_drink` | `scraping_url` |

---

## Onboarding Walkthrough: Tockify Venue

Here is a complete step-by-step example for a fictional new Tockify venue called "The Comedy Loft" with calname `thecomedyloft`.

**Step 1 — Confirm the platform**

Navigate to the venue's show listing page in Playwright:
```
browser_navigate → https://thecomedyloft.com/shows
browser_wait_for  → time: 3
browser_network_requests (includeStatic: false)
```
Look for a request to `tockify.com/api/tagoptions/thecomedyloft`. The `calname` is `thecomedyloft`.

**Step 2 — Test the API directly**
```bash
curl "https://tockify.com/api/ngevent?calname=thecomedyloft&max=200&startms=$(date +%s)000"
```
Confirm events are returned. Note the `customButtonLink` format for ticket URLs.

**Step 3 — Create the scraper**
```bash
cp -r apps/scraper/src/laughtrack/scrapers/implementations/venues/ice_house \
      apps/scraper/src/laughtrack/scrapers/implementations/venues/comedy_loft
```
In `comedy_loft/scraper.py`:
- Change `key = "comedy_loft"`
- Change `_TOCKIFY_BASE_URL` to use `calname=thecomedyloft`

In `comedy_loft/extractor.py`:
- Adjust any venue-specific ticket URL normalization if needed

Add `__init__.py` (empty) to the new directory.

**Step 4 — Add to the DB**
```sql
INSERT INTO clubs (name, scraper, scraping_url, ...)
VALUES ('The Comedy Loft', 'comedy_loft', 'https://thecomedyloft.com/shows', ...);
```

**Step 5 — Verify**
```bash
cd apps/scraper && make scrape-club CLUB='The Comedy Loft'
```
Confirm shows are scraped with correct dates (timestamps ÷ 1000 → seconds), ticket URLs, and comedian names.

---

## Quick Reference: DB Fields by Scraper Key

| Scraper Key | Required DB Fields |
|---|---|
| `live_nation` | `ticketmaster_id` (alphanumeric Discovery API ID) |
| `eventbrite` | `eventbrite_id` (organizer or venue numeric ID) |
| `seatengine` | `seatengine_id` (numeric) |
| `seatengine_classic` | `seatengine_id` (numeric) |
| `seatengine_v3` | `seatengine_id` (UUID) |
| `the_rockwell` | `scraping_url` (Tribe Events REST API base URL) |
| `comedy_magic_club` | `scraping_url` (base `/events/` URL — no pagination) |
| `json_ld` | `scraping_url` (events page with JSON-LD markup, e.g. Prekindle, Humanitix) |
| `ninkashi` | `scraping_url` (tickets subdomain, e.g. `tickets.myvenue.com`) |
| `vivenu` | `scraping_url` (Vivenu seller page root URL) |
| `east_austin_comedy` | `scraping_url` (homepage anchor; unused at runtime) |
| All venue-specific | `scraping_url` (venue calendar page or API URL) |
