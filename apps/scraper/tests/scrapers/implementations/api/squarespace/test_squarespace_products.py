"""Unit tests for the Squarespace products/store-collection path (TASK-3012).

Some venues (e.g. Westside Improv Studio) sell each show as a dated store
product instead of using an Events collection, so GetItemsByMonth returns [].
extract_products parses the show date from the product fullUrl slug
(/tickets/p/june-19-2026) and the time from the title (@8pm).
"""

import json
import os
from datetime import datetime, timezone

from laughtrack.scrapers.implementations.api.squarespace.extractor import (
    SquarespaceExtractor,
)

_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "westside_improv_products.json"
)
_BASE = "https://westsideimprov.com"
_TZ = "America/Chicago"


def _items():
    with open(_FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)["items"]


def _utc(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


class TestExtractProducts:
    def test_parses_dated_products_skips_undatable(self):
        events = SquarespaceExtractor.extract_products(_items(), _BASE, timezone_name=_TZ)
        # "Gift Card" has no parseable date in slug or title -> skipped.
        assert len(events) == 2
        assert {e.id for e in events} == {"p1", "p2"}

    def test_date_from_slug_and_time_from_title(self):
        events = SquarespaceExtractor.extract_products(_items(), _BASE, timezone_name=_TZ)
        by_id = {e.id: e for e in events}
        # June 19 2026 @ 8pm CDT == 2026-06-20T01:00:00Z
        assert _utc(by_id["p1"].start_date_ms).isoformat() == "2026-06-20T01:00:00+00:00"
        # June 21 2026 @ 7pm CDT == 2026-06-22T00:00:00Z
        assert _utc(by_id["p2"].start_date_ms).isoformat() == "2026-06-22T00:00:00+00:00"

    def test_show_page_url_and_title_preserved(self):
        events = SquarespaceExtractor.extract_products(_items(), _BASE, timezone_name=_TZ)
        p1 = next(e for e in events if e.id == "p1")
        assert p1.full_url == "/tickets/p/june-19-2026"
        assert p1.base_domain == _BASE
        assert "Friday Night Show" in p1.title

    def test_to_show_round_trips_local_date(self):
        events = SquarespaceExtractor.extract_products(_items(), _BASE, timezone_name=_TZ)

        class _Club:
            id = 1
            timezone = _TZ
            name = "Westside Improv Studio"

        show = next(e for e in events if e.id == "p1").to_show(_Club(), enhanced=False)
        assert show is not None
        # Local Chicago datetime should read back as June 19, 8pm.
        assert show.date.strftime("%Y-%m-%d %H:%M") == "2026-06-19 20:00"

    def test_exclude_title_filter_applies(self):
        import re

        events = SquarespaceExtractor.extract_products(
            _items(), _BASE, timezone_name=_TZ,
            exclude_title_res=[re.compile(r"sunday", re.IGNORECASE)],
        )
        assert {e.id for e in events} == {"p1"}

    def test_default_hour_when_no_time_in_title(self):
        items = [{"id": "x", "title": "July 4: Special Show", "fullUrl": "/tickets/p/july-4-2026"}]
        events = SquarespaceExtractor.extract_products(items, _BASE, timezone_name=_TZ)
        assert len(events) == 1
        # No @time -> default 19:00 local (CDT) == 2026-07-05T00:00:00Z
        assert _utc(events[0].start_date_ms).isoformat() == "2026-07-05T00:00:00+00:00"

    def test_non_list_input_returns_empty(self):
        assert SquarespaceExtractor.extract_products({}, _BASE, timezone_name=_TZ) == []

    def test_non_month_word_not_parsed_as_date(self):
        # "marathon" must NOT match March via a 3-char prefix (review #3038); with
        # no datable slug, the product is skipped rather than mis-dated.
        items = [{"id": "z", "title": "Marathon 5 Training Night", "fullUrl": "/tickets/p/marathon-night"}]
        assert SquarespaceExtractor.extract_products(items, _BASE, timezone_name=_TZ) == []

    def test_full_month_name_in_slug_parsed(self):
        items = [{"id": "d", "title": "NYE Bash @9pm", "fullUrl": "/tickets/p/december-31-2026"}]
        events = SquarespaceExtractor.extract_products(items, _BASE, timezone_name=_TZ)
        assert len(events) == 1
        # Dec 31 2026 @ 9pm CST == 2027-01-01T03:00:00Z
        assert _utc(events[0].start_date_ms).isoformat() == "2027-01-01T03:00:00+00:00"
