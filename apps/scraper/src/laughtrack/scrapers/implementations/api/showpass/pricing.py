"""Strictly matched public Showpass detail evidence with a USD numeric guard."""

import re
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from laughtrack.core.entities.event.showpass import ShowpassEvent, ShowpassOffer

_PACKAGE = re.compile(
    r"\b(bogo|dinner|meal|table|package|bundle|group|couple|pair|half.off|half.price)\b|\bfor\s+\d+", re.I
)
_ADMISSION = re.compile(r"\b(admission|ticket|vip|reserved|balcony|standard)\b", re.I)
_EXTRA = re.compile(r"\b(donation|parking|merchandise|t-shirt|add-on)\b", re.I)


def _date(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def _amount(value):
    try:
        amount = Decimal(str(value))
        return amount if amount.is_finite() and 0 < amount <= 1000000 else None
    except InvalidOperation:
        return None


def _available(detail, tier, now):
    stats = detail.get("stats")
    if not isinstance(stats, dict) or stats.get("is_available") is not True:
        return False
    if detail.get("is_published") is not True or detail.get("status") != "sp_event_active":
        return False
    if detail.get("sold_out") is not False or tier.get("sold_out") is not False:
        return False
    for source, flags in [
        (
            detail,
            (
                "inventory_sold_out",
                "public_inventory_sold_out",
                "is_password_protected",
                "is_protected_by_queue",
                "is_waitlisted",
            ),
        ),
        (tier, ("is_password_protected", "voucher_purchases_only", "is_connect_voucher", "has_payment_plans")),
    ]:
        if any(source.get(flag) for flag in flags):
            return False
    if detail.get("region_is_allowed") is False:
        return False
    start, end = _date(tier.get("sale_starts_on")), _date(tier.get("sale_ends_on"))
    if start is None or end is None or not start <= now < end:
        return False
    if detail.get("event_sale_starts_on"):
        event_start = _date(detail["event_sale_starts_on"])
        if event_start is None or now < event_start:
            return False
    inventory = tier.get("inventory_left")
    if inventory is None:
        inventory = tier.get("inventory")
    if isinstance(inventory, bool) or not isinstance(inventory, (int, float)) or inventory <= 0:
        return False
    limit = tier.get("purchase_limit")
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0):
        return False
    return True


def extract_offers(detail: dict, event: ShowpassEvent, now: datetime | None = None) -> list[ShowpassOffer]:
    now = now or datetime.now(timezone.utc)
    if not isinstance(detail, dict) or detail.get("id") != event.event_id or event.event_id <= 0:
        return []
    start = _date(detail.get("starts_on"))
    if start is None or start != _date(event.starts_on) or detail.get("slug") != event.slug:
        return []
    tiers = detail.get("ticket_types")
    if not isinstance(tiers, list):
        return []
    currency = detail.get("currency")
    currency = currency.strip().upper() if isinstance(currency, str) else ""
    offers = []
    for tier in tiers:
        if not isinstance(tier, dict) or tier.get("event") != event.event_id:
            continue
        name = tier.get("name")
        if not isinstance(name, str) or not name.strip() or _EXTRA.search(name):
            continue
        tier_currency = tier.get("currency", currency)
        tier_currency = tier_currency.strip().upper() if isinstance(tier_currency, str) else ""
        if tier_currency != currency:
            continue
        minimum = tier.get("minimum_purchase_limit")
        individual = (
            bool(_ADMISSION.search(name))
            and not _PACKAGE.search(name + " " + str(tier.get("description") or ""))
            and not tier.get("is_bundle")
            and not tier.get("is_custom_package")
            and (minimum is None or (type(minimum) is int and minimum == 1))
        )
        fees = tier.get("fees_pricing_info")
        web = fees.get("psp_web", {}) if isinstance(fees, dict) else {}
        quotes = {}
        if isinstance(web, dict):
            for option, values in web.items():
                if isinstance(values, dict):
                    quotes[str(option)] = {
                        key: amount
                        for key in ("total_price_no_tax", "total_price")
                        if (amount := _amount(values.get(key))) is not None
                    }
        sold_out = (
            event.sold_out
            or any(detail.get(flag) is True for flag in ("sold_out", "inventory_sold_out", "public_inventory_sold_out"))
            or tier.get("sold_out") is True
        )
        offers.append(
            ShowpassOffer(
                deepcopy(tier),
                currency,
                _amount(tier.get("price")),
                not event.sold_out and _available(detail, tier, now),
                sold_out,
                bool(individual),
                quotes,
            )
        )
    return offers
