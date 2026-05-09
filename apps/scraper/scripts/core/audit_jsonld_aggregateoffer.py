"""TASK-2047: Audit JSON-LD scrapers for AggregateOffer ticket-extraction bug.

Background
----------
TASK-2028 (commit d7e2ba64) fixed the shared JsonLdEvent._parse_offers parser to
read AggregateOffer.lowPrice / highPrice when the offer's price field is empty.
Before that fix, every venue using the shared JSON-LD parser (JsonLdEvent.from_json_ld
-> _parse_offers) silently dropped tickets for any event whose JSON-LD emitted a
single AggregateOffer rather than a concrete Offer with a price field.

For Uptown Theater (club_id=80) that meant 10 of 13 future shows persisted with
zero tickets. Other venues using the same parser may have the same issue.

What this script does
---------------------
1. Lists all active+visible clubs whose enabled scraping_sources point at a
   scraper_key that uses JsonLdEvent (the shared parser).
2. For each candidate club, counts future shows (date >= now()) and how many
   future shows have zero rows in tickets.
3. Surfaces clubs with >50% of future shows missing tickets — these are likely
   AggregateOffer-affected (or otherwise upstream-data-limited) and should be
   re-checked with a live PlaywrightBrowser probe.

Candidate scraper_keys are discovered at runtime by walking every BaseScraper
subclass via ScraperResolver and checking whether its package directory
references the `JsonLdEvent` symbol. Previously this was a hand-maintained
tuple that silently went stale every time a venue was folded into or out of
the shared JSON-LD parser (e.g. TASK-2068 dropped brew_haha_river; TASK-2079
/2082/2083 are in flight).

Usage
-----
    cd apps/scraper && make run-script SCRIPT=scripts/core/audit_jsonld_aggregateoffer.py
or
    cd apps/scraper && .venv/bin/python scripts/core/audit_jsonld_aggregateoffer.py

Re-run after the next nightly scrape post-deploy of TASK-2028 to verify that
tickets now populate for the listed venues.

Live probe results (2026-05-08, post-TASK-2028-deploy)
------------------------------------------------------
SQL audit verified TASK-2028's fix in production:
  uptown_theater (club_id=80): 0 / 15 future shows missing tickets
  (down from 10 / 13 at the time TASK-2028 was filed)

Two new clubs surfaced under scraper_key='json_ld', both at 18 / 18 future shows
missing tickets (100%). PlaywrightBrowser probe of each venue's listing page
(the scraper's source_url) and one event detail page:

  club_id=435  Comedy on State           https://www.madisoncomedy.com/events/
    Listing JSON-LD: 19 Event nodes, every one missing the 'offers' field
    entirely. Per-Event keys: @context, @type, description, endDate,
    eventAttendanceMode, eventStatus, image, location, name, organizer.
    No price, lowPrice, highPrice, or offers list anywhere in the JSON-LD.
    → UPSTREAM-DATA-LIMITED. Site (WordPress + The Events Calendar plugin)
      simply does not emit ticket pricing in schema.org markup. TASK-2028's
      AggregateOffer-fallback cannot help — there is no offer object to read.

  club_id=410  Let's Comedy Venues       https://www.letscomedyftw.com/events
    Listing JSON-LD: only a single Place node (no Event nodes at all).
    Detail page JSON-LD: 1 Event node with keys @context, @type, description,
    image, location, name, startDate, url. No offers field.
    → UPSTREAM-DATA-LIMITED. Same conclusion: no JSON-LD offers anywhere.

Triage recommendation: file a separate task per venue to either (a) build a
custom HTML extractor that pulls price from the page body / ticket-button URL,
or (b) accept that JSON-LD ingestion can't populate tickets for these venues
and document the limitation in scraping_sources.metadata. Tracking these in a
follow-up rather than expanding TASK-2028's scope keeps the AggregateOffer fix
narrowly scoped to its actual root cause.
"""

import inspect
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_connection  # noqa: E402
from laughtrack.app.scraper_resolver import ScraperResolver  # noqa: E402

_JSON_LD_MARKER = "JsonLdEvent"


def discover_json_ld_scraper_keys() -> list[str]:
    """Return scraper keys whose implementation package references JsonLdEvent.

    Walks every BaseScraper subclass discovered by ScraperResolver and scans
    each scraper's source directory for the JsonLdEvent symbol — the canonical
    marker that the scraper feeds JSON-LD into the shared parser. This avoids
    the previous hand-maintained tuple, which silently went stale every time a
    venue was folded into or out of the shared parser.
    """
    resolver = ScraperResolver()
    keys: list[str] = []
    for key, cls in resolver.items():
        try:
            package_dir = Path(inspect.getfile(cls)).parent
        except (OSError, TypeError):
            continue
        for py_file in package_dir.rglob("*.py"):
            try:
                if _JSON_LD_MARKER in py_file.read_text(encoding="utf-8", errors="replace"):
                    keys.append(key)
                    break
            except OSError:
                continue
    return sorted(keys)


