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

Default output is a bounded anomaly summary; --json/--output retain safe evidence.
Use --legacy to additionally print historical inventory/ticket tables. Findings
exit 0 (review only); execution failures exit 1. No cleanup is performed.
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
    with get_connection(autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute("SET LOCAL statement_timeout = '120s'")
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        cur.close()
    if not rows:
        print("(no rows)")
        return
    widths = [max(len(str(c)), max((len(str(r[i])) for r in rows), default=0)) for i, c in enumerate(cols)]
    print(" | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    print("-+-".join("-" * w for w in widths))
    show = rows if limit_rows is None else rows[:limit_rows]
    for r in show:
        print(" | ".join(str(v).ljust(widths[i]) for i, v in enumerate(r)))
    if limit_rows is not None and len(rows) > limit_rows:
        print(f"... ({len(rows) - limit_rows} more rows)")


def _run_health_cls(population_cte: str) -> str:
    """Legacy tables use the same explicit evidence as the structured audit.

    Missing direct-run history or fetch counters is unknown, not an outage.
    Actual per-club persistence remains unavailable; these are extraction states.
    """
    return f"""
    WITH {population_cte}
    latest AS ({RUN_HEALTH_QUERY}),
    cls AS (
        SELECT pop.*,
          CASE
            WHEN latest.club_id IS NULL THEN 'unknown_no_direct_run'
            WHEN num_shows > 0 AND (success IS FALSE OR errors > 0 OR fetches_failed::text::numeric > 0)
              THEN 'partial_productive'
            WHEN num_shows = 0 AND bot_block_detected THEN 'broken_bot_block'
            WHEN num_shows = 0 AND (success IS FALSE OR errors > 0 OR http_status >= 400 OR fetches_failed::text::numeric > 0)
              THEN 'broken_error'
            WHEN success IS NOT TRUE OR fetches_failed IS NULL OR errors IS NULL THEN 'unknown_coverage'
            WHEN num_shows > 0 AND bot_block_detected THEN 'recovered_productive'
            WHEN num_shows > 0 THEN 'healthy_productive'
            WHEN fetches_ok::text::numeric > 0 AND items_before_filter = 0 THEN 'healthy_empty'
            ELSE 'unknown_coverage'
          END AS classification
        FROM pop LEFT JOIN latest ON latest.club_id = pop.club_id
    )
    """


def legacy_inventory_report():
    """Historical inventory tables; prefer the structured audit for triage."""
    # ---------------------------------------------------------------------------
    # 1. Inventory
    # ---------------------------------------------------------------------------

    _section("1. INVENTORY — clubs / sources / shows")

    _query(
        "Club status mix",
        """
        SELECT visible, status, COUNT(*) AS clubs
        FROM clubs GROUP BY 1, 2 ORDER BY 1, 2
    """,
    )

    _query(
        "Scraping sources by platform (enabled vs disabled)",
        """
        SELECT
            platform,
            COUNT(*) FILTER (WHERE enabled)     AS enabled,
            COUNT(*) FILTER (WHERE NOT enabled) AS disabled,
            COUNT(*)                            AS total
        FROM scraping_sources
        GROUP BY platform
        ORDER BY enabled DESC, platform
    """,
    )

    _query(
        "Upcoming-show inventory",
        """
        SELECT
            COUNT(*) FILTER (WHERE date >= NOW())                                       AS upcoming,
            COUNT(*) FILTER (WHERE date >= NOW() AND date < NOW() + INTERVAL '30 days') AS next_30d,
            COUNT(*) FILTER (WHERE date >= NOW() AND date < NOW() + INTERVAL '90 days') AS next_90d,
            COUNT(*) FILTER (WHERE date >= NOW() + INTERVAL '365 days')                 AS more_than_1yr_out,
            COUNT(*) FILTER (WHERE date < NOW())                                        AS past
        FROM shows
    """,
    )

    # ---------------------------------------------------------------------------
    # 2. Per-scraper productivity
    # ---------------------------------------------------------------------------

    _section("2. PER-SCRAPER PRODUCTIVITY (last 7 days of scrape activity)")

    _query(
        "Shows attributed by lastScrapedBy in last 7 days",
        """
        SELECT
            COALESCE(last_scraped_by, '<null>')    AS scraper,
            COUNT(*)                               AS shows_touched,
            COUNT(DISTINCT club_id)                AS distinct_clubs,
            COUNT(*) FILTER (WHERE date >= NOW())  AS upcoming_touched
        FROM shows
        WHERE last_scraped_date >= NOW() - INTERVAL '7 days'
        GROUP BY 1
        ORDER BY shows_touched DESC
    """,
    )

    _query(
        "Per-platform: enabled sources vs upcoming shows produced",
        """
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
    """,
    )

    # ---------------------------------------------------------------------------
    # 3. Dead sources (enabled but producing zero upcoming shows)
    # ---------------------------------------------------------------------------

    _section("3. ZERO-OUTPUT SCRAPERS (sources enabled, club has 0 upcoming shows)")

    _query(
        "Per-platform: enabled sources whose club has zero upcoming shows",
        """
        SELECT ss.platform, COUNT(*) AS dead_sources
        FROM scraping_sources ss
        JOIN clubs c ON c.id = ss.club_id
        WHERE ss.enabled AND c.visible AND c.status = 'active'
          AND NOT EXISTS (SELECT 1 FROM shows s WHERE s.club_id = ss.club_id AND s.date >= NOW())
        GROUP BY ss.platform
        ORDER BY dead_sources DESC
    """,
    )

    _query(
        "Sample dead-source clubs (first 25)",
        """
        SELECT ss.platform, ss.scraper_key, c.id AS club_id, c.name AS club
        FROM scraping_sources ss
        JOIN clubs c ON c.id = ss.club_id
        WHERE ss.enabled AND c.visible AND c.status = 'active'
          AND NOT EXISTS (SELECT 1 FROM shows s WHERE s.club_id = ss.club_id AND s.date >= NOW())
        ORDER BY ss.platform, c.id
        LIMIT 25
    """,
    )

    # The raw "dead source" count above over-reports: it cannot tell a broken
    # scraper from a healthy-but-empty venue. Classify by run health so the
    # actionable buckets (partial_productive / broken_*) are separated from the healthy
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
        "Dead sources classified by run health (only partial_productive / broken_* are actionable)",
        _run_health_cls(_DEAD_POP)
        + "SELECT classification, COUNT(*) AS clubs FROM cls GROUP BY classification ORDER BY clubs DESC",
    )

    _query(
        "Actionable dead sources (partial_productive + broken_*) — sample",
        _run_health_cls(_DEAD_POP) + """
        SELECT classification, platform, scraper_key, club_id, name
        FROM cls
        WHERE classification = 'partial_productive' OR classification LIKE 'broken_%'
        ORDER BY classification, club_id
        LIMIT 40
        """,
    )

    # ---------------------------------------------------------------------------
    # 4. Stale scrapes
    # ---------------------------------------------------------------------------

    _section("4. STALE SCRAPES (last_scraped_date older than nightly)")

    _query(
        "Per-platform: oldest scrape touch on any club's shows",
        """
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
    """,
    )

    # stale_30d above is NOT a "scraper is dead" signal on its own: shows.last_scraped_date
    # only refreshes when a show is written, so a venue whose nightly succeeds with 0
    # events stays "stale" forever (TASK-3512: 5 seatengine clubs flagged stale_30d all
    # had 27 successful runs, 0 events, no bot-block). Classify the stale_30d population
    # by run health — dormant_* are healthy, only partial_productive / broken_* are real breakage.
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
        "Stale clubs that are actually broken (partial_productive + broken_*) — sample",
        _run_health_cls(_STALE_POP) + """
        SELECT classification, platform, scraper_key, club_id, name
        FROM cls
        WHERE classification = 'partial_productive' OR classification LIKE 'broken_%'
        ORDER BY classification, club_id
        LIMIT 40
        """,
    )

    # ---------------------------------------------------------------------------
    # 5. Show data quality
    # ---------------------------------------------------------------------------

    _section("5. SHOW DATA QUALITY (upcoming shows)")

    _query(
        "Upcoming shows missing key fields",
        """
        WITH base AS (SELECT * FROM shows WHERE date >= NOW())
        SELECT
            COUNT(*)                                                            AS total_upcoming,
            COUNT(*) FILTER (WHERE name IS NULL OR name = '')                   AS missing_name,
            COUNT(*) FILTER (WHERE show_page_url IS NULL OR show_page_url = '') AS missing_url,
            COUNT(*) FILTER (WHERE last_scraped_by IS NULL)                     AS no_attribution,
            COUNT(*) FILTER (WHERE last_scraped_date IS NULL)                   AS never_marked_scraped
        FROM base
    """,
    )

    _query(
        "Upcoming shows with NO tickets (UI gates on tickets.length>0)",
        """
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
    """,
    )

    _query(
        "Sample shows-without-tickets (first 25)",
        """
        SELECT s.id, c.name AS club, s.date::date AS show_date, s.last_scraped_by,
               LEFT(COALESCE(s.name,''), 50) AS show_name
        FROM shows s JOIN clubs c ON c.id = s.club_id
        WHERE s.date >= NOW()
          AND NOT EXISTS (SELECT 1 FROM tickets t WHERE t.show_id = s.id)
        ORDER BY s.date
        LIMIT 25
    """,
    )

    _query(
        "Upcoming shows with NO lineup items, by scraper",
        """
        SELECT s.last_scraped_by, COUNT(*) AS shows_without_lineup
        FROM shows s
        WHERE s.date >= NOW()
          AND NOT EXISTS (SELECT 1 FROM lineup_items li WHERE li.show_id = s.id)
        GROUP BY s.last_scraped_by
        ORDER BY shows_without_lineup DESC
        LIMIT 30
    """,
    )

    # ---------------------------------------------------------------------------
    # 6. Ticket data quality
    # ---------------------------------------------------------------------------

    _section("6. TICKET DATA QUALITY")

    _query(
        "Ticket field-coverage on upcoming shows (overall)",
        """
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
    """,
    )

    _query(
        "Per-scraper: NULL-price rate on upcoming-show tickets (sorted by worst)",
        """
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
    """,
    )

    _query(
        "Suspicious shows where ALL tickets are sold out",
        """
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
    """,
    )

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
    _query(
        "Shows with implausible dates",
        """
        SELECT
            COUNT(*) FILTER (WHERE s.date < '2024-01-01')               AS very_old,
            COUNT(*) FILTER (WHERE s.date > NOW() + INTERVAL '2 years') AS very_far_future,
            COUNT(*) FILTER (
                WHERE (s.date AT TIME ZONE c.timezone)::time = '00:00:00'
                  AND s.date >= NOW()
            ) AS midnight_upcoming,
            COUNT(*) FILTER (WHERE c.timezone IS NULL AND s.date >= NOW()) AS unknown_local_time
        FROM shows s
        LEFT JOIN clubs c ON c.id = s.club_id
    """,
    )

    _query(
        "Per-scraper: midnight-time rate on upcoming shows (sorted by worst)",
        """
        SELECT
            s.last_scraped_by,
            COUNT(*)                                                                                       AS upcoming,
            COUNT(*) FILTER (WHERE (s.date AT TIME ZONE c.timezone)::time = '00:00:00')    AS midnight,
            ROUND(100.0 * COUNT(*) FILTER (WHERE (s.date AT TIME ZONE c.timezone)::time = '00:00:00')
                  / NULLIF(COUNT(*), 0), 1)                                                                 AS pct_midnight
        FROM shows s
        LEFT JOIN clubs c ON c.id = s.club_id
        WHERE s.date >= NOW()
        GROUP BY s.last_scraped_by
        HAVING COUNT(*) >= 5
           AND COUNT(*) FILTER (WHERE (s.date AT TIME ZONE c.timezone)::time = '00:00:00') > 0
        ORDER BY pct_midnight DESC
        LIMIT 20
    """,
    )

    # ---------------------------------------------------------------------------
    # 8. Chain coverage
    # ---------------------------------------------------------------------------

    _section("8. CHAIN COVERAGE")

    _query(
        "Chain-aware: are chained clubs producing shows?",
        """
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
    """,
    )

    # ---------------------------------------------------------------------------
    # 9. Lineup health
    # ---------------------------------------------------------------------------

    _section("9. LINEUP / COMEDIAN HEALTH")

    _query(
        "Lineup-per-show distribution on upcoming shows",
        """
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
    """,
    )

    _query(
        "Per-scraper: empty-lineup RATE on upcoming shows (sorted by worst)",
        """
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
    """,
    )

    print("\n[done]")


