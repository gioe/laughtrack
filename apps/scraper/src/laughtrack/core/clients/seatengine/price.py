"""Shared price coercion for SeatEngine inventory rows.

Both the SeatEngine v1 JSON API (``services.seatengine.com/api/v1/venues/{id}/shows/{sid}``)
and the classic SeatEngine HTML pages (``cdn.seatengine.com/.../shows/{id}``,
parsed via ``window.seat_engine_app_config``) carry inventory entries shaped like::

    {"id": 1, "name": "...", "price": 3500, ...}   # price is integer cents

The price field is occasionally used as a sentinel marker — e.g. a "Closed for
4th of July" placeholder show priced at 100_000_000¢ (=$1,000,000.00). The
catalog stores ``tickets.price`` as ``Decimal(7, 2)`` (cap $99,999.99), so any
sentinel like this overflows on insert and Postgres drops the whole batch —
costing every other show in that batch its price data.

The fix lives at the inventory boundary: treat anything over a sane comedy
ticket ceiling as a data error and drop it (return ``None``), so the row
either falls back to a NULL ticket price or a different inventory's real
price is used. We deliberately do NOT clamp to the ceiling — a clamped value
would silently pollute downstream price stats; NULL is the correct signal
for "we don't know the real price."

Logging the drop is a separate caller concern (Logger context differs between
the client and the classic extractor), so the helper returns a sentinel tuple
that lets the caller emit a structured warning if it wants one.
"""

from typing import Optional, Tuple

INVENTORY_PRICE_CEILING_CENTS = 100_000
"""Reject inventory prices over this value (in cents).

$1000 is well above any real comedy ticket — premium / meet-and-greet tiers
top out around $150 — and well below the $99,999.99 Decimal(7,2) ceiling, so
sentinel placeholders ($100k / $1M) get caught cleanly while leaving real
high-end tiers untouched.
"""


def coerce_inventory_price_cents(raw: object) -> Tuple[Optional[float], Optional[str]]:
    """Convert a raw ``inventory['price']`` value (integer cents) to dollars.

    The SeatEngine v1 JSON API and the classic ``window.seat_engine_app_config``
    embedded JSON both document ``price`` as an integer number of cents — any
    fractional input is coerced via ``int(raw)`` and truncated toward zero,
    matching the existing classic-extractor behavior and the integer-only
    contract. If SeatEngine ever returns a float-shaped cents value, treat
    that as an upstream bug rather than relaxing the truncation here.

    Returns ``(price_dollars, reject_reason)``:

    - ``(price, None)`` when the value parses as a positive integer at or below
      ``INVENTORY_PRICE_CEILING_CENTS``.
    - ``(None, None)`` when the value is ``None``, non-numeric, or non-positive
      — the existing "missing / extraction-failure" behavior callers already
      treat as NULL.
    - ``(None, "<reason>")`` when the value parses but exceeds the ceiling.
      The reason string is short and includes the raw cents value so callers
      can emit one warning per drop without re-formatting.
    """
    if raw is None:
        return None, None
    try:
        cents = int(raw)
    except (TypeError, ValueError):
        return None, None
    if cents <= 0:
        return None, None
    if cents > INVENTORY_PRICE_CEILING_CENTS:
        return None, (
            f"inventory price {cents}¢ (${cents / 100:,.2f}) exceeds "
            f"${INVENTORY_PRICE_CEILING_CENTS / 100:.0f} ceiling — treating as sentinel"
        )
    return cents / 100.0, None
