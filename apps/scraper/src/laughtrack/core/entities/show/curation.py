"""Durable occurrence screening before eligibility and every supported upsert."""
import json
from laughtrack.core.comedy_eligibility_gate import candidate_payload, event_key, GateBatch
from laughtrack.core.comedy_eligibility_store import _row
from laughtrack.foundation.infrastructure.logger.logger import Logger


def screen_shows(transaction, shows):
    result = GateBatch()
    for show in shows:
        try:
            payload = candidate_payload(show)
            if show.id is not None:
                payload["id"] = show.id
            with transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT curation_lock_intake()")
                    source_id = show.eligibility_source_id
                    if source_id is None and show.last_scraped_by:
                        cur.execute("SELECT id FROM scraping_sources WHERE club_id=%s AND scraper_key=%s", (show.club_id, show.last_scraped_by))
                        rows = cur.fetchall()
                        if len(rows) == 1:
                            source_id = rows[0][0]
                    if source_id is not None:
                        payload.update(source_id=source_id, event_key=event_key(show))
                        if show.curation_series_id:
                            payload["series_id"] = show.curation_series_id
                    cur.execute("SELECT curation_observe_show(%s::jsonb)", (json.dumps(payload),))
                    cur.execute("SELECT * FROM curation_show_policy(%s::jsonb)", (json.dumps(payload),))
                    decision = _row(cur)
                    allowed = bool(decision and decision["allowed"])
        except Exception as exc:
            Logger.warn(f"Show curation unavailable; holding occurrence: {exc}")
            allowed = False
        if allowed:
            result.shows.append(show)
        else:
            result.withheld += 1
            result.reconciliation_safe = False
    return result