# Structured recurring audit. Input queries deliberately project individual
# fields; raw payloads, source configuration, URLs and error strings are never
# copied into retained reports.
import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from laughtrack.core.entities.comedian.false_positive_detector import detect_false_positive
from laughtrack.core.rss_episode_reader import parse_duration_seconds
from scripts.core.check_scraping_source_invariants import is_aggregate_covered
from scripts.core.scraping_run_health import (
    RUN_HEALTH_QUERY,
    RUN_PERSISTENCE_QUERY,
    classify_run_health,
)

SHOW_QUERY = """
SELECT s.id, s.club_id, s.name, s.date, s.room, s.show_page_url,
       s.last_scraped_date, s.last_scraped_by, s.scraped_by_organizer_id,
       c.zip_code, c.country, c.club_type, c.timezone,
       EXISTS (SELECT 1 FROM scraping_sources ss WHERE ss.club_id=c.id AND ss.enabled) AS has_enabled_source
FROM shows s JOIN clubs c ON c.id=s.club_id
WHERE c.visible AND s.date >= %(as_of)s AND s.date < %(until)s
ORDER BY s.id
"""
LINEUP_QUERY = """
SELECT c.id AS comedian_id, c.name, l.show_id
FROM comedians c JOIN lineup_items l ON l.comedian_id=c.uuid
JOIN shows s ON s.id=l.show_id JOIN clubs cl ON cl.id=s.club_id
WHERE c.visible AND cl.visible AND s.date >= %(as_of)s AND s.date < %(until)s
ORDER BY c.id,l.show_id
"""
IDENTITY_QUERY = """
SELECT c.id, c.parent_comedian_id, p.visible AS parent_visible,
       c.instagram_account, c.tiktok_account, c.youtube_account,
       array(SELECT l.show_id FROM lineup_items l JOIN shows s ON s.id=l.show_id
             JOIN clubs cl ON cl.id=s.club_id WHERE l.comedian_id=c.uuid
             AND cl.visible AND s.date >= %(as_of)s AND s.date < %(until)s ORDER BY l.show_id) AS show_ids
FROM comedians c LEFT JOIN comedians p ON p.id=c.parent_comedian_id
WHERE c.visible ORDER BY c.id
"""
EPISODE_QUERY = """
SELECT podcast_id, source,
       CASE WHEN source_payload ? 'itunes_duration' THEN 'rss_duration_evidence'
            WHEN source_payload ? 'duration' THEN 'duration_field_evidence'
            ELSE 'unknown' END AS provenance,
       CASE WHEN duration_seconds <= 0 THEN 'nonpositive'
            WHEN duration_seconds > 86400 THEN 'over_day'
            ELSE 'valid_long_form' END AS duration_band,
       count(*) AS episode_count, min(id) AS sample_episode_id,
       min(duration_seconds) AS minimum_seconds, max(duration_seconds) AS maximum_seconds
FROM podcast_episodes
WHERE duration_seconds <= 0 OR duration_seconds > 21600
GROUP BY podcast_id, source, provenance, duration_band
ORDER BY podcast_id, source, provenance, duration_band
"""


