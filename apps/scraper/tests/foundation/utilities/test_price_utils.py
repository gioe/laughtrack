from laughtrack.foundation.utilities.number import parse_price_text


def test_parse_price_text_simple_dollar_amount():
    assert parse_price_text("$25") == 25.0
    assert parse_price_text("$25.50") == 25.5


def test_parse_price_text_bare_number_without_dollar_sign():
    assert parse_price_text("25") == 25.0
    assert parse_price_text("18.00") == 18.0


def test_parse_price_text_free_returns_zero():
    assert parse_price_text("Free") == 0.0
    assert parse_price_text("FREE admission") == 0.0
    assert parse_price_text("Free ($0 cover)") == 0.0


def test_parse_price_text_range_returns_minimum():
    assert parse_price_text("$20-$30") == 20.0
    assert parse_price_text("$30 to $20") == 20.0
    assert parse_price_text("$45 - $65 + fees") == 45.0


def test_parse_price_text_strips_thousands_separators():
    assert parse_price_text("$1,234.50") == 1234.5
    assert parse_price_text("$2,000") == 2000.0


def test_parse_price_text_none_when_no_numeric_signal():
    assert parse_price_text("") is None
    assert parse_price_text(None) is None
    assert parse_price_text("Sold out") is None
    assert parse_price_text("Call for pricing") is None


def test_parse_price_text_free_takes_precedence_over_numbers():
    # "Free" wins even if an unrelated number is present in the string.
    assert parse_price_text("Free show, doors at 7") == 0.0


def test_parse_price_text_free_requires_word_boundary():
    # A substring match would wrongly treat these as free and discard the price;
    # a word boundary keeps the real price.
    assert parse_price_text("Freezing cold beers $10") == 10.0
    assert parse_price_text("Freestyle comedy night $15") == 15.0


def test_parse_price_text_prefers_dollar_anchored_amount_over_stray_numbers():
    # A stray leading number (e.g. a time) should not beat the $-anchored price.
    assert parse_price_text("7:30pm show $25") == 25.0


def test_parse_price_text_detect_free_false_ignores_free_substring():
    # Broad-HTML callers pass detect_free=False so an incidental "free" in a
    # paid show's markup does not false-positive to 0.0 and discard the price.
    html = '<div class="free-shipping">Tickets $25 — free parking</div>'
    assert parse_price_text(html, detect_free=False) == 25.0
    # Default still treats whole-word "free" as 0.0.
    assert parse_price_text("Free parking, $25 show") == 0.0


def test_parse_price_text_detect_free_false_still_returns_min_of_dollars():
    # detect_free=False keeps the min-of-$ range behaviour for HTML scanners.
    assert parse_price_text("$30 GA / $20 balcony", detect_free=False) == 20.0
    # No dollar amount and no free detection -> None (unknown), not 0.0.
    assert parse_price_text("Free show", detect_free=False) is None
