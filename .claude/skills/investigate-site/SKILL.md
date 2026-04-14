---
name: investigate-site
description: "Deep-inspect a venue URL with Playwright MCP — captures network requests, identifies ticketing platform, and reports API endpoints. Usage: /investigate-site <url>"
allowed-tools: Bash, Read, Grep, Glob, WebFetch, Agent
---

# Investigate Site

Open a venue URL in Playwright MCP, capture all network requests, inspect page
source / bootstrap JSON, and report what ticketing platform and API endpoints are
available. Designed to catch JS-only APIs that static HTML inspection misses
(e.g., Square Online JSON API, Crowdwork widget, Wix Events).

## Usage

```
/investigate-site https://www.examplecomedy.com/shows
/investigate-site https://www.examplecomedy.com
```

## Arguments

- **URL** (required) — the venue's events/shows page to inspect. If only the homepage
  is given, navigate to the events/shows page first.

## Step 1: Navigate to the Page

Open the URL in Playwright MCP and wait for the page to fully load:

```
browser_navigate → <url>
```

If the page redirects, note the final URL.

If navigation fails (Chrome conflict — "Opening in existing browser session"), inform
the user:

> Playwright MCP failed — Chrome is already running with a conflicting profile.
> Close Chrome and retry, or I can fall back to WebFetch (limited to static HTML).

## Step 2: Find the Events Page

If the URL is a homepage (no `/shows`, `/events`, `/calendar`, `/tickets`, `/schedule`
in the path), take a snapshot and look for navigation links:

```
browser_snapshot
```

Look for links labeled "Shows", "Events", "Calendar", "Tickets", or "Schedule".
If found, navigate to that page:

```
browser_click → <events link ref>
```

## Step 3: Capture Network Requests

After the events page is loaded, capture all network requests made by the page:

```
browser_network_requests
```

## Step 4: Analyze Network Requests

Scan the captured requests for known API patterns. Categorize matches by platform:

### Club-Hosted APIs (preferred — show_page_url stays on venue site)

| Network request pattern | Platform | Notes |
|------------------------|----------|-------|
| `/wp-json/tribe/events/v1/events` | Tribe Events (WordPress) | REST API, paginated |
| `/api/open/GetItemsByMonth` | Squarespace | Calendar widget API |
| `crowdwork.com/api/v2` | Crowdwork | Embedded ticket widget |
| `tockify.com/api/` | Tockify | Calendar embed |
| `plugin.vbotickets.com` | VBO Tickets | Ticket widget |
| `/.netlify/functions/` | Netlify Functions | Custom serverless API |
| `editmysite.com/app/store/api/` | Square Online (Weebly) | Product/event API |
| `app.showslinger.com` | ShowSlinger | Embedded widget |
| `showpass.com/api/public/venues/` | Showpass | Venue events API |
| `wixstatic.com` / `wix-events` | Wix Events | Client-side widget |
| `stageti.me` | StageTime | RSC segments |
| `app.opendate.io` | OpenDate | Booking widget |

### Third-Party Aggregator APIs (fallback)

| Network request pattern | Platform | Notes |
|------------------------|----------|-------|
| `ticketmaster.com` / `livenation.com` | Ticketmaster/Live Nation | Discovery API |
| `eventbrite.com` or `evbqa.com` | Eventbrite | Organizer/venue API |
| `seatengine.net` or `seatengine.com` | SeatEngine | Venue shows API |
| `api.ninkashi.com` | Ninkashi | Ticket platform |
| `vivenu` | Vivenu | Seller page API |
| `tixr.com` | Tixr | Event API |
| `prekindle.com` | Prekindle | Ticket platform |
| `thundertix.com` | ThunderTix | Ticket platform |

### Generic Patterns (any JSON endpoint returning event data)

Also flag any request that returns JSON containing arrays of objects with date-like
fields (`date`, `start_time`, `event_date`, `starts_at`, etc.) — these may be custom
APIs not in the tables above.

## Step 5: Inspect Page Source for Static Patterns

Take a page snapshot to check for non-API patterns embedded in HTML:

```
browser_snapshot
```

Look for:

| Source pattern | Platform |
|---------------|----------|
| `var all_events = [...]` + `tw-plugin-calendar` | TicketWeb (WordPress) |
| `<script type="application/ld+json">` with `"@type": "Event"` | JSON-LD |
| `rhpSingleEvent` / `rhp-event__title--list` | rhp-events (WordPress) |
| `self.__next_f.push` + `stageti.me` | StageTime (Next.js RSC) |
| `app.opendate.io` / `confirm-card` | OpenDate |
| `data-compId` on Wix widget | Wix Events |
| `squadup = { userId:` | SquadUP |
| `showpass.com/widget/` iframe | Showpass |
| `app.showslinger.com` iframe / `promo_widget_v3` | ShowSlinger |

## Step 6: Sample API Data (Optional)

If a promising API endpoint was found in Step 4, fetch it directly to confirm it
returns usable event data:

```bash
cd apps/scraper && .venv/bin/python3 -c "
import ssl, urllib.request, json
ctx = ssl.create_default_context()
ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
with urllib.request.urlopen('<api_url>', context=ctx) as r:
    data = json.loads(r.read())
print(type(data), len(data) if isinstance(data, list) else 'dict')
import json as j; print(j.dumps(data if isinstance(data, list) and len(data) <= 3 else data[:3] if isinstance(data, list) else data, indent=2, default=str)[:2000])
"
```

This confirms the API is publicly accessible and shows the response structure.

## Step 7: Report Results

Present findings in this format:

```
Investigate Site Results
━━━━━━━━━━━━━━━━━━━━━━━
URL:              <final URL after redirects>
Platform:         <detected platform name, or "Unknown / No platform detected">
API Endpoints:    <list of discovered API URLs>
Data Available:   <yes/no — does the API return event data?>
Static Patterns:  <any HTML-embedded patterns found>
Sample Events:    <count of events in API response, if sampled>

Recommendation:
  <one of:>
  - Use generic scraper: <scraper_key> (e.g., json_ld, eventbrite, live_nation)
  - Build venue-specific scraper for <platform> (reference: <existing venue>)
  - No scrapable data found — venue may not sell tickets online
  - Site uses <platform> but API returns 0 events — shows may not be on sale yet
```

## Integration with /adopt-scraper

This skill is called by `/adopt-scraper` at Step 2e before concluding a platform is
unsupported. When invoked in that context, the report feeds directly into the
adopt-scraper's platform decision — no need to repeat the research.

When used standalone, the user can act on the recommendation manually or invoke
`/adopt-scraper <club name>` to proceed with onboarding.
