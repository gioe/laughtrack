"""End-to-end audit of scraping pipeline outputs.

Surfaces likely broken or degraded scrapers by querying the production DB for:
- per-platform / per-scraper output volume vs. enabled-source counts
- stale `last_scraped_date` (nightly scrape didn't touch a club)
- enabled scraping_sources whose club has zero upcoming shows ("dead sources")
- shows with no tickets (UI gates on tickets.length>0 — invisible inventory)
- shows with empty lineups (search/notification quality)
- per-scraper ticket-field coverage (NULL price, NULL purchase_url, all sold-out)
- anomalous show dates (midnight times, far-future, far-past)
- chain-level coverage

Usage
-----
    cd apps/scraper
    .venv/bin/python scripts/core/audit_scraping_data.py

Exit code is always 0; this is informational. The driving skill
(/analyze-scraping-data) classifies findings against thresholds.
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    sp = str(_path)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.adapters.db import get_connection


def _section(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def _query(label: str, sql: str, limit_rows: int | None = None) -> None:
    print(f"\n--- {label} ---")
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        cur.close()
    if not rows:
        print("(no rows)")
        return
    widths = [
        max(len(str(c)), max((len(str(r[i])) for r in rows), default=0))
        for i, c in enumerate(cols)
    ]
    print(" | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    print("-+-".join("-" * w for w in widths))
    show = rows if limit_rows is None else rows[:limit_rows]
    for r in show:
        print(" | ".join(str(v).ljust(widths[i]) for i, v in enumerate(r)))
    if limit_rows is not None and len(rows) > limit_rows:
        print(f"... ({len(rows) - limit_rows} more rows)")


def _run_health_cls(population_cte: str) -> str:
    """Wrap a `pop(club_id, name, platform, scraper_key)` CTE with run-health
    classification by joining ``scraper_run_clubs`` (TASK-3520).

    A bare "0 upcoming shows" or "stale last_scraped_date" signal cannot tell a
    genuinely broken scraper apart from a healthy-but-empty one, because
    ``shows.last_scraped_date`` only refreshes when a show is written — a venue
    whose nightly succeeds with 0 events never updates it (TASK-3512). And a club
    fed by an aggregate scraper (eventbrite organizer / ticketmaster_national)
    has 0 per-club ``scraper_run_clubs`` rows despite fresh coverage (TASK-3518).
    This classifies each club in ``pop`` by its actual run history:

    - ``never_run``                 — 0 ``scraper_run_clubs`` rows. The genuine
      coverage gap (visible+active+enabled source that never ran directly). NB:
      aggregate-covered venue clubs are excluded by the callers' ``0 upcoming
      shows`` is FALSE (they have shows), so they don't reach here.
    - ``broken_bot_block``          — most recent run was bot-blocked (DataDome
      etc.). Real breakage; coordinate with the proxy/reprobe path.
    - ``broken_error``              — most recent run failed (success=false).
    - ``dormant_recently_productive`` — recent runs succeeded and produced shows
      in the last 30d but there are 0 upcoming now. Usually a month-boundary /
      current-window source (e.g. json_ld calendars that expose only the current
      month) that self-heals, or shows that just expired (TASK-3513). NOT dead.
    - ``dormant_dark``              — recent runs succeeded but produced 0 shows
      in 30d: a real venue with no current programming on its source (TASK-3512's
      5 seatengine clubs). NOT a broken scraper.

    Only the ``never_run`` / ``broken_*`` buckets are usually actionable; the
    ``dormant_*`` buckets are healthy. See conventions #293 / #294.
    """
    return f"""
    WITH {population_cte}
    rs AS (
        SELECT
            pop.*,
            (SELECT COUNT(*) FROM scraper_run_clubs r WHERE r.club_id = pop.club_id) AS runs,
            (SELECT r.success FROM scraper_run_clubs r
                WHERE r.club_id = pop.club_id ORDER BY r.created_at DESC LIMIT 1) AS last_success,
            (SELECT r.bot_block_detected FROM scraper_run_clubs r
                WHERE r.club_id = pop.club_id ORDER BY r.created_at DESC LIMIT 1) AS last_block,
            (SELECT COALESCE(MAX(r.num_shows), 0) FROM scraper_run_clubs r
                WHERE r.club_id = pop.club_id AND r.created_at > NOW() - INTERVAL '30 days') AS max_shows_30d
        FROM pop
    ),
    cls AS (
        SELECT
            rs.*,
            CASE
                WHEN runs = 0              THEN 'never_run'
                WHEN last_block            THEN 'broken_bot_block'
                WHEN last_success IS FALSE THEN 'broken_error'
                WHEN max_shows_30d > 0     THEN 'dormant_recently_productive'
                ELSE                            'dormant_dark'
            END AS classification
        FROM rs
    )
    """


# ---------------------------------------------------------------------------
# 1. Inventory
# ---------------------------------------------------------------------------

_section("1. INVENTORY — clubs / sources / shows")

_query("Club status mix", """
    SELECT visible, status, COUNT(*) AS clubs
    FROM clubs GROUP BY 1, 2 ORDER BY 1, 2
