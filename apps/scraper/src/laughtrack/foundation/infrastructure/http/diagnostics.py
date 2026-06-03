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
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

__all__ = [
    "ScrapeDiagnostics",
    "current_diagnostics",
    "bind_diagnostics",
    "reset_diagnostics",
]


@dataclass
class ScrapeDiagnostics:
    """Diagnostics collected during a single club scrape.

    ``http_status`` is sticky on the first non-200 code seen — once a 4xx or
    5xx is recorded, a subsequent 200 cannot overwrite it. Within non-200
    codes, the first-seen wins (e.g. 403 then 503 leaves ``http_status=403``).
    The goal is to surface the root cause of an empty result rather than a
    recovered status from a later retry; picking "which non-200 is most
    diagnostic" is a judgement call we intentionally don't make in the
    recorder — the first failure is typically the one worth investigating.
    """

    http_status: Optional[int] = None
    bot_block_detected: bool = False
    bot_block_signature: Optional[str] = None
    bot_block_provider: Optional[str] = None
    bot_block_type: Optional[str] = None
    bot_block_source: Optional[str] = None
    bot_block_stage: Optional[str] = None
    playwright_fallback_used: bool = False
    items_before_filter: int = 0
    # Per-stage counters used to distinguish a genuinely empty venue calendar
    # from a broken-fetch / broken-parser failure at run-end. fetches_ok counts
    # exception-free returns from get_data() (None or non-None); fetches_failed
    # counts exceptions out of the retry-wrapped fetch.
    targets_collected: int = 0
    fetches_ok: int = 0
    fetches_failed: int = 0
    # Cross-host redirect dedup. Keyed on (original_host, final_host); the HTTP
    # client logs at most one WARN per tuple per scrape run so a fan-out that
    # fetches 300+ price-detail pages from the same uncanonical host emits one
    # actionable signal instead of 300 (TASK-2559 incident on OTH).
    cross_host_redirects_warned: set[tuple[str, str]] = field(default_factory=set)
    # Per-venue persist-layer lock timeouts. Recorded as (venue_label,
    # dropped_event_count) tuples by scrapers that swallow LockHeldError /
    # asyncio.TimeoutError inside a fan-out (currently EventbriteScraper's
    # organizer mode) so the events are not silently dropped: scrape_with_result
    # surfaces this list to ClubScrapingResult.error with a 'lock_timeout:'
    # prefix, which keeps the per-venue WARN logs intact AND populates the
    # metric row's error field so Grafana can alert on lock-timeout
    # specifically rather than on the generic zero-show outcome.
    persist_lock_timeouts: List[Tuple[str, int]] = field(default_factory=list)

    def record_response(self, status_code: int) -> None:
        if self.http_status is None:
            self.http_status = status_code
            return
        if self.http_status == 200 and status_code != 200:
            self.http_status = status_code

    def record_bot_block(
        self,
        signature: str,
        *,
        provider: Optional[str] = None,
        block_type: Optional[str] = None,
        source: Optional[str] = None,
        stage: str = "direct_fetch",
    ) -> None:
        self.bot_block_detected = True
        if self.bot_block_signature is None:
            self.bot_block_signature = signature
        inferred_provider, inferred_type = _infer_block_details(signature)
        if self.bot_block_provider is None:
            self.bot_block_provider = provider or inferred_provider
        if self.bot_block_type is None:
            self.bot_block_type = block_type or inferred_type
        if self.bot_block_source is None:
            self.bot_block_source = source
        self.bot_block_stage = _merge_block_stage(self.bot_block_stage, stage)

    def record_playwright_fallback(self) -> None:
        self.playwright_fallback_used = True

    def add_items_before_filter(self, n: int) -> None:
        if n > 0:
            self.items_before_filter += n

    def record_targets_collected(self, n: int) -> None:
        if n > 0:
            self.targets_collected += n

    def record_fetch_ok(self) -> None:
        self.fetches_ok += 1

    def record_fetch_failed(self) -> None:
        self.fetches_failed += 1

    def note_cross_host_redirect(self, original_host: str, final_host: str) -> bool:
        """Record a cross-host redirect tuple. Returns True if this is the
        first time the tuple has been seen this scrape (caller should emit
        the WARN); False if a prior fetch already warned about it."""
        key = (original_host, final_host)
        if key in self.cross_host_redirects_warned:
            return False
        self.cross_host_redirects_warned.add(key)
        return True

    def record_persist_lock_timeout(self, venue_label: str, dropped_events: int) -> None:
        """Record that a venue's persist-layer write timed out on
        ``_DB_WRITE_LOCK`` (either ``LockHeldError`` from the fail-fast
        acquire or ``asyncio.TimeoutError`` from the per-venue wait_for
        bound).

        Caller's existing per-venue ERROR log still names the venue and the
        timeout shape; this records the (venue, dropped_event_count) tuple
        so the run-end aggregation in ``scrape_with_result`` can surface the
        incident to ``ClubScrapingResult.error`` with the ``lock_timeout:``
        prefix. Without that surface, an Eventbrite organizer scrape whose
        only failure was a lock-timeout dropped its N events silently
        (the metric row recorded success=true, num_shows=0, error=null —
        the original incident in TASK-2626).
        """
        self.persist_lock_timeouts.append((venue_label, dropped_events))


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


def _infer_block_details(signature: str) -> tuple[Optional[str], Optional[str]]:
    normalized = signature.lower()
    if normalized.startswith("playwright_"):
        normalized = normalized.removeprefix("playwright_")

    if "datadome" in normalized or "captcha-delivery.com" in normalized:
        if "captcha" in normalized:
            return "datadome", "captcha"
        return "datadome", "interstitial"

    if (
        "just a moment" in normalized
        or "_cf_chl_opt" in normalized
        or "enable javascript and cookies to continue" in normalized
    ):
        return "cloudflare", "challenge"

    if "access denied" in normalized:
        return "generic_waf", "interstitial"

    return None, None


def _merge_block_stage(existing: Optional[str], incoming: Optional[str]) -> Optional[str]:
    if incoming is None:
        return existing
    if existing in (None, incoming):
        return incoming
    if existing == "both" or incoming == "both":
        return "both"
    if {existing, incoming} == {"direct_fetch", "playwright_fallback"}:
        return "both"
    return existing
