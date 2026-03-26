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

None of the above → custom HTML scraper required
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

**DB setup:**
```sql
UPDATE clubs SET scraper = 'eventbrite', eventbrite_id = '30460267696' WHERE name = 'My Club';
```

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
| Tixr | venue-specific | **Yes** — new scraper dir | `scraping_url` |
| Tockify | venue-specific | **Yes** — replace calname | `scraping_url` |
| Squarespace | venue-specific | **Yes** — replace collectionId | `scraping_url` |
| Wix Events | venue-specific | **Yes** — replace compId | `scraping_url` |
| Crowdwork | venue-specific | **Yes** — replace theatre slug | `scraping_url` |
| VBO Tickets | venue-specific | **Yes** — replace UUID | `scraping_url` |
| SquadUP | venue-specific | **Yes** — replace user_id | `scraping_url` |
| Netlify Functions | venue-specific | **Yes** — new scraper dir | `scraping_url` (unused) |

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
bin/scrape 'The Comedy Loft'
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
| `json_ld` | `scraping_url` (events page with JSON-LD markup) |
| `east_austin_comedy` | `scraping_url` (homepage anchor; unused at runtime) |
| All venue-specific | `scraping_url` (venue calendar page or API URL) |
