# TASK-1648 — Audit: Scraper HTTP paths missing Playwright fallback

Date: 2026-04-19
Scope: `apps/scraper/src/laughtrack/` (excluding `foundation/infrastructure/http/` and `tests/`)

## TL;DR

The Playwright fallback documented in CLAUDE.md — "automatic on 403, empty body, or bot-block markers" — is **only** implemented inside `HttpClient.fetch_html` at
`apps/scraper/src/laughtrack/foundation/infrastructure/http/client.py:132-209`.
Every other code path in the scraper that issues an HTTP request is unprotected.

That includes three much larger surfaces than the originally reported Tixr/Etix pair:

1. `HttpConvenienceMixin.fetch_html` / `fetch_json` (`core/data/mixins/http_convenience_mixin.py:72-82, 38-46`) — inherited by **every `BaseScraper` subclass**. `self.fetch_html(url)` does a bare `session.get → raise_for_status → response.text`. 63 scraper files rely on it.
2. `HttpClient.fetch_json` (`foundation/infrastructure/http/client.py:211-253`) — the foundation's own JSON path has no fallback, so `BaseApiClient.fetch_json` (which delegates to it) inherits that gap.
3. `BaseApiClient.post_json` / `post_form` (`core/clients/base.py:319-404, 405-464`) — open their own `AsyncSession` and call `session.post` directly, bypassing `HttpClient` entirely.

The bespoke per-client bypasses called out in the task description are the most acute instances, but fixing only those leaves the generic path broken.

## Category A — Generic paths inherited by many scrapers

### A1. `HttpConvenienceMixin.fetch_html` / `fetch_json`
`apps/scraper/src/laughtrack/core/data/mixins/http_convenience_mixin.py`
- `fetch_json` — line 38-46: `session.get → raise_for_status → response.json()`
- `fetch_html` — line 72-82: `session.get → raise_for_status → response.text`
- `fetch_html_bare` — line 96-99: transient `AsyncSession`, `session.get → raise_for_status → response.text`
- `post_json` — line 117
- `post_form` — line 143

`BaseScraper` inherits this mixin (`scrapers/base/base_scraper.py:32`). Any subclass using `await self.fetch_html(url)` or `await self.fetch_json(url)` is unprotected. Grep shows **85 call sites across 63 scraper files** under `scrapers/implementations/`. The `_fetch_html_with_js` helper on `BaseScraper` (line 156) exists to manually opt into Playwright, but it is never called automatically on 403/bot-block.

**This explains TASK-1647 (Etix Funny Bone wave).** `EtixScraper.get_data` (`scrapers/implementations/api/etix/scraper.py:98`) calls `self.fetch_html(url)` — the mixin path — so a Cloudflare 403 returns `None` with no retry.

Venues affected: **every scraper that subclasses `BaseScraper` and uses `self.fetch_html`/`self.fetch_json`** (effectively the entire catalog). See grep output at the bottom.

### A2. `HttpClient.fetch_json` (foundation)
`apps/scraper/src/laughtrack/foundation/infrastructure/http/client.py:211-253`
Symmetric to `HttpClient.fetch_html` but missing the whole fallback block (lines 180-209 of the `.fetch_html` sibling). Non-200 → `None`, empty body → `None`, no bot-block detection, no Playwright retry.

