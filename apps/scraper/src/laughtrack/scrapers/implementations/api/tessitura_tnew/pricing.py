"""Available TNEW admission selectors, never seat-map price configuration."""

import json
import math
import re
from datetime import datetime
from decimal import Decimal
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.tessitura_tnew import TNEWAdmission, TessituraTNEWEvent, _parse_tnew_datetime
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.foundation.utilities.number import parse_price_text

_ADDON = re.compile(r"talk[\s-]*back|meet[\s-]*(?:and|&)?[\s-]*greet|add[ -]?on|donation|parking", re.I)
_ADMISSION = re.compile(r"\b(?:adult|regular|general admission|standard|student|senior|child|youth)\b", re.I)
_AMOUNT = r"\$([\d,]+\.\d{2})"
_FEE = re.compile(_AMOUNT + r"\s+ticket\s*\+\s*" + _AMOUNT + r"\s+fees", re.I)


def performance_identity(url: str):
    parsed = urlparse(url)
    match = re.fullmatch(r"/(\d+)/(\d+)/?", parsed.path)
    return (parsed.hostname, *match.groups()) if match and parsed.scheme == "https" else None


def best_available_url(html: str, event: TessituraTNEWEvent) -> str | None:
    """Follow only the page's own same-performance switch to standard seating."""
    soup = BeautifulSoup(html or "", "html.parser")
    for link in soup.select("a.tn-ticketing-mode-change__anchor[href]"):
        url = urljoin(event.show_page_url, link["href"])
        if (
            performance_identity(url) == performance_identity(event.show_page_url)
            and performance_identity(url) is not None
            and parse_qs(urlparse(url).query) == {"z": ["0"]}
            and "best available" in link.get_text(" ", strip=True).casefold()
        ):
            return url
    return None


def _disabled(node) -> bool:
    return node.has_attr("disabled") or node.find_parent("fieldset", disabled=True) is not None


def extract_admissions(html: str, event: TessituraTNEWEvent, timezone_name: str) -> list[TNEWAdmission]:
    identity = performance_identity(event.show_page_url)
    if not identity or event.is_on_sale is False or _ADDON.search(event.title):
        return []
    _, production_id, performance_id = identity
    if (event.production_id and event.production_id != production_id) or (
        event.performance_id and event.performance_id != performance_id
    ):
        return []
    model = JSONUtils.extract_json_variable(html, "productDataModel")
    if (
        html.count("var productDataModel =") != 1
        or not isinstance(model, dict)
        or str(model.get("productionSeasonId")) != production_id
        or str(model.get("performanceId")) != performance_id
    ):
        return []
    # Currency is explicit storefront configuration, not inferred from '$'.
    config_match = re.search(r"tnew\.app\.init\(\s*(\{)", html)
    try:
        config, _ = json.JSONDecoder().raw_decode(html, config_match.start(1)) if config_match else ({}, 0)
    except ValueError:
        return []
    if config.get("iso4217CurrencyCode") != "USD" or urlparse(config.get("rootUrl", "")).hostname != identity[0]:
        return []
    soup = BeautifulSoup(html, "html.parser")
    dates = soup.select(".tn-event-detail__display-time")
    forms = soup.select("form#tn-events-detail-best-available-form")
    if len(dates) != 1 or len(forms) != 1:
        return []
    date_text = re.sub(r"^[A-Za-z]+,\s*", "", dates[0].get_text(" ", strip=True))
    try:
        rendered = datetime.strptime(date_text, "%B %d, %Y %I:%M%p")
    except ValueError:
        return []
    expected = _parse_tnew_datetime(event.start_date_str, timezone_name)
    if expected is None or _parse_tnew_datetime(rendered.isoformat(), timezone_name) != expected:
        return []
    form = forms[0]
    if performance_identity(urljoin(event.show_page_url, form.get("action", ""))) != identity:
        return []
    for name, value in (("PerformanceId", performance_id), ("ProductionSeasonId", production_id)):
        inputs = form.select(f'input[name="{name}"]')
        if len(inputs) != 1 or inputs[0].get("value") != value:
            return []

    offers = {}
    for zone in form.select(".tn-ticket-selector__input-zone[data-zone-id]"):
        zone_id = zone["data-zone-id"]
        try:
            count = int(zone.get("data-tn-zone-available-count", "0"))
        except ValueError:
            continue
        if zone_id == "0" or count <= 0 or _disabled(zone):
            continue
        containers = [
            c for c in form.select(".tn-ticket-selector__pricetype-container") if c.get("data-zone-id") == zone_id
        ]
        if len(containers) != 1:
            continue
        container = containers[0]
        heading = container.select_one(".tn-ticket-selector__pricetype-zone-heading")
        zone_name = re.sub(r"^Quantity for\s+", "", heading.get_text(" ", strip=True)) if heading else ""
        if not zone_name or _ADDON.search(zone_name):
            continue
        for tier in container.select(".tn-ticket-selector__pricetype"):
            selector = tier.select_one("select.tn-ticket-selector__pricetype-select")
            name_node = tier.select_one(".tn-ticket-selector__pricetype-name")
            if (
                selector is None
                or name_node is None
                or _disabled(selector)
                or selector.get("data-zone-id") != zone_id
                or selector.get("data-pricetype-id") != tier.get("data-tn-price-type-id")
            ):
                continue
            if not any(
                o.get("value", "").isdigit() and 0 < int(o["value"]) <= count and not o.has_attr("disabled")
                for o in selector.select("option[value]")
            ):
                continue
            text = name_node.get_text(" ", strip=True)
            match = re.fullmatch(r"(.+?)\s+" + _AMOUNT, text)
            if not match or _ADDON.search(text) or not _ADMISSION.search(match[1]):
                continue
            price = parse_price_text(match[0], detect_free=False, dollar_only=True)
            if price is None or not math.isfinite(price) or price <= 0:
                continue
            base = fees = None
            fee_node = tier.select_one(".tn-ticket-selector__pricetype-fee-breakdown")
            if fee_node is not None:
                fee_match = _FEE.fullmatch(fee_node.get_text(" ", strip=True))
                if not fee_match:
                    continue
                base, fees = (Decimal(v.replace(",", "")) for v in fee_match.groups())
                if base <= 0 or fees < 0 or base + fees != Decimal(match[2].replace(",", "")):
                    continue
            offer = TNEWAdmission(
                f"{zone_name} — {match[1]}",
                price,
                float(base) if base is not None else None,
                float(fees) if fees is not None else None,
            )
            key = (zone_id, selector.get("data-pricetype-id"))
            if key in offers and offers[key] != offer:
                return []
            offers[key] = offer
    return list(offers.values())
