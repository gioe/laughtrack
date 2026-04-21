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
