"""Odoo-only association of detached registration tiers with an exact Event."""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.event import JsonLdEvent, Offer
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor

_EVENT_PATH = re.compile(r"(/event/[^/]+-(\d+))/(register|registration/new)/?$")
_PACKAGE = re.compile(r"\b(table|package|bundle|group|couple|pair)\b|\bfor\s+\d+", re.I)
_EXTRA = re.compile(r"\b(donation|parking|merchandise|t-shirt|drink|meal|add-on)\b", re.I)


def _identity(url):
    try:
        parsed = urlsplit(url)
        path = _EVENT_PATH.fullmatch(parsed.path)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc or not path:
            return None
        return parsed.scheme, parsed.netloc.lower(), path[1], path[2], path[3]
    except (ValueError, TypeError, AttributeError):
        return None


def _value(row, prop):
    elements = row.select(f'[itemprop="{prop}"]')
    if len(elements) != 1:
        return ""
    element = elements[0]
    return (element.get("content") or element.get("href") or element.get_text(" ", strip=True)).strip()


@dataclass
class RegistrationOffers:
    name: str
    start: datetime
    url: str
    offers: list[Offer]

    def matches(self, event: JsonLdEvent) -> bool:
        return (
            event.name == self.name and event.start_date == self.start and _identity(event.url) == _identity(self.url)
        )


def extract_registration_offers(html: str, url: str) -> RegistrationOffers | None:
    identity = _identity(url)
    if identity is None or identity[-1] != "register":
        return None
    soup = BeautifulSoup(html or "", "html.parser")
    scopes = [s for s in soup.select("[itemscope]") if EventExtractor._itemtype_matches(s, "Event")]
    if len(scopes) != 1:
        return None
    scope = scopes[0]
    event_ids = {node.get("data-res-id") for node in scope.select('[data-res-model="event.event"]')}
    if event_ids and event_ids != {identity[3]}:
        return None
    if not event_ids and not EventExtractor._microdata_value(scope, "url"):
        return None
    raw = EventExtractor._microdata_event(scope, url_fallback=url)
    if not raw or _identity(urljoin(url, raw["url"])) != identity:
        return None
    try:
        start = datetime.fromisoformat(raw["startDate"].replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None
    forms = soup.select("form#registration_form")
    if len(forms) != 1:
        return None
    form = forms[0]
    action = _identity(urljoin(url, form.get("action", "")))
    if not action or action[:-1] != identity[:-1] or action[-1] != "registration/new":
        return None
    if str(form.get("method", "")).lower() != "post":
        return None
    offers = []
    for row in form.select(".o_wevent_registration_single, .o_wevent_ticket_selector"):
        name = _value(row, "name")
        if not name or _EXTRA.search(name):
            continue
        currency = _value(row, "priceCurrency").upper()
        availability = _value(row, "availability").rstrip("/").rsplit("/", 1)[-1]
        selectors = row.select('select[name^="nb_register-"]')
        quantity_available = False
        if len(selectors) == 1:
            selector = selectors[0]
            if not selector.has_attr("disabled") and not selector.find_parent("fieldset", disabled=True):
                for option in selector.select("option:not([disabled])"):
                    if option.find_parent("optgroup", disabled=True):
                        continue
                    value = option.get("value", option.get_text(strip=True))
                    if str(value).isdigit() and int(value) > 0:
                        quantity_available = True
        # Some Odoo multi-tier forms omit schema availability. Enabled positive
        # quantities are purchase evidence; the JS-controlled submit isn't.
        available = quantity_available and availability in {"", "InStock", "LimitedAvailability"}
        if not availability:
            availability = "InStock" if available else "NotOnSale"
        try:
            amount = Decimal(_value(row, "price"))
            if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000"):
                amount = None
        except InvalidOperation:
            amount = None
        numeric = amount if available and currency == "USD" and not _PACKAGE.search(name) else None
        if numeric is None and amount is not None:
            name += f" ({currency or 'currency unspecified'} {amount})"
        if not available:
            name += f" [{availability}; quantity unavailable]"
        # Shared tickets have no currency/unit field and their minimum includes
        # sold-out tiers. Keep unsupported/package amounts in the label only.
        offers.append(
            Offer(
                url=url,
                price_currency=currency,
                price=str(numeric) if numeric is not None else "",
                availability="SoldOut" if availability in {"OutOfStock", "Discontinued"} else availability,
                name=name,
            )
        )
    return RegistrationOffers(raw["name"], start, url, offers)