def event_identity(url: str | None) -> str | None:
    """Conservative event key; calendar/home pages are not performance IDs."""
    if not url:
        return None
    try:
        parsed = urlsplit(url.strip())
        host = (parsed.hostname or "").lower().removeprefix("www.")
        if parsed.scheme not in ("https", "http") or not host:
            return None
        path = parsed.path.rstrip("/")
        if host.endswith("eventbrite.com") or host.endswith("eventbrite.ca"):
            match = re.search(r"-(\d+)$", path)
            if match:
                return "eventbrite:" + match.group(1)
        params = parse_qs(parsed.query)
        # Preserve event identifiers, discard tracking and authentication values.
        for key in ("eventId", "event_id", "eventid", "id"):
            if key in params and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", params[key][0]):
                return host + path + "?" + key + "=" + params[key][0]
        if re.search(r"/(?:e|event|events|show|shows|performance|performances)/[^/]+", path, re.I):
            return host + path
    except ValueError:
        pass
    return None


def _date(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def analyze_snapshot(data, *, as_of, until, sample_limit=10):
    """Pure analysis with allowlisted output, complete counts and bounded IDs.

    Counts mean potential exposure at visible venues, not proof of every web
    query's eligibility. Review candidates never initiate cleanup.
    """
    metrics = {}

    def add(key, entities, show_ids=(), *, warning=True, note=""):
        entities, show_ids = sorted(set(entities)), sorted(set(show_ids))
        count = len(entities)
        metrics[key] = {
            "count": count,
            "affected_show_count": len(show_ids),
            "warning_threshold": 1 if warning else None,
            "status": "review" if warning and count else ("info" if count else "clear"),
            "sample_ids": entities[:sample_limit],
            "sample_show_ids": show_ids[:sample_limit],
            "note": note,
        }

    shows = [s for s in data.get("shows", []) if as_of <= _date(s["date"]) < until]
    by_id = {s["id"]: s for s in shows}
    bad_ids, bad_shows = set(), set()
    for row in data.get("lineups", []):
        if row["show_id"] in by_id and detect_false_positive(row["name"]):
            bad_ids.add(row["comedian_id"])
            bad_shows.add(row["show_id"])
    add(
        "suspicious_lineup_identities",
        bad_ids,
        bad_shows,
        note="Shared ingestion detector candidates; visible lineup/venue exposure, not verified false identities.",
    )

    cross, rooms = defaultdict(list), defaultdict(list)
    for s in shows:
        key = event_identity(s.get("show_page_url"))
        if key:
            cross[(key, _date(s["date"]))].append(s)
            rooms[(s["club_id"], key, _date(s["date"]))].append(s)
    cross_groups = [v for v in cross.values() if len({s["club_id"] for s in v}) > 1]
    room_groups = [v for v in rooms.values() if len({(s.get("room") or "").strip() for s in v}) > 1]
    stale_groups = [
        v
        for v in room_groups
        if any(not s.get("last_scraped_date") or _date(s["last_scraped_date"]) < as_of - timedelta(days=7) for s in v)
        and any(s.get("last_scraped_date") and _date(s["last_scraped_date"]) >= as_of - timedelta(days=7) for s in v)
    ]
    for key, groups in [
        ("cross_venue_event_candidates", cross_groups),
        ("room_duplicate_candidates", room_groups),
        ("stale_room_duplicate_candidates", stale_groups),
    ]:
        add(
            key,
            [min(s["id"] for s in group) for group in groups],
            [s["id"] for group in groups for s in group],
            note="Same explicit event identity and instant; requires source review, never automatic deletion.",
        )

    missing = [s for s in shows if not (s.get("zip_code") or "").strip()]
    for suffix, country in [("us", "US"), ("unknown_country", None), ("other_country", "other")]:

        def matches(s):
            value = (s.get("country") or "").strip().upper()
            return (
                (value in ("US", "USA", "UNITED STATES"))
                if country == "US"
                else (not value if country is None else bool(value) and value not in ("US", "USA", "UNITED STATES"))
            )

        cohort = [s for s in missing if matches(s)]
        add(
            "missing_zip_" + suffix,
            [s["club_id"] for s in cohort],
            [s["id"] for s in cohort],
            note="Upcoming inventory missing postal coverage; producer/multi-location venues require manual review.",
        )
    no_direct = [s for s in shows if not s.get("has_enabled_source")]
    covered_clubs = {s["club_id"] for s in no_direct if is_aggregate_covered(s, as_of)}
    covered = [s for s in no_direct if s["club_id"] in covered_clubs]
    unverified = [s for s in no_direct if s["club_id"] not in covered_clubs]
    add(
        "aggregate_covered_without_direct_source",
        [s["club_id"] for s in covered],
        [s["id"] for s in covered],
        warning=False,
        note="Recent aggregate or organizer-attributed writes establish indirect coverage.",
    )
    add(
        "unverified_source_coverage",
        [s["club_id"] for s in unverified],
        [s["id"] for s in unverified],
        warning=False,
        note="No direct source or verified recent aggregate provenance; not proof of absent ingestion. See source invariant report.",
    )
    unknown, midnight = [], []
    for s in shows:
        try:
            if not s.get("timezone"):
                raise ZoneInfoNotFoundError("unknown")
            local = _date(s["date"]).astimezone(ZoneInfo(s["timezone"]))
            if (local.hour, local.minute, local.second) == (0, 0, 0):
                midnight.append(s)
        except (ZoneInfoNotFoundError, ValueError):
            unknown.append(s)
    add(
        "unknown_local_time",
        [s["id"] for s in unknown],
        [s["id"] for s in unknown],
        note="Missing/invalid timezone; UTC midnight is not evidence of local midnight.",
    )
    add(
        "local_midnight_candidates",
        [s["id"] for s in midnight],
        [s["id"] for s in midnight],
        note="Known local midnight, which may be a legitimate late show; review only.",
    )

    handles = defaultdict(list)
    hidden = []
    for row in data.get("identities", []):
        if row.get("parent_comedian_id") is not None:
            if row.get("parent_visible") is False:
                hidden.append(row)
            continue
        for platform in ("instagram", "tiktok", "youtube"):
            handle = (row.get(platform + "_account") or "").strip().lower().lstrip("@")
            if handle:
                handles[(platform, handle)].append(row)
    conflicts = [v for v in handles.values() if len(v) > 1]
    add(
        "unlinked_social_handle_identities",
        [r["id"] for v in conflicts for r in v],
        [sid for v in conflicts for r in v for sid in r.get("show_ids", []) if sid in by_id],
        note="Distinct visible roots sharing a normalized handle; equality does not establish identity.",
    )
    add(
        "visible_alias_hidden_parent",
        [r["id"] for r in hidden],
        [sid for r in hidden for sid in r.get("show_ids", []) if sid in by_id],
        note="Review existing moderation lineage; do not automatically change parent eligibility.",
    )

    # Grouped SQL avoids loading every episode; validate the stored numeric
    # boundaries against the shared parser, never infer units from magnitude.
    durations = []
    for row in data.get("durations", []):
        valid = (
            parse_duration_seconds(row["minimum_seconds"]) is not None
            and parse_duration_seconds(row["maximum_seconds"]) is not None
        )
        durations.append(
            {
                "podcast_id": int(row["podcast_id"]),
                "source": (
                    row["source"]
                    if row["source"] in ("rss", "podcast_index", "apple", "spotify", "youtube")
                    else "other"
                ),
                "provenance": (
                    row["provenance"]
                    if row["provenance"] in ("rss_duration_evidence", "duration_field_evidence")
                    else "unknown"
                ),
                "duration_band": (
                    "valid_long_form" if valid else ("nonpositive" if row["maximum_seconds"] <= 0 else "over_day")
                ),
                "episode_count": int(row["episode_count"]),
                "sample_episode_id": int(row["sample_episode_id"]),
                "minimum_seconds": int(row["minimum_seconds"]),
                "maximum_seconds": int(row["maximum_seconds"]),
            }
        )
    for band in ("over_day", "nonpositive", "valid_long_form"):
        cohort = [r for r in durations if r["duration_band"] == band]
        metrics["podcast_duration_" + band] = {
            "count": sum(r["episode_count"] for r in cohort),
            "affected_podcast_count": len({r["podcast_id"] for r in cohort}),
            "warning_threshold": None if band == "valid_long_form" else 1,
            "status": ("info" if band == "valid_long_form" else "review") if cohort else "clear",
            "groups": cohort,
            "note": "Policy: positive whole seconds through 24h. Historical nonpositive values are a baseline, not proof of a new regression. Source label is not latest ingestion provenance.",
        }

    health = defaultdict(list)
    for row in data.get("runs", []):
        health[classify_run_health(row)].append(row)
    for category in (
        "healthy_productive",
        "healthy_empty",
        "recovered_productive",
        "partial_productive",
        "blocked_empty",
        "failed",
        "unknown",
    ):
        cohort = health[category]
        clubs = {r["club_id"] for r in cohort}
        add(
            "run_health_" + category,
            clubs,
            [s["id"] for s in shows if s["club_id"] in clubs],
            warning=category in ("partial_productive", "blocked_empty", "failed"),
            note="Latest direct run within 30d. num_shows is extraction; per-club persistence is unknown. Missing fetch counters retain unknown coverage.",
        )
    persistence = []
    for row in data.get("persistence", []):
        persistence.append(
            {
                k: row.get(k)
                for k in (
                    "run_id",
                    "run_type",
                    "shows_saved",
                    "shows_inserted",
                    "shows_updated",
                    "shows_failed_save",
                    "shows_validation_failed",
                    "shows_db_errors",
                )
            }
        )
    failed_runs = [
        r
        for r in persistence
        if any((r.get(k) or 0) > 0 for k in ("shows_failed_save", "shows_validation_failed", "shows_db_errors"))
    ]
    add(
        "run_persistence_failures",
        [r["run_id"] for r in failed_runs],
        note="Global per-run failure counters; do not sum overlapping partition and merged snapshots or attribute them to individual clubs.",
    )
    return {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "until": until.isoformat(),
        "read_only": True,
        "upcoming_show_count": len(shows),
        "sample_limit": sample_limit,
        "metrics": metrics,
        "run_persistence": persistence,
        "limitations": [
            "Counts are potential exposure at visible venues, not exact eligibility across every discovery surface.",
            "Candidate event identity keys do not prove a duplicate; shared calendars without event identifiers are excluded.",
            "Episodes are audited across all dates; show exposure uses the declared window. No automatic data repair.",
        ],
    }


def collect_snapshot(as_of, until):
    params = {"as_of": as_of, "until": until}
    queries = {
        "shows": SHOW_QUERY,
        "lineups": LINEUP_QUERY,
        "identities": IDENTITY_QUERY,
        "durations": EPISODE_QUERY,
        "runs": RUN_HEALTH_QUERY,
        "persistence": RUN_PERSISTENCE_QUERY,
    }
    data = {}
    with get_connection(autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cur.execute("SET LOCAL statement_timeout = '120s'")
            for key, sql in queries.items():
                cur.execute(sql, params)
                columns = [d[0] for d in cur.description]
                data[key] = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.rollback()
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only production anomaly audit with bounded, credential-free evidence."
    )
    parser.add_argument(
        "--legacy", action="store_true", help="Also print historical inventory/ticket diagnostics (human output only)."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit the structured report instead of the human-readable summary."
    )
    parser.add_argument("--output", type=Path, help="Retain the structured JSON report at this path.")
    parser.add_argument(
        "--days", type=int, default=365, help="Future show window (1–730 days; default 365). Episodes use all dates."
    )
    parser.add_argument(
        "--sample-limit", type=int, default=10, help="Maximum IDs retained per metric (0–100). Counts remain complete."
    )
    args = parser.parse_args(argv)
    if not 1 <= args.days <= 730 or not 0 <= args.sample_limit <= 100:
        parser.error("days must be 1–730 and sample-limit must be 0–100")
    as_of = datetime.now(timezone.utc)
    try:
        report = analyze_snapshot(
            collect_snapshot(as_of, as_of + timedelta(days=args.days)),
            as_of=as_of,
            until=as_of + timedelta(days=args.days),
            sample_limit=args.sample_limit,
        )
        encoded = json.dumps(report, indent=2, default=str) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            pending = args.output.with_suffix(args.output.suffix + ".tmp")
            pending.write_text(encoded)
            pending.replace(args.output)
        if args.legacy and not args.json:
            legacy_inventory_report()
        if args.json:
            print(encoded, end="")
        else:
            for key, metric in report["metrics"].items():
                print(
                    f"{metric['status']:6} {key}: {metric['count']} (upcoming shows: {metric.get('affected_show_count', 'n/a')})"
                )
        return 0  # Findings are review signals, not execution failures.
    except Exception as exc:
        # Driver exception text may include credentials, query values or URLs.
        print(f"Audit execution failed ({type(exc).__name__}); no report published.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
