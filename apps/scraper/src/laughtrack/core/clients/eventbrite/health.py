"""Startup health check for the Eventbrite API token.

A stale ``EVENTBRITE_PRIVATE_TOKEN`` produces silent HTTP 401s scattered
across every Eventbrite-backed venue, which look identical to per-venue
WAF blocks in nightly summaries. This module pings ``/v3/users/me/`` once
at startup and aborts the run with a single loud ERROR if the credential
is missing or rejected, so the operator knows to rotate/sync the secret.
"""
from __future__ import annotations

import os
import sys

import requests

from laughtrack.foundation.infrastructure.logger.logger import Logger

USERS_ME_URL = "https://www.eventbriteapi.com/v3/users/me/"
TOKEN_ENV_VAR = "EVENTBRITE_PRIVATE_TOKEN"
REQUEST_TIMEOUT_SEC = 10


def validate_eventbrite_token() -> None:
    """Ping ``/v3/users/me/`` with the configured token; exit 1 on failure.

    Raises ``SystemExit(1)`` if the env var is unset or the API rejects the
    token. ``SystemExit`` is a ``BaseException`` so it bypasses any broad
    ``except Exception`` in the caller and aborts the process cleanly with a
    single ERROR-level log.
    """
    token = os.getenv(TOKEN_ENV_VAR)
    if not token:
        Logger.error(
            f"{TOKEN_ENV_VAR} is not set. Eventbrite-backed venues would all "
            f"fail with 401 — aborting before per-venue scrape. Set the secret "
            f"in GHA (or apps/scraper/.env locally) and rerun."
        )
        sys.exit(1)

    try:
        response = requests.get(
            USERS_ME_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT_SEC,
        )
    except requests.RequestException as e:
        Logger.error(
            f"{TOKEN_ENV_VAR} validation request to {USERS_ME_URL} failed: {e}. "
            f"Cannot confirm token validity — aborting before per-venue scrape."
        )
        sys.exit(1)

    if response.status_code != 200:
        Logger.error(
            f"{TOKEN_ENV_VAR} rejected by Eventbrite — {USERS_ME_URL} returned "
            f"HTTP {response.status_code}. Rotate the token in Eventbrite and "
            f"sync the GHA secret EVENTBRITE_PRIVATE_TOKEN, then rerun."
        )
        sys.exit(1)

    Logger.info(f"Eventbrite token validated via {USERS_ME_URL}")
