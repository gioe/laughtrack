# TASK-1647 — Audit: Etix.com DataDome CAPTCHA block on Funny Bone chain

Date: 2026-04-20
Scope: the 17 clubs that started returning HTTP 403 in waves between 2026-04-16 and 2026-04-19 (nightly runs).

## TL;DR

The "Funny Bone 403 wave" is a **single-platform incident**: 16 of the 17 affected clubs are hosted on etix.com, which has deployed a DataDome *visible* CAPTCHA challenge (`title="DataDome CAPTCHA"`, iframe → `geo.captcha-delivery.com`). Neither `curl-cffi` impersonation (any profile) nor the project's Playwright stealth browser defeats it — both paths receive the CAPTCHA interstitial. The TASK-1441 "bare curl-cffi without app-level headers" trick (which broke Tixr's DataDome in October) **does not help here** — etix.com is blocking at the TLS-fingerprint / IP-reputation layer, before request headers are even evaluated.

McCurdy's Comedy Theatre (1 of 17) is a separate, unrelated incident — its own site `www.mccurdyscomedy.com` loads cleanly via Playwright (54 KB, no bot-block markers).

## Affected clubs

Source: nightly metrics 2026-04-16 through 2026-04-19.

### Etix-platform (16 clubs, scraper=`etix`)
| ID | Club | Scraping URL |
|----|------|---|
| 207 | Dr. Grins Comedy Club | etix.com/ticket/v/35455/... |
| 308 | Funny Bone Columbus | etix.com/ticket/v/31594/... |
| 317 | Dayton Funny Bone | etix.com/ticket/v/31595/... |
| 323 | Albany Funny Bone | etix.com/ticket/v/31591/... |
| 332 | Laugh Patriot Place | etix.com/ticket/v/32411/... |
| 1026 | Omaha Funny Bone | etix.com/ticket/v/31598/... |
| 1027 | Orlando Funny Bone | etix.com/ticket/v/31599/... |
| 1028 | Syracuse Funny Bone | etix.com/ticket/v/31436/... |
| 1029 | Zanies Comedy Night Club | etix.com/ticket/v/21745/... |
| 1030 | Des Moines Funny Bone | etix.com/ticket/v/28453/... |
| 1033 | Virginia Beach Funny Bone | etix.com/ticket/v/31602/... |
| 1034 | Richmond Funny Bone | etix.com/ticket/v/31601/... |
| 1048 | The Moon | etix.com/ticket/v/14500/... |
| 1050 | Cleveland Funny Bone | etix.com/ticket/v/31603/... |
| 1053 | Tampa Funny Bone | etix.com/ticket/v/31600/... |
| 1353 | The Lounge at World Stage | etix.com/ticket/v/26727/... |

### Separate (1 club, scraper=`mccurdys_comedy_theatre`)
| ID | Club | Scraping URL |
|----|------|---|
| 1025 | McCurdy's Comedy Theatre | mccurdyscomedy.com/shows/ |

McCurdy's was already 403ing for 7 days before the rest of the wave started — it shares nothing with the Etix clubs and must be investigated separately (see follow-up TASK-1660).

## Evidence

### 1. `curl-cffi` is blocked for every impersonation profile

```
chrome124:  status=403 dd=True  preview=<html lang="en"><head><title>etix.com</title>...
chrome131:  status=403 dd=True  preview=<html lang="en"><head><title>etix.com</title>...
chrome120:  status=403 dd=True  preview=<html lang="en"><head><title>etix.com</title>...
safari17_0: status=403 dd=True  preview=<html lang="en"><head><title>etix.com</title>...
chrome116:  status=403 dd=True  preview=<html lang="en"><head><title>etix.com</title>...
```

Command (bare `AsyncSession`, no extra headers):
```python
async with AsyncSession(impersonate=prof, timeout=20) as s:
    r = await s.get("https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=31594&orderBy=1&pageNumber=1")
```

All responses are the DataDome interstitial, 1.5 KB of HTML whose `<title>` is `etix.com` and body begins with:
```html
<script data-cfasync="false">var dd={'rt':'c','cid':'...','hsh':'...','t':'bv','qp':'','s':59502,...,'host':'geo.captcha-delivery.com'}</script>
<script data-cfasync="false" src="https://ct.captcha-delivery.com/c.js"></script>
<iframe src="https://geo.captcha-delivery.com/captcha/?initialCid=...&hash=...&t=bv&referer=...&s=59502&..." title="DataDome CAPTCHA" width="100%" height="100%">
```

The `t:'bv'` parameter is DataDome's "block-visible" mode — a rendered CAPTCHA the user must solve. Not `t:'it'` (interstitial) or `t:'cc'` (cookie challenge), which the passive JS path could clear.

### 2. Playwright (current stealth stack) is also blocked

