"""Apply explicit admin requests using the same live checks as CLI reviews."""
from contextlib import contextmanager
import json

from laughtrack.core.comedy_eligibility_review import current_identity_fingerprint
from laughtrack.core.comedy_eligibility_review_store import CURRENT_SQL, ReviewStore, _token
from laughtrack.core.comedy_eligibility_store import _row


def process_one(transaction, *, store_factory=ReviewStore):
    # Request, review operation and terminal status commit together. A crash rolls
    # everything back to pending; concurrent workers skip the locked request.
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT * FROM comedy_admin_review_requests
                WHERE status='pending' ORDER BY created_at,id LIMIT 1 FOR UPDATE SKIP LOCKED""")
            request = _row(cur)
            if request is None:
                return None
            cur.execute("SAVEPOINT admin_review")
            try:
                cur.execute("SELECT role FROM user_profiles WHERE id=%s", (request["actor"],))
                actor = _row(cur)
                if not actor or actor["role"] != "admin":
                    raise ValueError("Reviewer no longer has admin access")
                cur.execute(CURRENT_SQL, (request["candidate_id"],))
                row = _row(cur)
                if row is None:
                    raise ValueError("Candidate no longer exists")
                scope = _token(row)
                scope["observation_generation"] = str(scope["observation_generation"])
                if scope != request["snapshot"]:
                    raise ValueError("Event evidence or review changed; inspect and submit again")

                @contextmanager
                def same_transaction():
                    yield conn

                store = store_factory(same_transaction, snapshot_validator=current_identity_fingerprint)
                preview = store.preview([request["candidate_id"]], request["action"], request["reason"], request["actor"])
                # Recheck the scope that ReviewStore actually previewed, including
                # races between our first read and its snapshot validation.
                preview_scope = dict(preview["items"][0])
                preview_scope["observation_generation"] = str(preview_scope["observation_generation"])
                if preview_scope != request["snapshot"]:
                    raise ValueError("Event changed while preparing review")
                result = store.apply(preview["preview_id"], request["actor"],
                                     "admin:" + request["id"], preview["token_digest"])
            except ValueError as exc:
                cur.execute("ROLLBACK TO SAVEPOINT admin_review")
                cur.execute("""UPDATE comedy_admin_review_requests SET status='stale',error=%s,
                    completed_at=clock_timestamp() WHERE id=%s""", (str(exc), request["id"]))
                return {"id": request["id"], "status": "stale"}
            cur.execute("""UPDATE comedy_admin_review_requests SET status='applied',result=%s::jsonb,
                completed_at=clock_timestamp() WHERE id=%s""", (json.dumps(result), request["id"]))
            return {"id": request["id"], "status": "applied"}


def process_requests(transaction, limit=100):
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("Limit must be between 1 and 500")
    results = []
    for _ in range(limit):
        result = process_one(transaction)
        if result is None:
            break
        results.append(result)
    return results
