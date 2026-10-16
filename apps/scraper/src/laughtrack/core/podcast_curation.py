"""Shared exact podcast identity lookup. Errors deliberately propagate (hold intake)."""
import json


def resolve_candidate(cur, candidate):
    payload = {"source": candidate.source, "source_podcast_id": candidate.source_podcast_id,
               "feed_url": candidate.feed_url, "title": candidate.title}
    value = json.dumps(payload)
    cur.execute("SELECT curation_lock_intake()")
    cur.execute("SELECT * FROM curation_podcast_policy(%s::jsonb)", (value,))
    row = cur.fetchone()
    if not row or row[0] in ("blocked", "ambiguous"):
        raise ValueError("Podcast intake held: blocked, ambiguous or unavailable policy")
    cur.execute("SELECT curation_observe_podcast(%s::jsonb)", (value,))
    return row[2]
