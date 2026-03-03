import json
from typing import Any, List

import pytest

from laughtrack.scrapers.implementations.venues.comedy_cellar.extractor import ComedyCellarExtractor
from laughtrack.foundation.models.api.comedy_cellar.models import (
    ComedyCellarLineupAPIResponse,
    ComedyCellarShowsAPIResponse,
    ShowInfoData,
    ShowsInfoData,
    ShowsDataContainer,
    DateAbbreviation,
    ShowAge,
)


def make_lineup_api_response(html: str, api_date: str = "2025-01-01") -> ComedyCellarLineupAPIResponse:
    payload = {
        "show": {"html": html, "date": "Sunday January 1, 2025"},
        "date": api_date,
        "dates": {api_date: "Sunday January 1, 2025"},
    }
    return ComedyCellarLineupAPIResponse.from_dict(payload)


def make_shows_api_response(
    api_date: str,
    shows: List[ShowInfoData],
) -> ComedyCellarShowsAPIResponse:
    show_info = ShowsInfoData(
        date=api_date,
        prettyDate="",
        abbr=DateAbbreviation(day="", month="", date="", pretty=""),
        shows=shows,
        age=ShowAge(seconds=0, time=0),
    )
    return ComedyCellarShowsAPIResponse(message="Ok", data=ShowsDataContainer(showInfo=show_info))


class DummyContainer:
    def __init__(self, label: str):
        self.label = label

    def __str__(self) -> str:
        return f"<container {self.label}>"


@pytest.fixture
def patch_html_scraper(monkeypatch):
    """Patch HtmlScraper methods for deterministic behavior in tests."""
    calls = {"containers": [], "href": {}, "names": {}}

    def mock_find_parent_containers_by_child_class(html: str, tag: str, child_class: str):
        return calls["containers"]

    def mock_extract_nested_link_href(container: Any, class_name: str):
        return calls["href"].get(container)

    def mock_extract_text_from_links_by_href_pattern(container: Any, pattern: str):
        return calls["names"].get(container, [])

    from laughtrack.utilities.infrastructure.html import scraper as html_scraper_module

    monkeypatch.setattr(html_scraper_module.HtmlScraper, "find_parent_containers_by_child_class", mock_find_parent_containers_by_child_class)
    monkeypatch.setattr(html_scraper_module.HtmlScraper, "extract_nested_link_href", mock_extract_nested_link_href)
    monkeypatch.setattr(html_scraper_module.HtmlScraper, "extract_text_from_links_by_href_pattern", mock_extract_text_from_links_by_href_pattern)

    return calls


def test_extract_available_dates_valid():
    payload = {"dates": {"2025-01-01": "Jan 1", "2025-01-02": "Jan 2"}}
    text = json.dumps(payload)
    result = ComedyCellarExtractor.extract_available_dates(text)
    assert set(result) == {"2025-01-01", "2025-01-02"}


def test_extract_available_dates_invalid_json():
    text = "{not json}"
    result = ComedyCellarExtractor.extract_available_dates(text)
    assert result == []


def test_extract_lineup_data_valid():
    text = json.dumps({
        "show": {"html": "<div>OK</div>", "date": "Sunday"},
        "date": "2025-01-01",
        "dates": {"2025-01-01": "Sunday"},
    })
    result = ComedyCellarExtractor.extract_lineup_data(text)
    assert result is not None
    assert result.show.html == "<div>OK</div>"
    assert result.date == "2025-01-01"


def test_extract_shows_data_valid():
    shows_data = {
        "message": "Ok",
        "data": {
            "showInfo": {
                "date": "2025-01-01",
                "prettyDate": "",
                "abbr": {"day": "", "month": "", "date": "", "pretty": ""},
                "shows": [
                    {"id": 123, "time": "20:00:00", "description": "A Show", "roomId": 2, "timestamp": 1}
                ],
                "age": {"seconds": 0, "time": 0},
            }
        },
    }
    result = ComedyCellarExtractor.extract_shows_data(shows_data)
    assert result is not None
    assert result.data.showInfo.date == "2025-01-01"
    assert result.data.showInfo.shows[0].id == 123


