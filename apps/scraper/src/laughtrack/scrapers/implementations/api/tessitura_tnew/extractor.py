"""Extraction helpers for Tessitura TNEW production-season payloads."""

from typing import Any, Iterable, List
from urllib.parse import urljoin

from laughtrack.core.entities.event.tessitura_tnew import TessituraTNEWEvent


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _performance_title(production: dict[str, Any], performance: dict[str, Any]) -> str:
    title = _clean(performance.get("performanceTitle"))
    if title:
        return title
    title = _clean(performance.get("performanceSortTitle"))
    if title:
        return title
    return _clean(production.get("productionTitle") or production.get("name"))


def extract_events(productions: Iterable[dict[str, Any]], base_url: str) -> List[TessituraTNEWEvent]:
    """Flatten TNEW productions into one event per visible performance."""
    events: List[TessituraTNEWEvent] = []
    for production in productions or []:
        if not isinstance(production, dict):
            continue
        production_title = _clean(production.get("productionTitle") or production.get("name"))
        performances = production.get("performances") or []
        if not isinstance(performances, list):
            continue
        for performance in performances:
            if not isinstance(performance, dict):
                continue
            title = _performance_title(production, performance)
            start_date = _clean(
                performance.get("performanceDate") or performance.get("iso8601DateString")
            )
            action_url = _clean(performance.get("actionUrl") or production.get("actionUrl"))
            if not title or not start_date or not action_url:
                continue
            events.append(
                TessituraTNEWEvent(
                    title=title,
                    production_title=production_title or None,
                    start_date_str=start_date,
                    show_page_url=urljoin(base_url, action_url),
                    is_visible=bool(performance.get("isPerformanceVisible", True)),
                    is_on_sale=performance.get("isOnSale"),
                )
            )
    return events
