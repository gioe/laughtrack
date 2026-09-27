"""Read-only run evidence and conservative extraction-health classification.

num_shows counts extracted/transformed shows, never persisted rows. Per-club
persistence attribution is unavailable; scraper_runs holds the global counters.
Missing legacy fetch counters are unknown, not evidence of a healthy calendar.
Bot diagnostics are sticky across fallback attempts: productive output plus
clean fetch/error counters is recovered_productive, not blocked_empty.
Latest per-club evidence includes completed partitions even when the overall
pipeline failed. Global counters retain run_type labels: partition and merged
snapshots overlap and must never be added together.
"""

from collections.abc import Mapping
from typing import Any

RUN_HEALTH_QUERY = """
SELECT DISTINCT ON (c.club_id)
    c.id AS run_club_id, c.run_id, r.run_type, c.club_id, c.num_shows,
    c.success, c.errors_count AS errors, c.http_status,
    c.bot_block_detected, c.playwright_fallback_used, c.items_before_filter,
    r.exported_at AS latest_run,
    CASE WHEN jsonb_typeof(c.raw_stat->'targets_collected') = 'number'
         THEN c.raw_stat->'targets_collected' END AS targets_collected,
    CASE WHEN jsonb_typeof(c.raw_stat->'fetches_ok') = 'number'
         THEN c.raw_stat->'fetches_ok' END AS fetches_ok,
    CASE WHEN jsonb_typeof(c.raw_stat->'fetches_failed') = 'number'
         THEN c.raw_stat->'fetches_failed' END AS fetches_failed
FROM scraper_run_clubs c
JOIN scraper_runs r ON r.id = c.run_id
WHERE c.club_id IS NOT NULL AND r.run_type IN ('scraper', 'scraper_partition')
  AND r.exported_at >= NOW() - INTERVAL '30 days'
ORDER BY c.club_id, r.exported_at DESC, c.id DESC
"""

RUN_PERSISTENCE_QUERY = """
SELECT id AS run_id, run_type, exported_at, shows_scraped, shows_saved,
       shows_inserted, shows_updated, shows_failed_save, shows_skipped_dedup,
       shows_validation_failed, shows_db_errors, clubs_processed,
       clubs_successful, clubs_failed, errors_total
FROM scraper_runs
WHERE run_type IN ('scraper', 'scraper_partition')
  AND exported_at >= NOW() - INTERVAL '30 days'
ORDER BY exported_at DESC, id DESC
LIMIT 30
"""


def _count(value: Any) -> int | None:
    # Reject strings, booleans, fractional and negative values rather than
    # converting malformed raw JSON into false evidence of clean execution.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value < 0 or not float(value).is_integer():
        return None
    return int(value)


def classify_run_health(row: Mapping[str, Any]) -> str:
    """Classify observed extraction; missing stage coverage remains unknown.

    A positive result cannot establish completeness without fetch/error counters.
    Global validation/save counters may be supplied by an aggregate caller but
    must never be copied onto individual clubs as if they were attributable.
    """
    shows = _count(row.get("num_shows"))
    if shows is None:
        return "unknown"
    success = row.get("success")
    blocked = row.get("bot_block_detected") is True
    failures = [_count(row.get(key)) for key in ("fetches_failed", "errors", "validation_failed", "failed_save")]
    has_failure = success is False or any(value is not None and value > 0 for value in failures)
    if shows > 0:
        if has_failure:
            return "partial_productive"
        if success is not True or failures[0] is None or failures[1] is None:
            return "unknown"
        return "recovered_productive" if blocked else "healthy_productive"
    if blocked:
        return "blocked_empty"
    if has_failure or (_count(row.get("http_status")) or 0) >= 400:
        return "failed"
    if (
        success is True
        and failures[0] == 0
        and failures[1] == 0
        and (_count(row.get("fetches_ok")) or 0) > 0
        and _count(row.get("items_before_filter")) == 0
    ):
        return "healthy_empty"
    return "unknown"
