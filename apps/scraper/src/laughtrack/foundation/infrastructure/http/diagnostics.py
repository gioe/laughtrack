"""Fetch-layer diagnostics used to self-triage 0-show nightly results.

When a club's nightly scrape returns 0 shows without raising, triage today
requires manually re-running to distinguish a transient WAF challenge from a
genuine empty response or a stale platform ID. This module exposes a
``ScrapeDiagnostics`` container via a ``ContextVar`` so the HTTP client can
record fetch-side signals (status code, bot-block signature, Playwright
fallback) without changing the ``fetch_html`` / ``fetch_json`` return
signatures, and the base scraper can read them back at the end of a scrape.

The HTTP client records into the *currently bound* diagnostics; recording is
a no-op when nothing is bound (e.g. ad-hoc scripts that call ``fetch_html``
outside a scrape).
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Optional

__all__ = [
    "ScrapeDiagnostics",
    "current_diagnostics",
    "bind_diagnostics",
    "reset_diagnostics",
]


@dataclass
class ScrapeDiagnostics:
    """Diagnostics collected during a single club scrape.

    ``http_status`` retains the most-diagnostic code seen — a 5xx or 4xx
    observed on any request wins over a later 200, so the field reflects the
    root cause of an empty result rather than a recovered status from a retry.
    """

    http_status: Optional[int] = None
    bot_block_detected: bool = False
    bot_block_signature: Optional[str] = None
    playwright_fallback_used: bool = False
    items_before_filter: int = 0

    def record_response(self, status_code: int) -> None:
        if self.http_status is None:
            self.http_status = status_code
            return
        if self.http_status == 200 and status_code != 200:
            self.http_status = status_code

    def record_bot_block(self, signature: str) -> None:
        self.bot_block_detected = True
        if self.bot_block_signature is None:
            self.bot_block_signature = signature

    def record_playwright_fallback(self) -> None:
        self.playwright_fallback_used = True

    def add_items_before_filter(self, n: int) -> None:
        if n > 0:
            self.items_before_filter += n


_current: ContextVar[Optional[ScrapeDiagnostics]] = ContextVar(
    "scrape_diagnostics_current", default=None
)


def current_diagnostics() -> Optional[ScrapeDiagnostics]:
    """Return the ScrapeDiagnostics bound to the current context, or None."""
    return _current.get()


def bind_diagnostics(diagnostics: ScrapeDiagnostics) -> Token:
    """Bind *diagnostics* to the current context and return a reset token."""
    return _current.set(diagnostics)


def reset_diagnostics(token: Token) -> None:
    _current.reset(token)
