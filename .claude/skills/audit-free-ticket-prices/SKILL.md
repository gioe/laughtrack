---
name: audit-free-ticket-prices
description: Investigate clubs with suspiciously many Free or 0.00 tickets by comparing persisted rows, scraper code, raw source payloads, and rendered purchase pages; conclude whether shows are truly free or prices are not being scraped, and optionally create a tusk bug task.
allowed-tools: Bash, Read, Glob, Grep, WebSearch, WebFetch, Task
---

# Audit Free Ticket Prices

Use this when a club has too many shows tagged `Free`, many `tickets.price = 0.00` rows, or a user asks whether a specific "free" show is actually free.

Goal: prove whether the source really sells free tickets, or whether the scraper is defaulting to `0.0` because it does not parse price data.

## Ground Rules

- Investigate one club at a time unless the user explicitly asks for a batch.
- Before editing or creating tasks, query relevant conventions:
  - `./.claude/bin/tusk conventions search "scraper price"`
  - `./.claude/bin/tusk conventions search "<club name>"`
  - `./.claude/bin/tusk conventions inject apps/scraper`
- Do not use plain `requests` or `urllib` to decide whether a ticket page is fetchable. Use the scraper's HTTP stack or Playwright browser flow.
- For JSON/API response shape and item counts, use direct HTTP/client calls, not summarized WebFetch.
- Treat `ShowFactoryUtils.create_fallback_ticket(...)` with no explicit `price` as suspicious: it defaults to `0.0`, which maps to the `FREE` price tag.
- Prefer direct evidence from the source payload or rendered checkout page over assumptions from event titles.

## Step 1: Identify Sample Rows

Query future shows for the club, including ticket rows and source attribution.

From repo root:

```bash
cd apps/scraper
PYTHONPATH=src .venv/bin/python3 -c '
from dotenv import load_dotenv
load_dotenv()
from laughtrack.infrastructure.database.connection import get_connection

club_name = "<CLUB NAME>"
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                s.id, s.name, s.date, s.show_page_url, s.last_scraped_by,
                t.price, t.purchase_url, t.type, t.sold_out
            FROM shows s
            JOIN clubs c ON c.id = s.club_id
            LEFT JOIN tickets t ON t.show_id = s.id
            WHERE c.name = %s
              AND s.date > NOW()
            ORDER BY s.date ASC, s.id ASC
            LIMIT 20
        """, (club_name,))
        for row in cur.fetchall():
            print(row)
'
```

If DNS/network fails in the sandbox, rerun with elevated permissions. This is read-only DB inspection.

Pick at least one ordinary paid-looking show with `price = 0.00`; avoid titles that clearly imply open mic, comp, RSVP, or community/free events unless the user asked about that exact row.

## Step 2: Locate the Scraper Path

Search by club and scraper key:

```bash
rg -n -i "<club name>|<scraper_key>|<purchase host>|free|price|ticket" apps/scraper/src apps/scraper/tests apps/web/prisma
```

Read the venue scraper, extractor, transformer, event entity, and focused tests. Answer:

- Where does the purchase URL come from?
- Does the raw payload include price fields?
- Does the entity store price fields?
- Does `to_show()` create real `Ticket` objects or fallback tickets?
- Does any test assert non-zero price behavior?

Also inspect these shared defaults when relevant:

- `apps/scraper/src/laughtrack/utilities/domain/show/factory.py` for `create_fallback_ticket`.
- `apps/scraper/src/laughtrack/core/entities/ticket/model.py` for `price_tag`.

## Step 3: Fetch Source Payload With the Scraper Stack

Use the same fetch path the scraper uses. For HTML pages that may need JS/bot bypass, use `PlaywrightBrowser`:

```bash
cd apps/scraper
PYTHONPATH=src .venv/bin/python3 -c '
import asyncio
from laughtrack.foundation.infrastructure.http.playwright_browser import PlaywrightBrowser

url = "<SOURCE OR LISTING URL>"

async def main():
    browser = PlaywrightBrowser()
    html = await browser.fetch_html(url)
    print("html_length", len(html or ""))
    print((html or "")[:1000])
    await browser.close()

asyncio.run(main())
'
```