def test_extract_events_join_and_date_resolution(monkeypatch, patch_html_scraper):
    # Arrange: HTML containers and scraper patches
    c1 = DummyContainer("one")
    c2 = DummyContainer("two")
    patch_html_scraper["containers"][:] = [c1, c2]
    # Only provide ticket/link for first container; second should be skipped
    patch_html_scraper["href"][c1] = "https://www.comedycellar.com/reservations-newyork/?showid=123"
    patch_html_scraper["names"][c1] = ["Comic A", "Comic B"]

    # API responses
    lineup = make_lineup_api_response(html="<html></html>", api_date="2025-01-01")
    shows = make_shows_api_response(
        api_date="2025-01-01",
        shows=[ShowInfoData(id=123, time="20:00:00", description="A Show", roomId=2, timestamp=1, cover=25)],
    )

    # Act: pass mismatching external date to ensure API date wins
    events = ComedyCellarExtractor.extract_events("2025-01-02", lineup, shows)

    # Assert
    assert len(events) == 1
    e = events[0]
    assert e.show_id == 123
    assert e.date_key == "2025-01-01"  # preferred API date
    assert e.ticket_link.endswith("showid=123")
    assert e.lineup_names == ["Comic A", "Comic B"]
    assert e.room_name == "Village Underground"  # roomId=2 mapping
    assert e.api_time == "20:00:00"
    assert e.show_name == "A Show"


def test_extract_events_no_html_returns_empty(patch_html_scraper):
    lineup = make_lineup_api_response(html="", api_date="2025-01-01")
    shows = make_shows_api_response(api_date="2025-01-01", shows=[])
    events = ComedyCellarExtractor.extract_events(None, lineup, shows)
    assert events == []


def test_extract_events_no_ticket_link_skips_all(monkeypatch, patch_html_scraper):
    c = DummyContainer("one")
    patch_html_scraper["containers"][:] = [c]
    # No href provided => extractor should skip
    lineup = make_lineup_api_response(html="<html></html>", api_date="2025-01-01")
    shows = make_shows_api_response(api_date="2025-01-01", shows=[])
    events = ComedyCellarExtractor.extract_events(None, lineup, shows)
    assert events == []


def test_extract_events_joins_by_timestamp_when_showid_is_timestamp(monkeypatch, patch_html_scraper):
    # HTML uses showid equal to API show.timestamp
    c = DummyContainer("ts")
    patch_html_scraper["containers"][:] = [c]
    patch_html_scraper["href"][c] = "https://www.comedycellar.com/reservations-newyork/?showid=1705434000"
    patch_html_scraper["names"][c] = ["Comic T"]

    lineup = make_lineup_api_response(html="<html></html>", api_date="2025-01-10")
    # API: id is 999 but timestamp matches link's showid
    shows = make_shows_api_response(
        api_date="2025-01-10",
        shows=[ShowInfoData(id=999, time="22:00:00", description="TS Show", roomId=1, timestamp=1705434000)],
    )

    events = ComedyCellarExtractor.extract_events(None, lineup, shows)
    assert len(events) == 1
    e = events[0]
    # show_id in event reflects the lineup link param we parsed (timestamp), not the API id
    assert e.show_id == 1705434000
    assert e.api_time == "22:00:00"
    assert e.room_name == "MacDougal St."
    assert e.show_name == "TS Show"


def test_extract_lineup_names_includes_img_alt_text(monkeypatch, patch_html_scraper):
    # Simulate that visible link text is empty but image alt carries the name
    class Img:
        def __init__(self, alt_text: str):
            self._alt_text = alt_text

        def get(self, key):
            return self._alt_text if key == "alt" else None

    class Link:
        def __init__(self, href: str, alt_text: str):
            self._href = href
            self._alt_text = alt_text

        def get(self, k):
            return self._href if k == "href" else None

        def find_all(self, tag):
            if tag != "img":
                return []
            return [Img(self._alt_text)]

        def get_text(self, strip: bool = True):
            return ""

    class Container:
        def __init__(self, links):
            self._links = links

        def find_all(self, tag, href=None):
            if tag != "a":
                return []
            # emulate BeautifulSoup's callable filter
            if callable(href):
                return [l for l in self._links if href(l.get("href"))]
            return self._links

    # Build a container with one comedian link containing an image with alt text
    link = Link("/comedians/jane-doe", "Jane Doe")
    container = Container([link])

    # Bypass HtmlScraper for this test and call the private method directly
    names = ComedyCellarExtractor._extract_lineup_names(container)
    assert names == ["Jane Doe"]