""")

_query("Scraping sources by platform (enabled vs disabled)", """
    SELECT
        platform,
        COUNT(*) FILTER (WHERE enabled)     AS enabled,
        COUNT(*) FILTER (WHERE NOT enabled) AS disabled,
        COUNT(*)                            AS total
    FROM scraping_sources
    GROUP BY platform
    ORDER BY enabled DESC, platform
""")

_query("Upcoming-show inventory", """
    SELECT
        COUNT(*) FILTER (WHERE date >= NOW())                                       AS upcoming,
        COUNT(*) FILTER (WHERE date >= NOW() AND date < NOW() + INTERVAL '30 days') AS next_30d,
        COUNT(*) FILTER (WHERE date >= NOW() AND date < NOW() + INTERVAL '90 days') AS next_90d,
        COUNT(*) FILTER (WHERE date >= NOW() + INTERVAL '365 days')                 AS more_than_1yr_out,
        COUNT(*) FILTER (WHERE date < NOW())                                        AS past
    FROM shows
""")

# ---------------------------------------------------------------------------
# 2. Per-scraper productivity
# ---------------------------------------------------------------------------

_section("2. PER-SCRAPER PRODUCTIVITY (last 7 days of scrape activity)")

_query("Shows attributed by lastScrapedBy in last 7 days", """
    SELECT
        COALESCE(last_scraped_by, '<null>')    AS scraper,
        COUNT(*)                               AS shows_touched,
        COUNT(DISTINCT club_id)                AS distinct_clubs,
        COUNT(*) FILTER (WHERE date >= NOW())  AS upcoming_touched
    FROM shows
    WHERE last_scraped_date >= NOW() - INTERVAL '7 days'
    GROUP BY 1
    ORDER BY shows_touched DESC
""")

_query("Per-platform: enabled sources vs upcoming shows produced", """
    WITH src AS (
        SELECT platform, COUNT(*) AS enabled_sources
        FROM scraping_sources WHERE enabled GROUP BY platform
    ),
    sh AS (
        SELECT
            ss.platform,
            COUNT(DISTINCT s.id) AS upcoming_shows,
            COUNT(DISTINCT ss.club_id) FILTER (WHERE s.id IS NOT NULL) AS clubs_with_shows
        FROM scraping_sources ss
        LEFT JOIN shows s ON s.club_id = ss.club_id AND s.date >= NOW()
        WHERE ss.enabled
        GROUP BY ss.platform
    )
    SELECT
        src.platform,
        src.enabled_sources,
        sh.clubs_with_shows,
        sh.upcoming_shows,
        ROUND(sh.upcoming_shows::numeric / NULLIF(src.enabled_sources, 0), 1) AS shows_per_source
    FROM src JOIN sh USING (platform)
    ORDER BY src.enabled_sources DESC
""")

# ---------------------------------------------------------------------------
# 3. Dead sources (enabled but producing zero upcoming shows)
# ---------------------------------------------------------------------------

_section("3. ZERO-OUTPUT SCRAPERS (sources enabled, club has 0 upcoming shows)")

_query("Per-platform: enabled sources whose club has zero upcoming shows", """
    SELECT ss.platform, COUNT(*) AS dead_sources
    FROM scraping_sources ss
    JOIN clubs c ON c.id = ss.club_id
    WHERE ss.enabled AND c.visible AND c.status = 'active'
      AND NOT EXISTS (SELECT 1 FROM shows s WHERE s.club_id = ss.club_id AND s.date >= NOW())
    GROUP BY ss.platform
    ORDER BY dead_sources DESC
""")

_query("Sample dead-source clubs (first 25)", """
    SELECT ss.platform, ss.scraper_key, c.id AS club_id, c.name AS club
    FROM scraping_sources ss
    JOIN clubs c ON c.id = ss.club_id
    WHERE ss.enabled AND c.visible AND c.status = 'active'
      AND NOT EXISTS (SELECT 1 FROM shows s WHERE s.club_id = ss.club_id AND s.date >= NOW())
    ORDER BY ss.platform, c.id
    LIMIT 25