If the venue has an extractor, prefer importing and running it against the fetched HTML so the investigation uses the production parser:

```bash
cd apps/scraper
PYTHONPATH=src .venv/bin/python3 -c '
import asyncio, json
from laughtrack.foundation.infrastructure.http.playwright_browser import PlaywrightBrowser
from laughtrack.scrapers.implementations.venues.<module>.extractor import <Extractor>

target_id_or_slug = "<ID OR SLUG FROM PURCHASE URL>"

async def main():
    browser = PlaywrightBrowser()
    html = await browser.fetch_html("<LISTING URL>")
    events = <Extractor>.extract_shows(html or "")
    print("events", len(events))
    for event in events:
        if target_id_or_slug in str(event):
            print(json.dumps(event, indent=2, ensure_ascii=False)[:12000])
            print("price-like keys", [k for k in event.keys() if "price" in k.lower() or "ticket" in k.lower() or "fee" in k.lower()])
            break
    await browser.close()

asyncio.run(main())
'
```

Record exact field names, units, and sold-out/remaining semantics. Common shapes include cents integers (`2000` means `20.00`) and tier arrays where sold-out tiers must be ignored.

## Step 4: Inspect the Purchase Page

If the source payload has no obvious price, render the purchase URL and accept cookie gates if necessary:

```bash
cd apps/scraper
.venv/bin/python3 -c '
import asyncio, re
from playwright.async_api import async_playwright

url = "<PURCHASE URL>"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        for label in ["Accept all", "Accept All", "Accepteren", "I agree", "Agree"]:
            try:
                await page.get_by_text(label, exact=True).click(timeout=3000)
                print("clicked", label)
                break
            except Exception:
                pass
        await page.wait_for_timeout(5000)
        text = await page.locator("body").inner_text(timeout=10000)
        text = re.sub(r"\s+", " ", text)
        print("URL", page.url)
        print(text[:5000])
        for match in re.finditer(r".{0,120}(?:\$|€|free|gratis|eur|usd|price|total|ticket).{0,160}", text, flags=re.I):
            print("MATCH", match.group(0))
        await browser.close()

asyncio.run(main())
'
```

If the page only shows a cookie shell or JS shell, use Playwright interaction rather than treating the page as price-less.

## Step 5: Decide Whether It Is Truly Free

Classify the result:

- **Actually free:** source payload or rendered checkout explicitly says free/gratis/0.00 for available tickets.
- **Price not scraped:** DB has `0.00`, but source payload or purchase page shows a non-zero available ticket price.
- **Unknown:** purchase/source page cannot be rendered or price is hidden until a checkout step that should not be automated.

When the result is "price not scraped", identify the likely implementation gap:

- Raw price fields are extracted but discarded.
- Raw price fields are not extracted by the venue extractor.
- Entity lacks price/tier fields.
- `to_show()` uses `create_fallback_ticket()` without passing price.
- Tests only assert ticket URL presence, not price.

## Step 6: Optional Task Creation

If the user wants a task, use `/create-task` or `./.claude/bin/tusk task-insert` after checking duplicates:

```bash
./.claude/bin/tusk dupes check "Scrape <club> ticket prices from <source field>"
```

Task shape:

- Priority: `High` when paid shows are visible as free.
- Domain: `scraper`
- Type: `bug`
- Complexity: usually `S` for one venue, `M` if platform-generic.
- Description: include stable field names and source URLs, not line-number anchors.
- Criteria: prefer typed pytest criteria for entity conversion, sold-out tier handling, scraper mapping, and focused venue test suite.

## Report Format

End with:

```markdown
Club: <name>
Sample show: <show id/name/date>
Persisted ticket: <price/type/purchase_url>
Source evidence: <raw field or rendered checkout text>
Classification: <actually free | price not scraped | unknown>
Root cause: <specific code path or data gap>
Recommended action: <none | task id | proposed task summary>
```
