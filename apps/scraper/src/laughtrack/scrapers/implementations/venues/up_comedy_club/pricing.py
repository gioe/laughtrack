"""Second City identity/availability checks before PatronTicket tier normalization."""

from urllib.parse import urlparse

from laughtrack.scrapers.implementations.venues.patron_ticket.extractor import _extract_ticket_tiers


def source_bool(value):
    """Keep unknown distinct from the source's boolean and string encodings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int)):
        normalized = str(value).strip().lower()
        if normalized in ("true", "1"):
            return True
        if normalized in ("false", "0"):
            return False
    return None


def currency_for(instance, ticket_data):
    explicit = instance.get("currency") or ticket_data.get("currency")
    if explicit:
        return str(explicit).upper()
    if urlparse(instance.get("purchaseUrl", "")).hostname in {
        "us.tickets.secondcity.com", "secondcityus.my.salesforce-sites.com"
    }:
        return "USD"
    return None


def sale_state(instance):
    if source_bool(instance.get("soldOut")) is True:
        return "sold_out"
    state = str(instance.get("saleState") or "").lower()
    on_sale = source_bool(instance.get("onSale"))
    if state == "soldout":
        return "sold_out"
    if on_sale is False or (state and state != "onsale"):
        return "unavailable"
    if on_sale is True or state == "onsale":
        return "on_sale"
    return "unknown"


def ticket_tiers(instance, currency, state):
    """Reuse decimal fee addition and unique tier naming after validating identity.

    Amounts are dollars per admission, including only the explicit resolver fee.
    Missing fee is unknown, not an invented zero. Ticket cannot store non-USD.
    """
    allocations = instance.get("allocations")
    if not isinstance(allocations, list):
        return []
    normalized = []
    for allocation in allocations:
        if not isinstance(allocation, dict):
            continue
        if allocation.get("instanceId") and allocation["instanceId"] != instance.get("id"):
            continue
        levels = allocation.get("levels")
        if not isinstance(levels, list):
            continue
        sold_out = source_bool(allocation.get("soldOut"))
        accepted = []
        for level in levels:
            if not isinstance(level, dict):
                continue
            if level.get("allocationId") and level["allocationId"] != allocation.get("id"):
                continue
            level_currency = level.get("currency", currency)
            price_known = (
                currency == "USD" and level_currency == "USD"
                and (state == "sold_out" or (state == "on_sale" and sold_out is not None))
            )
            accepted.append({**level, "price": level.get("price") if price_known else None,
                             "fee": level.get("fee")})
        normalized.append({**allocation, "soldOut": sold_out is True, "levels": accepted})
    return _extract_ticket_tiers({"allocations": normalized}, state == "sold_out")