""")

# The raw "dead source" count above over-reports: it cannot tell a broken
# scraper from a healthy-but-empty venue. Classify by run health so the
# actionable buckets (never_run / broken_*) are separated from the healthy
# dormant ones (TASK-3520; conventions #293/#294).
_DEAD_POP = """
    pop AS (
        SELECT c.id AS club_id, c.name,
               MIN(ss.platform::text) AS platform, MIN(ss.scraper_key) AS scraper_key
        FROM scraping_sources ss
        JOIN clubs c ON c.id = ss.club_id
        WHERE ss.enabled AND c.visible AND c.status = 'active'
          AND NOT EXISTS (SELECT 1 FROM shows s WHERE s.club_id = ss.club_id AND s.date >= NOW())
        GROUP BY c.id, c.name
    ),
"""

_query(
    "Dead sources classified by run health (only never_run / broken_* are actionable)",
    _run_health_cls(_DEAD_POP)
    + "SELECT classification, COUNT(*) AS clubs FROM cls GROUP BY classification ORDER BY clubs DESC",
)

_query(
    "Actionable dead sources (never_run + broken_*) — sample",
    _run_health_cls(_DEAD_POP)
    + """
    SELECT classification, platform, scraper_key, club_id, name
    FROM cls
    WHERE classification = 'never_run' OR classification LIKE 'broken_%'
    ORDER BY classification, club_id
    LIMIT 40
    """,
)

# ---------------------------------------------------------------------------
# 4. Stale scrapes
# ---------------------------------------------------------------------------

_section("4. STALE SCRAPES (last_scraped_date older than nightly)")

_query("Per-platform: oldest scrape touch on any club's shows", """
    WITH last_touch AS (
        SELECT ss.platform, ss.club_id, MAX(s.last_scraped_date) AS latest
        FROM scraping_sources ss
        LEFT JOIN shows s ON s.club_id = ss.club_id
        WHERE ss.enabled
        GROUP BY 1, 2
    )
    SELECT
        platform,
        COUNT(*)                                                    AS clubs,
        COUNT(*) FILTER (WHERE latest IS NULL)                      AS never_scraped,
        COUNT(*) FILTER (WHERE latest < NOW() - INTERVAL '2 days')  AS stale_2d,
        COUNT(*) FILTER (WHERE latest < NOW() - INTERVAL '7 days')  AS stale_7d,
        COUNT(*) FILTER (WHERE latest < NOW() - INTERVAL '30 days') AS stale_30d
    FROM last_touch
    GROUP BY platform
    ORDER BY stale_7d DESC, platform
""")

# stale_30d above is NOT a "scraper is dead" signal on its own: shows.last_scraped_date
# only refreshes when a show is written, so a venue whose nightly succeeds with 0
# events stays "stale" forever (TASK-3512: 5 seatengine clubs flagged stale_30d all
# had 27 successful runs, 0 events, no bot-block). Classify the stale_30d population
# by run health — dormant_* are healthy, only never_run / broken_* are real breakage.
_STALE_POP = """
    pop AS (
        SELECT c.id AS club_id, c.name,
               MIN(ss.platform::text) AS platform, MIN(ss.scraper_key) AS scraper_key
        FROM scraping_sources ss
        JOIN clubs c ON c.id = ss.club_id
        WHERE ss.enabled
          AND (SELECT MAX(s.last_scraped_date) FROM shows s WHERE s.club_id = ss.club_id)
              < NOW() - INTERVAL '30 days'
        GROUP BY c.id, c.name
    ),
"""

_query(
    "stale_30d clubs classified by run health (dormant_* are healthy, not dead)",
    _run_health_cls(_STALE_POP)
    + "SELECT classification, COUNT(*) AS clubs FROM cls GROUP BY classification ORDER BY clubs DESC",
)

_query(
    "Stale clubs that are actually broken (never_run + broken_*) — sample",
    _run_health_cls(_STALE_POP)
    + """
    SELECT classification, platform, scraper_key, club_id, name
    FROM cls
    WHERE classification = 'never_run' OR classification LIKE 'broken_%'
    ORDER BY classification, club_id
    LIMIT 40
    """,
)

# ---------------------------------------------------------------------------
# 5. Show data quality
# ---------------------------------------------------------------------------

_section("5. SHOW DATA QUALITY (upcoming shows)")

_query("Upcoming shows missing key fields", """
    WITH base AS (SELECT * FROM shows WHERE date >= NOW())
    SELECT
        COUNT(*)                                                            AS total_upcoming,
        COUNT(*) FILTER (WHERE name IS NULL OR name = '')                   AS missing_name,
        COUNT(*) FILTER (WHERE show_page_url IS NULL OR show_page_url = '') AS missing_url,
        COUNT(*) FILTER (WHERE last_scraped_by IS NULL)                     AS no_attribution,
        COUNT(*) FILTER (WHERE last_scraped_date IS NULL)                   AS never_marked_scraped
    FROM base
