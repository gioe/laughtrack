"""PostgreSQL model cache and conservative USD-micro reservation ledger.

Transactions are short; callers perform provider I/O only after reserve returns.
The database mutex serializes reservations across hosts and event loops.
"""
import json
from uuid import uuid4

LOCK_SQL = "SELECT id FROM comedy_model_budget_mutex WHERE id=1 FOR UPDATE"
LOOKUP_SQL = "SELECT result FROM comedy_model_cache WHERE cache_key=%s"
RESERVE_SQL = """
INSERT INTO comedy_model_attempts(token,cache_key,reserved_micros,charged_micros,lease_until)
SELECT %s,%s,%s,%s,clock_timestamp()+(%s * interval '1 second')
WHERE NOT EXISTS(SELECT 1 FROM comedy_model_cache WHERE cache_key=%s)
 AND NOT EXISTS(SELECT 1 FROM comedy_model_attempts WHERE cache_key=%s AND state='pending' AND lease_until>clock_timestamp())
 AND (SELECT count(*) FROM comedy_model_attempts WHERE state='pending' AND lease_until>clock_timestamp()) < %s
 AND (SELECT count(*) FROM comedy_model_attempts WHERE budget_day=(clock_timestamp() AT TIME ZONE 'UTC')::date) < %s
 AND COALESCE((SELECT sum(charged_micros) FROM comedy_model_attempts WHERE budget_day=(clock_timestamp() AT TIME ZONE 'UTC')::date),0)+%s <= %s
RETURNING token
"""
COMPLETE_SQL = """
UPDATE comedy_model_attempts SET state='complete',actual_micros=%s,charged_micros=%s,finished_at=clock_timestamp()
WHERE token=%s AND state='pending' AND lease_until>clock_timestamp() AND reserved_micros>=%s
RETURNING cache_key
"""
OVERAGE_SQL = """
UPDATE comedy_model_attempts SET state='failed',actual_micros=%s,
 charged_micros=GREATEST(charged_micros,%s),finished_at=clock_timestamp()
WHERE token=%s AND state='pending'
"""
CACHE_SQL = """
INSERT INTO comedy_model_cache(cache_key,owner_token,result) VALUES(%s,%s,%s::jsonb)
ON CONFLICT(cache_key) DO NOTHING
"""
FAIL_SQL = """
UPDATE comedy_model_attempts SET state='failed',finished_at=clock_timestamp()
WHERE token=%s AND state='pending'
"""


class ModelDecisionStore:
    def __init__(self, transaction):
        self.transaction = transaction

    def lookup(self, key):
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(LOOKUP_SQL, (key,))
                row = cur.fetchone()
                return row[0] if row else None

    def reserve(self, key, *, max_cost_micros, daily_budget_micros, daily_request_limit,
                concurrency_limit, lease_seconds):
        values = (max_cost_micros, daily_budget_micros, daily_request_limit, concurrency_limit, lease_seconds)
        if any(type(v) is not int or v <= 0 for v in values) or not isinstance(key, str) or not key:
            raise ValueError("Model reservations require a key and positive integer bounds")
        token = str(uuid4())
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(LOCK_SQL)
                if cur.fetchone() is None:
                    raise RuntimeError("Model budget mutex missing")
                cur.execute(RESERVE_SQL, (token, key, max_cost_micros, max_cost_micros, lease_seconds,
                                         key, key, concurrency_limit, daily_request_limit,
                                         max_cost_micros, daily_budget_micros))
                return token if cur.fetchone() else None

    def complete(self, token, result, actual_cost_micros):
        if type(actual_cost_micros) is not int or actual_cost_micros < 0 or not isinstance(result, dict):
            raise ValueError("Model completion requires an object and nonnegative integer cost")
        encoded = json.dumps(result, sort_keys=True, allow_nan=False)
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(LOCK_SQL)
                if cur.fetchone() is None:
                    raise RuntimeError("Model budget mutex missing")
                cur.execute(COMPLETE_SQL, (actual_cost_micros, actual_cost_micros, token, actual_cost_micros))
                row = cur.fetchone()
                if row is None:
                    # Expired or under-reserved requests never populate cache.
                    # Retain the reservation, recording any observed excess cost.
                    cur.execute(OVERAGE_SQL, (actual_cost_micros, actual_cost_micros, token))
                    return False
                cur.execute(CACHE_SQL, (row[0], token, encoded))
                return True

    def fail(self, token, actual_cost_micros=None):
        if actual_cost_micros is not None and (type(actual_cost_micros) is not int or actual_cost_micros < 0):
            raise ValueError("Failure cost must be a nonnegative integer")
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(LOCK_SQL)
                if cur.fetchone() is None:
                    raise RuntimeError("Model budget mutex missing")
                if actual_cost_micros is None:
                    cur.execute(FAIL_SQL, (token,))
                else:
                    cur.execute(OVERAGE_SQL, (actual_cost_micros, actual_cost_micros, token))