Callers (via `BaseApiClient.fetch_json` at `core/clients/base.py:186-188`): every API client that subclasses `BaseApiClient`:
- `TixrClient.get_event_detail` (for the api.tixr.com JSON path)
- `SeatEngineClient` (seatengine.com API)
- `TesseraClient` (GET calls that aren't the direct `_fetch_ticket_data`)
- `core/clients/ninkashi/`, `core/clients/opendate/`, `core/clients/prekindle/`, `core/clients/humanitix/`, `core/clients/ovationtix/`, `core/clients/tickettailor/`, `core/clients/ticketsocket/`, `core/clients/showpass/`, `core/clients/showclix/`, `core/clients/ticketsource/`, `core/clients/wix_events/`, etc. (inspect `core/clients/*/client.py` for the list)

### A3. `BaseApiClient.post_json` / `post_form`
`apps/scraper/src/laughtrack/core/clients/base.py:319-404` (`post_json`), `405-464` (`post_form`)
Each opens its own `AsyncSession` and calls `session.post(...)` directly at lines 363 and 450 — no delegation to `HttpClient`, no bot-block retry.

## Category B — Bespoke clients that bypass `BaseApiClient` entirely

### B1. `TixrClient._fetch_tixr_page`
`apps/scraper/src/laughtrack/core/clients/tixr/client.py:168-196`
Opens its own `AsyncSession(impersonate=...)` on line 188, `session.get(url)` on line 189, returns `None` on non-200 (line 191-192). This is the DataDome 403 path called out in the task description.

**Venues affected** (grep for `from laughtrack.core.entities.event.tixr` / `TixrVenueEventTransformer`):
- `improv_asylum` (TASK-1644)
- `st_marks` (TASK-1642)
- `the_stand` (TASK-1641)
- `laugh_boston`
- `haha_comedy_club`

`TixrClient.get_event_detail` also uses `self.fetch_json` (the BaseApiClient path → A2 above), which has the same gap via a different code path.

### B2. `TesseraClient._fetch_ticket_data` + `refresh_session_id`
`apps/scraper/src/laughtrack/core/clients/tessera/client.py:72, 117`
Both open their own `AsyncSession` and call `session.get(...)` directly. Empty 200 responses and non-200s both return `None` with no Playwright retry.

**Venue affected**: `broadway_comedy_club` (only venue using TesseraClient per grep).

### B3. `SquadUpScraper._fetch_events_page`
`apps/scraper/src/laughtrack/scrapers/implementations/api/squadup/scraper.py:68-76`
Opens `AsyncSession(impersonate="chrome124")` on line 68, bare `session.get(url)` on line 69, returns `None` on non-200. Comment on line 55-57 explicitly notes "bare AsyncSession to bypass Cloudflare's TLS fingerprint check" — but no fallback if the bypass fails.

**Venues affected**: clubs with `scraper="squadup"`. `squadup_api` is a generic platform scraper; resolving the venue list requires a DB query (`SELECT name FROM clubs WHERE scraper='squadup'`) — included as a follow-up data point for the per-client fix task rather than inlined here.

### B4. `LiveNationClient.scrape_event_page`
`apps/scraper/src/laughtrack/core/clients/live_nation/client.py:161`
Synchronous `requests.get(event_url, ...)` inside an `async def` method (architectural bug, not just a fallback gap). **Currently unused** — no scraper imports `LiveNationClient` per grep. Flag only; do not file a fix task until it is actually wired up.

## Category C — Shared utilities that issue HTTP calls

### C1. `utilities/infrastructure/paginator/paginator.py` (sync)
Line 140: `self.session.get(current_url, timeout=…)` using the sync `requests.Session`. `raise_for_status` only. Used by `venues/improv/scraper.py`.

### C2. `utilities/infrastructure/paginator/async_paginator.py`
Line 76: `await self.async_session.get(current_url)`, breaks on non-200.

### C3. `utilities/infrastructure/paginator/api_paginator.py`
Lines 68, 128: `await self.session.get(base_url, ...)`, `raise_for_status`.

### C4. `utilities/infrastructure/graphql/client.py`
Line 76: `await session.post(endpoint_url, json=payload, ...)` for GraphQL. POST path — fallback doesn't cleanly apply, but callers are exposed to 403s with no recovery.

### C5. Social/comedian enrichment (non-primary scraping — LOW severity)
- `core/entities/comedian/handler.py`: `_youtube_request` (line 376), `_instagram_request` (line 463), `_tiktok_request` (line 555) — sync `requests.get`. Non-scraping follower refresh; has circuit breaker. Acceptable as-is.
- `core/services/image_sourcing.py`: Wikidata SPARQL + TMDb — sync `requests.get`. Well-behaved APIs, no bot detection. Acceptable.
- `core/clients/google/places.py`, `core/clients/google/custom_search.py`, `core/clients/brave/search.py` — sync `requests.get`. Authenticated SaaS APIs. Acceptable.
- `core/clients/bunny/client.py` — sync `requests.put` for CDN upload. Acceptable.

## Summary table

| ID | Path / client | Library | Fallback? | Venues affected | Severity |
|---|---|---|---|---|---|
| A1 | `HttpConvenienceMixin.{fetch_html,fetch_json,post_json,post_form}` | curl_cffi `AsyncSession` via `get_session` | **NO** | Every `BaseScraper` subclass (~63 files) — incl. EtixScraper (→ TASK-1647) | **HIGH** |
| A2 | `HttpClient.fetch_json` (foundation) | curl_cffi `AsyncSession` | **NO** | Every `BaseApiClient` subclass (Tixr, SeatEngine, Tessera, Ninkashi, OpenDate, Prekindle, Humanitix, OvationTix, TicketTailor, TicketSocket, Showpass, ShowClix, TicketSource, Wix Events, …) | **HIGH** |
| A3 | `BaseApiClient.post_json` / `post_form` | curl_cffi `AsyncSession` direct | **NO** | Every client using POST (Crowdwork, Humanitix auth, GraphQL clients) | MEDIUM |
| B1 | `TixrClient._fetch_tixr_page` | curl_cffi `AsyncSession` direct | **NO** | improv_asylum, st_marks, the_stand, laugh_boston, haha_comedy_club | **HIGH** (→ TASK-1641/1642/1644) |
| B2 | `TesseraClient._fetch_ticket_data` / `refresh_session_id` | curl_cffi `AsyncSession` direct | **NO** | broadway_comedy_club | MEDIUM |
| B3 | `SquadUpScraper._fetch_events_page` | curl_cffi `AsyncSession` direct | **NO** | clubs with scraper=squadup (query DB) | MEDIUM |
| B4 | `LiveNationClient.scrape_event_page` | sync `requests` in async | **NO** | none (unused) | LOW (flag only) |
| C1 | sync `Paginator` | sync `requests` | **NO** | improv | LOW |
| C2 | `AsyncPaginator` | curl_cffi session | **NO** | any scraper threading its session through | LOW |
| C3 | `ApiPaginator` | curl_cffi session | **NO** | ditto | LOW |
| C4 | `GraphQLClient` | curl_cffi session POST | N/A for POST | GraphQL scrapers | LOW |
| C5 | social/image/search (sync `requests`) | sync `requests` | **NO** | non-scraping enrichment | NONE (safe APIs) |

## Follow-up fix tasks

Per-client fix tasks filed as part of TASK-1648 closure (see "Per-client fix tasks" progress note for IDs):
- A1 — unify `HttpConvenienceMixin.fetch_html` / `fetch_json` with the foundation's fallback (highest blast radius)
- A2 — port the Playwright fallback from `HttpClient.fetch_html` into `HttpClient.fetch_json`
- A3 — add 403/bot-block handling to `BaseApiClient.post_json` / `post_form`
- B1 — refactor `TixrClient._fetch_tixr_page` to delegate to `HttpClient.fetch_html` (explicitly keeping the no-app-headers behavior)
- B2 — same treatment for TesseraClient
- B3 — same treatment for SquadUpScraper
- C1 — migrate sync `Paginator` to the async path (isolated to Improv)

B4 (LiveNationClient) is flagged but not actionable until the client is wired into a scraper.

## Reference

Working `fetch_html` fallback implementation: `apps/scraper/src/laughtrack/foundation/infrastructure/http/client.py:180-209`. Triggers: `html is None`, `not html.strip()`, or `_bot_block_reason(html)`. Gated by `PLAYWRIGHT_FALLBACK` env var (default on).
