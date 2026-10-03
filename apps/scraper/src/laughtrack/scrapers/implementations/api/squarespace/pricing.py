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


def explicit_free_admission(event, detail: Any) -> bool:
    """Prove the free improv jam's admission from its dated detail product.

    This deliberately recognizes the captured free-jam pattern, not generic
    mentions of free gifts, conditional discounts or zero parent placeholders.
    """
    import json
    from urllib.parse import urljoin

    from bs4 import BeautifulSoup

    if event.price is not None or event.sold_out or not isinstance(detail, dict):
        return False
    item = detail.get("item", detail)
    if not isinstance(item, dict):
        return False
    full_url = item.get("fullUrl")
    if not isinstance(full_url, str) or not full_url or not event.full_url:
        return False
    base = event.base_domain.rstrip("/") + "/"
    if urljoin(base, full_url) != urljoin(base, event.full_url):
        return False
    title = item.get("title")
    if not isinstance(title, str) or " ".join(title.split()) != " ".join(event.title.split()):
        return False
    start = item.get("startDate")
    if type(start) not in (int, float) or not isinstance(event.start_date_ms, int):
        return False
    # The JSON date is milliseconds; older rendered evidence truncates subsecond
    # precision. Never relax beyond the same second, even for recurring titles.
    if not float(start) // 1000 == event.start_date_ms // 1000:
        return False
    structured = item.get("structuredContent", {})
    if not isinstance(structured, dict) or structured.get("_type") != "CalendarEvent":
        return False
    if structured.get("startDate", start) != start:
        return False
    free_jam = r"^(?:the\s+)?free\s+(?:all\s+)?improv\s+comedy\s+jam\b"
    if not re.match(free_jam, title.strip(), re.IGNORECASE):
        return False
    body = item.get("body")
    if not isinstance(body, str) or len(body) > 256_000:
        return False
    blocks = BeautifulSoup(body, "html.parser").select(".product-block[data-product]")
    if len(blocks) != 1:
        return False
    try:
        product = json.loads(blocks[0]["data-product"])
    except (ValueError, TypeError):
        return False
    if not isinstance(product, dict):
        return False
    product_title = product.get("title")
    if not isinstance(product_title, str) or not re.match(free_jam, product_title.strip(), re.IGNORECASE):
        return False
    copy = HtmlUtils.strip_tags(f"{title} {product_title} {product.get('description') or ''}")
    if re.search(
        r"\b(?:discount|coupon|promo|with purchase|minimum|members? only|donation required|package|bundle)\b",
        copy,
        re.IGNORECASE,
    ):
        return False
    if (
        product.get("published") is not True
        or product.get("soldOut") is not False
        or product.get("onSale") is not False
    ):
        return False
    if product.get("mightHavePaymentPlan") or product.get("isSubscribable"):
        return False
    variants = product.get("variants")
    if not isinstance(variants, list) or len(variants) != 1 or not isinstance(variants[0], dict):
        return False
    variant = variants[0]
    if variant.get("soldOut") is not False or variant.get("attributes") or variant.get("optionValues"):
        return False
    stock = variant.get("qtyInStock")
    if not (
        variant.get("unlimited") is True or (variant.get("unlimited") is False and type(stock) is int and stock > 0)
    ):
        return False
    for money in (product.get("price"), variant.get("price")):
        if not isinstance(money, dict) or money.get("currency") != "USD":
            return False
        value = money.get("value")
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            return False
        try:
            if Decimal(str(value)) != 0:
                return False
        except InvalidOperation:
            return False
    return True