AUDIT_SQL = """
WITH json_ld_clubs AS (
    SELECT DISTINCT
        c.id           AS club_id,
        c.name         AS club_name,
        c.timezone     AS timezone,
        c.website      AS website,
        ss.scraper_key AS scraper_key,
        ss.source_url  AS source_url,
        ss.priority    AS priority
    FROM clubs c
    JOIN scraping_sources ss ON ss.club_id = c.id
    WHERE c.status = 'active'
      AND COALESCE(c.visible, TRUE) = TRUE
      AND ss.enabled = TRUE
      AND ss.scraper_key = ANY(%(keys)s)
),
future_show_counts AS (
    SELECT
        s.club_id,
        COUNT(*) AS total_future,
        COUNT(*) FILTER (WHERE NOT EXISTS (
            SELECT 1 FROM tickets t WHERE t.show_id = s.id
        )) AS missing_tickets
    FROM shows s
    WHERE s.date >= NOW()
    GROUP BY s.club_id
)
SELECT
    j.club_id,
    j.club_name,
    j.scraper_key,
    j.priority,
    j.source_url,
    COALESCE(f.total_future, 0)     AS total_future,
    COALESCE(f.missing_tickets, 0)  AS missing_tickets,
    CASE
        WHEN COALESCE(f.total_future, 0) = 0 THEN 0.0
        ELSE ROUND(100.0 * f.missing_tickets / f.total_future, 1)
    END                              AS missing_pct
FROM json_ld_clubs j
LEFT JOIN future_show_counts f ON f.club_id = j.club_id
ORDER BY j.scraper_key, j.priority, j.club_name;
"""


def main() -> int:
    json_ld_keys = discover_json_ld_scraper_keys()
    if not json_ld_keys:
        print(
            "No JSON-LD scrapers discovered via ScraperResolver. "
            "Verify the scrapers package is importable from this venv."
        )
        return 1

    print(f"Discovered {len(json_ld_keys)} JSON-LD scraper_keys: {', '.join(json_ld_keys)}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(AUDIT_SQL, {"keys": json_ld_keys})
            rows = cur.fetchall()

    if not rows:
        print("No clubs found with JSON-LD scraper_keys.")
        return 0

    by_key: dict[str, list[tuple]] = {}
    for r in rows:
        by_key.setdefault(r[2], []).append(r)

    affected: list[tuple] = []
    print()
    print("=" * 100)
    print("JSON-LD scraper audit — clubs grouped by scraper_key")
    print("=" * 100)

    for key in sorted(by_key.keys()):
        clubs = by_key[key]
        print(f"\n[{key}]  {len(clubs)} active+visible clubs")
        print(f"  {'club_id':>7}  {'future':>6}  {'missing':>7}  {'%miss':>6}  club_name")
        for club_id, name, _key, priority, source_url, total, missing, pct in clubs:
            flag = " *" if total > 0 and pct > 50.0 else "  "
            print(f"{flag}{club_id:>7}  {total:>6}  {missing:>7}  {float(pct):>5.1f}%  {name}")
            if total > 0 and pct > 50.0:
                affected.append((club_id, name, key, total, missing, float(pct), source_url))

    print()
    print("=" * 100)
    print(f"Likely AggregateOffer-affected (>50% of future shows missing tickets): "
          f"{len(affected)} club(s)")
    print("=" * 100)
    if affected:
        print(f"  {'club_id':>7}  {'scraper_key':<22}  {'future':>6}  {'missing':>7}  {'%miss':>6}  club_name")
        for club_id, name, key, total, missing, pct, _src in affected:
            print(f"  {club_id:>7}  {key:<22}  {total:>6}  {missing:>7}  {pct:>5.1f}%  {name}")
        print()
        print("Next step (criterion 6709): for each club above, fetch a live event page")
        print("via PlaywrightBrowser and inspect the JSON-LD offers @type. If @type=")
        print("AggregateOffer, the TASK-2028 fix should resolve it on the next nightly.")
        print("If the JSON-LD has no price-bearing fields (no price, lowPrice, highPrice),")
        print("the venue is upstream-data-limited and needs separate triage.")
    else:
        print("  (none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
