"""Conservative admission pricing for Squarespace store products.

Ticket persistence has no currency column. Only explicit USD is representable;
amounts are base prices, never estimated totals including fees or minimums.
Parent amounts are placeholders on variant products and must not be consulted.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from laughtrack.foundation.utilities.html.utils import HtmlUtils


def _amount(value: Any, *, cents: bool = False) -> Optional[Decimal]:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0:
            return None
        if cents:
            if amount != amount.to_integral_value():
                return None
            amount /= 100
        # Match the DB's Decimal(7, 2); reject rounding/overflow rather than guess.
        if amount > Decimal("99999.99") or amount != amount.quantize(Decimal("0.01")):
            return None
        return amount
    except InvalidOperation:
        return None


def product_price(raw: dict) -> tuple[Optional[float], bool]:
    """Return (base USD price, sold out) only for one unambiguous variant.

    Multi-option products require admission-unit mapping, so do not select a
    cheapest variant or divide a package. Sold-out prices are not advertised.
    Missing/invalid inventory cannot establish an available offer.
    """
    content = raw.get("structuredContent")
    if not isinstance(content, dict):
        return None, False
    variants = content.get("variants")
    if not isinstance(variants, list) or len(variants) != 1 or not isinstance(variants[0], dict):
        return None, False
    if "variants" in raw and raw["variants"] != variants:
        return None, False
    variant = variants[0]
    stock = variant.get("qtyInStock")
    unlimited = variant.get("unlimited")
    valid_stock = type(stock) is int and stock >= 0
    sold_out = unlimited is False and valid_stock and stock == 0
    if sold_out or not (unlimited is True or (unlimited is False and valid_stock and stock > 0)):
        return None, sold_out
    if variant.get("attributes") or variant.get("optionValues"):
        return None, False
    if content.get("isSubscribable") or content.get("mightHavePaymentPlan"):
        return None, False
    copy = HtmlUtils.strip_tags(f"{raw.get('title') or ''} {raw.get('excerpt') or ''}")
    # The source can sell performer access or bundles rather than one admission.
    if re.search(
        r"\b(?:package|bundle|season pass|table for|tickets? for \d+|\d+[- ]pack)\b"
        r"|\bfree for (?:the )?audience\b|\bcoming to perform\b",
        copy,
        re.IGNORECASE,
    ):
        return None, False
    if variant.get("onSale") is not True and variant.get("onSale") is not False:
        return None, False
    field = "salePrice" if variant["onSale"] else "price"
    money = variant.get(field + "Money")
    if money is not None:
        if not isinstance(money, dict) or money.get("currency") != "USD":
            return None, False
        amount = _amount(money.get("value"))
        # Two representations of the same active amount must agree.
        if field in variant and _amount(variant[field], cents=True) != amount:
            return None, False
    else:
        # Legacy cents require explicit variant currency, not venue inference.
        if variant.get("currency") != "USD":
            return None, False
        amount = _amount(variant.get(field), cents=True)
    if variant.get("currency", "USD") != "USD":
        return None, False
    regular = variant.get("priceMoney")
    if variant["onSale"] and isinstance(regular, dict) and regular.get("currency") != "USD":
        return None, False
    return (float(amount) if amount is not None else None), False
