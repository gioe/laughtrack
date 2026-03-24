"""
Lightweight database utilities that are importable without the full app stack.

Use these in standalone scripts (e.g. bin/migrate) that only have a raw DATABASE_URL
and cannot load ConfigManager or the rest of the application stack.
"""

import time

import psycopg2

_CONNECT_RETRY_DELAYS = (1, 2, 4)  # seconds between attempts; total max wait ~7s


def connect_with_retry(
    dsn: str,
    retries: tuple = _CONNECT_RETRY_DELAYS,
) -> psycopg2.extensions.connection:
    """
    Connect to PostgreSQL with exponential-backoff retries for transient failures
    (e.g. Neon auto-suspend wakeups).

    Args:
        dsn: PostgreSQL connection string (DSN / URL format).
        retries: Sequence of sleep durations (seconds) between attempts.
                 The first attempt is made immediately; each entry adds one retry.

    Returns:
        An open psycopg2 connection.

    Raises:
        psycopg2.OperationalError: If all attempts fail.
    """
    last_err: psycopg2.OperationalError | None = None
    for delay in (None, *retries):
        if delay is not None:
            time.sleep(delay)
        try:
            return psycopg2.connect(dsn)
        except psycopg2.OperationalError as exc:
            last_err = exc
    assert last_err is not None
    raise last_err