""")

_query("Upcoming shows with NO tickets (UI gates on tickets.length>0)", """
    WITH no_tickets AS (
        SELECT s.id, s.last_scraped_by
        FROM shows s
        WHERE s.date >= NOW()
          AND NOT EXISTS (SELECT 1 FROM tickets t WHERE t.show_id = s.id)
    )
    SELECT last_scraped_by, COUNT(*) AS shows_without_tickets
    FROM no_tickets
    GROUP BY last_scraped_by
    ORDER BY shows_without_tickets DESC
""")

_query("Sample shows-without-tickets (first 25)", """
    SELECT s.id, c.name AS club, s.date::date AS show_date, s.last_scraped_by,
           LEFT(COALESCE(s.name,''), 50) AS show_name
    FROM shows s JOIN clubs c ON c.id = s.club_id
    WHERE s.date >= NOW()
      AND NOT EXISTS (SELECT 1 FROM tickets t WHERE t.show_id = s.id)
    ORDER BY s.date
    LIMIT 25
""")

_query("Upcoming shows with NO lineup items, by scraper", """
    SELECT s.last_scraped_by, COUNT(*) AS shows_without_lineup
    FROM shows s
    WHERE s.date >= NOW()
      AND NOT EXISTS (SELECT 1 FROM lineup_items li WHERE li.show_id = s.id)
    GROUP BY s.last_scraped_by
    ORDER BY shows_without_lineup DESC
    LIMIT 30
""")

# ---------------------------------------------------------------------------
# 6. Ticket data quality
# ---------------------------------------------------------------------------

_section("6. TICKET DATA QUALITY")

_query("Ticket field-coverage on upcoming shows (overall)", """
    WITH base AS (
        SELECT t.* FROM tickets t JOIN shows s ON s.id = t.show_id WHERE s.date >= NOW()
    )
    SELECT
        COUNT(*)                                                          AS total_tickets,
        COUNT(*) FILTER (WHERE price IS NULL)                             AS null_price,
        COUNT(*) FILTER (WHERE price = 0)                                 AS zero_price,
        COUNT(*) FILTER (WHERE purchase_url IS NULL OR purchase_url = '') AS no_purchase_url,
        COUNT(*) FILTER (WHERE sold_out)                                  AS sold_out,
        COUNT(*) FILTER (WHERE type IS NULL OR type = '')                 AS no_type
    FROM base
""")

_query("Per-scraper: NULL-price rate on upcoming-show tickets (sorted by worst)", """
    SELECT
        s.last_scraped_by,
        COUNT(t.id)                                                                                AS tickets,
        COUNT(t.id) FILTER (WHERE t.price IS NULL)                                                 AS null_price,
        COUNT(t.id) FILTER (WHERE t.purchase_url IS NULL)                                          AS null_url,
        ROUND(100.0 * COUNT(t.id) FILTER (WHERE t.price IS NULL) / NULLIF(COUNT(t.id), 0), 1)      AS pct_null_price
    FROM shows s LEFT JOIN tickets t ON t.show_id = s.id
    WHERE s.date >= NOW()
    GROUP BY s.last_scraped_by
    HAVING COUNT(t.id) > 0
    ORDER BY pct_null_price DESC NULLS LAST
    LIMIT 25
""")

_query("Suspicious shows where ALL tickets are sold out", """
    WITH show_ticket AS (
        SELECT s.id, s.last_scraped_by, s.date,
               COUNT(t.id) AS tickets,
               COUNT(t.id) FILTER (WHERE t.sold_out) AS sold_out
        FROM shows s LEFT JOIN tickets t ON t.show_id = s.id
        WHERE s.date >= NOW()
        GROUP BY s.id
    )
    SELECT last_scraped_by, COUNT(*) AS all_sold_out_shows
    FROM show_ticket
    WHERE tickets > 0 AND tickets = sold_out
    GROUP BY last_scraped_by
    ORDER BY all_sold_out_shows DESC
    LIMIT 25