Tested via `PlaywrightBrowser().fetch_html(url)` against three Etix URL shapes (venue MVC endpoint, public venue page, legacy `venueSearch.jsp`). All three return the same 1.5 KB DataDome CAPTCHA interstitial:

```
https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=31594&...
  len=1558 datadome=True title='etix.com'
https://www.etix.com/ticket/v/31594/funny-bone-comedy-club-columbus
  len=1514 datadome=True title='etix.com'
https://www.etix.com/ticket/online/venueSearch.jsp?venue_id=31594
  len=1514 datadome=True title='etix.com'
```

`columbus.funnybone.com` (and every other `{city}.funnybone.com` subdomain referenced from funnybone.com's homepage — albany, cleveland, dayton, desmoines, hartford, kc, liberty, omaha, orlando, richmond, syracuse, tampa, toledo, vb) behaves identically. Those subdomains are thin shells around the Etix widget; they inherit the same block.

Project Playwright stealth already applies: `--disable-blink-features=AutomationControlled` (TASK-1657), `navigator.webdriver` removal, spoofed `navigator.plugins` / `navigator.languages`, canvas-fingerprint noise, and an 8 s AWS-WAF challenge wait. None of these evasions address DataDome's visible CAPTCHA — the challenge requires *solving* the CAPTCHA, not *passing* a passive check.

### 3. The HttpClient fallback IS firing (not the bug)

Full scrape log for Funny Bone Columbus (`make scrape-club CLUB='Funny Bone Columbus'`):

```
WARNING | HTTP 403 when fetching https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=31594&...
INFO    | [HttpClient] Triggering Playwright fallback for ... (reason: 'HTTP 403')
INFO    | EtixScraper [Funny Bone Columbus]: discovered 1 page(s) of events
INFO    | EtixScraper [Funny Bone Columbus]: no events found on ...
INFO    | EtixScraper [Funny Bone Columbus]: Scraped 0 total shows
```

The curl-cffi → Playwright fallback (TASK-1649 delegation + `HttpClient.fetch_html:180-209`) triggers correctly. It's the Playwright fetch itself that comes back with CAPTCHA HTML, which the Etix parser correctly reports as "no events found". So the scraper's retry infrastructure is fine — it's the terminal bypass capability that's missing.

### 4. funnybone.com main site is clean, but has no scraper-useful content

`https://funnybone.com` loads cleanly via Playwright (~666 KB, `<title>Funny Bone Comedy Clubs</title>` JSON-LD schema). But:
- All location links on the page point back to `{city}.funnybone.com` → etix-backed (blocked).
- The site runs Rockhouse Partners' `rhp-events` WordPress plugin, but `admin-ajax.php?action=rhp_events_list` (and the expected plugin-action variants) return `0` (invalid action, no data).
- `/sitemap.xml`, `/sitemap_index.xml`, `/wp-sitemap.xml` are all empty.

There is no alternate event feed discoverable from the main site without credentialed access to the WP admin.

## Root cause

**Etix.com has enabled DataDome visible-CAPTCHA (mode `bv`) on 2026-04-16, affecting all public show-listing and venue endpoints.** Rollout was gradual (waves over 3 days) so venues flipped from working to 403 in batches as DataDome's edge config propagated.

This is platform-wide, not Funny-Bone-specific. Any other Etix-hosted venue we add in the future will hit the same block until DataDome is bypassed.

## Why existing bypass patterns don't apply

| Pattern | Where it worked | Why it doesn't work on Etix |
|---|---|---|
| TASK-1441 bare `curl-cffi` (no app-level headers) | Tixr SuperNova — DataDome was sniffing custom headers | Etix blocks at TLS fingerprint / IP reputation; removing headers changes nothing |
| TASK-1657 `--disable-blink-features=AutomationControlled` | AWS WAF passive JS challenge | DataDome uses an interactive CAPTCHA, not a passive JS check |
| TASK-1649 Playwright fallback delegation | Any site with a passive challenge | Playwright renders the CAPTCHA but cannot solve it |

## Options considered

### (a) Build a DataDome CAPTCHA solver path
- Integrate `2captcha`, `anti-captcha`, or `capsolver` as a paid backstop in `HttpClient`.
- Estimated cost: $2–3 per 1,000 solves. At ~30 daily fetches across 16 venues that's ~$1.50/month — acceptable.
- Engineering: ~2–3 days. Requires extending `PlaywrightBrowser` to detect DataDome iframe, post the sitekey to the solver API, inject the returned token, submit the form, and retry the origin request. Reference: `capsolver` has a DataDome-specific endpoint; `2captcha` requires a more generic interactive flow.
- **Recommended path** — it future-proofs the scraper for any site that adopts DataDome (already affects Tixr, now Etix; next likely targets: Ticketmaster, AXS, OVG-tier venues).

### (b) Residential proxy + stealth v2 rotation
- Switch Playwright to route through a residential proxy pool (e.g. Bright Data, Oxylabs) with per-request rotation.
- Cost: $5–15 per GB depending on provider; for HTML-only scraping this is ~$10/month.
- Engineering: ~1–2 days, but may not clear `t:'bv'` challenges reliably — DataDome flags residential IPs with abnormal request patterns too.
- **Not recommended as primary** — probabilistic, slower, and doesn't solve the CAPTCHA problem root.

### (c) Find alternate platform per venue
- Run `/adopt-scraper` on each of the 16 clubs to see if they also publish on Ticketmaster, Eventbrite, or a sibling rhp-events-served feed.
- Historically: Funny Bone uses Etix exclusively for ticketing, so yield is expected to be low — but worth spot-checking 2–3 clubs before committing.
- **Recommended as parallel track** — cheap insurance; some venues may have since migrated.

### (d) Hide the affected clubs
- `visible=false` via migration for all 16 clubs until a bypass lands.
- Downside: removes them from the site for weeks/months (stale total_shows, dead URLs if a user has them bookmarked).
- **Recommended only as last resort** if (a) and (c) both fail.

## Recommendation

Do (a) + (c) in parallel:

1. **TASK-1658** — Build DataDome CAPTCHA solver integration into `PlaywrightBrowser` (scraper, highest priority). Gates the recovery of all 16 clubs + future Etix venues.
2. **TASK-1659** — Spot-check `/adopt-scraper` for 3 representative Etix venues (Funny Bone Columbus 308, Dr. Grins 207, The Moon 1048) to confirm Etix is still their only platform. If any has migrated, onboard the new platform instead.
3. **TASK-1660** — Investigate McCurdy's Comedy Theatre HTTP 403 separately — its site loads cleanly via Playwright, so the scraper's own HTTP path is the bug, not a bot-block.

If TASK-1658 slips past 2 weeks, escalate to (d) and hide the 16 clubs until it lands.

## Spot-check results (TASK-1659 follow-ups)

### Dr. Grins Comedy Club (207) — TASK-1662, 2026-04-20

**Conclusion: Etix remains the only platform. No migration possible. Recovery depends on TASK-1658.**

- Club's own site (`thebob.com/drgrins`) is a static page with "Buy Tickets" links
  pointing directly at `etix.com/ticket/v/35455/drgrins-comedy-club-at-the-bob` —
  no embedded event data, no JSON-LD events (only a `Restaurant` block for The BOB).
- `grinstix.com` (the venue's marketing domain) 301-redirects to the same Etix
  venue_id=35455 URL.
- Ticketmaster Discovery API returns the venue (`venueId=ZFr9jZ11kk`) but only
  5 events, all the same comedian (Brian Simpson, Dec 3–5 2026). The secondary
  venue record `KovZpZAFAElA` ("The B.O.B. - Dr. Grin's") is the LaughFest
  festival listing with 0 upcoming events. Not a viable replacement for the
  full calendar (~60 shows historically).
- AXS has a venue page (`axs.com/venues/133204/...`) but it 403s from our stack
  and is functionally a ticket-resale mirror, not the primary sales channel.

Local reproduction (2026-04-20) matches the audit's core finding: fetch falls
back to Playwright, Playwright returns the DataDome CAPTCHA interstitial,
parser correctly reports "no events found":

```
WARNING | HTTP 403 when fetching https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=35455&...
INFO    | [HttpClient] Triggering Playwright fallback for ... (reason: 'HTTP 403')
INFO    | DrGrinsScraper: no events found on ...
INFO    | DrGrinsScraper: Scraped 0 total shows
```

## Reproduction pointers

```bash
# Reproduce the 403 through the full scraper stack
cd apps/scraper && make scrape-club CLUB='Funny Bone Columbus'

# Verify bare curl-cffi is blocked across all profiles
cd apps/scraper && .venv/bin/python3 -c "
import asyncio
from curl_cffi.requests import AsyncSession
async def t():
    url = 'https://www.etix.com/ticket/mvc/online/upcomingEvents/venue?venue_id=31594&orderBy=1&pageNumber=1'
    for prof in ['chrome124','chrome131','chrome120','safari17_0','chrome116']:
        async with AsyncSession(impersonate=prof, timeout=20) as s:
            r = await s.get(url); print(f'{prof}: status={r.status_code} dd={\"datadome\" in r.text.lower()}')
asyncio.run(t())
"

# Verify Playwright stealth is blocked
cd apps/scraper && .venv/bin/python3 -c "
import asyncio, sys; sys.path.insert(0, 'src')
from laughtrack.foundation.infrastructure.http.playwright_browser import PlaywrightBrowser
async def t():
    b = PlaywrightBrowser()
    html = await b.fetch_html('https://www.etix.com/ticket/v/31594/funny-bone-comedy-club-columbus')
    print(f'len={len(html)} datadome={\"datadome\" in html.lower()}')
    await b.close()
asyncio.run(t())
"
```