""")

# ---------------------------------------------------------------------------
# 7. Anomalous dates
# ---------------------------------------------------------------------------

_section("7. ANOMALOUS DATES")

# ``shows.date`` is a UTC ``timestamptz``. A bare ``date::time`` reads the
# time-of-day in UTC, which mislabels every evening show west of UTC as
# "midnight" (7pm Central / 6pm Mountain / 5pm Pacific / 8pm-EDT all map to
# 00:00 UTC) — the false "time-parse miss" signature that flagged zanies,
# esthers_follies, and fareharbor (TASK-3516, all confirmed correct). Convert
# to the club's local wall-clock via ``AT TIME ZONE`` before the midnight test
# so only genuinely time-less shows (true local 00:00) are counted.
_query("Shows with implausible dates", """
    SELECT
        COUNT(*) FILTER (WHERE s.date < '2024-01-01')               AS very_old,
        COUNT(*) FILTER (WHERE s.date > NOW() + INTERVAL '2 years') AS very_far_future,
        COUNT(*) FILTER (
            WHERE (s.date AT TIME ZONE COALESCE(c.timezone, 'UTC'))::time = '00:00:00'
              AND s.date >= NOW()
        ) AS midnight_upcoming
    FROM shows s
    LEFT JOIN clubs c ON c.id = s.club_id
""")

_query("Per-scraper: midnight-time rate on upcoming shows (sorted by worst)", """
    SELECT
        s.last_scraped_by,
        COUNT(*)                                                                                       AS upcoming,
        COUNT(*) FILTER (WHERE (s.date AT TIME ZONE COALESCE(c.timezone, 'UTC'))::time = '00:00:00')    AS midnight,
        ROUND(100.0 * COUNT(*) FILTER (WHERE (s.date AT TIME ZONE COALESCE(c.timezone, 'UTC'))::time = '00:00:00')
              / NULLIF(COUNT(*), 0), 1)                                                                 AS pct_midnight
    FROM shows s
    LEFT JOIN clubs c ON c.id = s.club_id
    WHERE s.date >= NOW()
    GROUP BY s.last_scraped_by
    HAVING COUNT(*) >= 5
       AND COUNT(*) FILTER (WHERE (s.date AT TIME ZONE COALESCE(c.timezone, 'UTC'))::time = '00:00:00') > 0
    ORDER BY pct_midnight DESC
    LIMIT 20
""")

# ---------------------------------------------------------------------------
# 8. Chain coverage
# ---------------------------------------------------------------------------

_section("8. CHAIN COVERAGE")

_query("Chain-aware: are chained clubs producing shows?", """
    SELECT
        ch.name AS chain,
        COUNT(DISTINCT c.id)                                                AS clubs,
        COUNT(DISTINCT c.id) FILTER (WHERE c.visible AND c.status='active') AS active_visible,
        COUNT(DISTINCT s.id) FILTER (WHERE s.date >= NOW())                 AS upcoming_shows
    FROM chains ch
    LEFT JOIN clubs c ON c.chain_id = ch.id
    LEFT JOIN shows s ON s.club_id = c.id
    GROUP BY ch.name
    ORDER BY upcoming_shows DESC
""")

# ---------------------------------------------------------------------------
# 9. Lineup health
# ---------------------------------------------------------------------------

_section("9. LINEUP / COMEDIAN HEALTH")

_query("Lineup-per-show distribution on upcoming shows", """
    WITH counts AS (
        SELECT s.id, COUNT(li.comedian_id) AS lineup_size
        FROM shows s LEFT JOIN lineup_items li ON li.show_id = s.id
        WHERE s.date >= NOW() GROUP BY s.id
    )
    SELECT
        CASE
            WHEN lineup_size = 0 THEN '0'
            WHEN lineup_size = 1 THEN '1'
            WHEN lineup_size BETWEEN 2 AND 5 THEN '2-5'
            WHEN lineup_size BETWEEN 6 AND 10 THEN '6-10'
            ELSE '11+'
        END AS bucket,
        COUNT(*) AS shows
    FROM counts
    GROUP BY bucket
    ORDER BY 1
""")

_query("Per-scraper: empty-lineup RATE on upcoming shows (sorted by worst)", """
    WITH per AS (
        SELECT
            s.last_scraped_by,
            COUNT(*) AS upcoming,
            COUNT(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM lineup_items li WHERE li.show_id = s.id)) AS empty_lineup
        FROM shows s
        WHERE s.date >= NOW()
        GROUP BY s.last_scraped_by
    )
    SELECT
        last_scraped_by,
        upcoming,
        empty_lineup,
        ROUND(100.0 * empty_lineup / NULLIF(upcoming, 0), 1) AS pct_empty
    FROM per
    WHERE upcoming >= 10
    ORDER BY pct_empty DESC
    LIMIT 25
""")

print("\n[done]")
