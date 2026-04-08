"""Tests for platform-specific comedian website extractors."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.scrapers.implementations.api.comedian_websites.platform_extractors import (
    KomiExtractorForComedian,
    SquarespaceExtractorForComedian,
    WixExtractorForComedian,
    _bandsintown_event_to_show,
    _is_valid_squarespace_event,
    detect_website_platform,
    detect_website_platform_from_html,
)


# ------------------------------------------------------------------ #
# detect_website_platform                                              #
# ------------------------------------------------------------------ #


class TestDetectWebsitePlatform:
    def test_squarespace_subdomain(self):
        assert detect_website_platform("https://mysite.squarespace.com/") == "squarespace"

    def test_squarespace_with_path(self):
        assert detect_website_platform("https://mysite.squarespace.com/shows") == "squarespace"

    def test_wix_subdomain(self):
        assert detect_website_platform("https://user.wixsite.com/mysite") == "wix"

    def test_komi_subdomain(self):
        assert detect_website_platform("https://chriskattan.komi.io/") == "komi"

    def test_custom_domain(self):
        assert detect_website_platform("https://www.mycomedysite.com") is None

    def test_empty_url(self):
        assert detect_website_platform("") is None

    def test_none_url(self):
        assert detect_website_platform(None) is None

    def test_invalid_url(self):
        assert detect_website_platform("not-a-url") is None


# ------------------------------------------------------------------ #
# detect_website_platform_from_html                                    #
# ------------------------------------------------------------------ #


class TestDetectWebsitePlatformFromHtml:
    def test_squarespace_context_marker(self):
        html = '<script>Static.SQUARESPACE_CONTEXT = {"collection": {"type": 10}};</script>'
        assert detect_website_platform_from_html(html) == "squarespace"

    def test_wix_events_marker(self):
        html = '<div data-hook="wix-one-events">...</div>'
        assert detect_website_platform_from_html(html) == "wix"

    def test_squarespace_takes_precedence_over_wix(self):
        html = 'Static.SQUARESPACE_CONTEXT = {} wix-one-events'
        assert detect_website_platform_from_html(html) == "squarespace"

    def test_plain_html_returns_none(self):
        assert detect_website_platform_from_html("<html><body>Hello</body></html>") is None

    def test_empty_string_returns_none(self):
        assert detect_website_platform_from_html("") is None

    def test_none_returns_none(self):
        assert detect_website_platform_from_html(None) is None


# ------------------------------------------------------------------ #
# SquarespaceExtractorForComedian                                      #
# ------------------------------------------------------------------ #


class TestSquarespaceCollectionDiscovery:
    def _make_html(self, collection_type=10, collection_id="abc123"):
        ctx = json.dumps({"collection": {"type": collection_type, "id": collection_id}})
        return f"<script>Static.SQUARESPACE_CONTEXT = {ctx};</script>"

    def test_discovers_events_collection(self):
        html = self._make_html(collection_type=10, collection_id="5e1e1d6f0d59cc2863ef0e90")
        assert SquarespaceExtractorForComedian.discover_collection_id(html) == "5e1e1d6f0d59cc2863ef0e90"

    def test_ignores_non_events_collection(self):
        html = self._make_html(collection_type=1, collection_id="5e1e1d6f0d59cc2863ef0e90")
        assert SquarespaceExtractorForComedian.discover_collection_id(html) is None

    def test_no_squarespace_context(self):
        assert SquarespaceExtractorForComedian.discover_collection_id("<html></html>") is None

    def test_invalid_json(self):
        html = "<script>Static.SQUARESPACE_CONTEXT = {invalid;};</script>"
        assert SquarespaceExtractorForComedian.discover_collection_id(html) is None


class TestSquarespaceEventValidation:
    def _make_event(self, **overrides):
        future_ms = int((datetime.now(tz=timezone.utc) + timedelta(days=30)).timestamp() * 1000)
        event = {
            "id": "evt1",
            "title": "Comedy Night",
            "startDate": future_ms,
            "fullUrl": "/calendar/2026/5/1/comedy-night",
            "excerpt": "<p>Great show</p>",
        }
        event.update(overrides)
        return event

    def test_valid_future_event(self):
        assert _is_valid_squarespace_event(self._make_event()) is True

    def test_rejects_past_event(self):
        past_ms = int((datetime.now(tz=timezone.utc) - timedelta(days=30)).timestamp() * 1000)
        assert _is_valid_squarespace_event(self._make_event(startDate=past_ms)) is False

    def test_rejects_missing_title(self):
        assert _is_valid_squarespace_event(self._make_event(title="")) is False

    def test_rejects_invalid_date(self):
        assert _is_valid_squarespace_event(self._make_event(startDate="not-a-number")) is False


# ------------------------------------------------------------------ #
# WixExtractorForComedian                                              #
# ------------------------------------------------------------------ #


class TestWixEventsDetection:
    def test_has_events_widget(self):
        assert WixExtractorForComedian.has_events_widget("...wix-one-events-server...") is True

    def test_no_events_widget(self):
        assert WixExtractorForComedian.has_events_widget("<html>no events here</html>") is False

    def test_discovers_comp_id_near_event_context(self):
        html = '..."compId":"comp-abc12345"...event..."compId":"comp-xyz99999"...'
        comp_id = WixExtractorForComedian.discover_comp_id(html)
        assert comp_id is not None
        assert comp_id.startswith("comp-")


class TestWixExtractShowsDetection:
    async def _noop(self):
        pass

    def test_returns_none_without_events_widget(self):
        """Wix sites without events widget should signal fallback to JSON-LD."""
        assert WixExtractorForComedian.has_events_widget("<html>regular page</html>") is False

    def test_returns_true_with_events_widget(self):
        assert WixExtractorForComedian.has_events_widget("...wix-one-events...") is True


# ------------------------------------------------------------------ #
# KomiExtractorForComedian                                             #
# ------------------------------------------------------------------ #


class TestKomiSlugExtraction:
    def test_extracts_slug(self):
        assert KomiExtractorForComedian.extract_artist_slug("https://chriskattan.komi.io/") == "chriskattan"

    def test_extracts_slug_no_trailing_slash(self):
        assert KomiExtractorForComedian.extract_artist_slug("https://devonwalker.komi.io") == "devonwalker"

    def test_returns_none_for_non_komi(self):
        assert KomiExtractorForComedian.extract_artist_slug("https://example.com") is None

    def test_returns_none_for_empty(self):
        assert KomiExtractorForComedian.extract_artist_slug("") is None


class TestBandsintownEventToShow:
    def _make_event(self, **overrides):
        future_dt = (datetime.now(tz=timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        event = {
            "id": "123",
            "datetime": future_dt,
            "url": "https://www.bandsintown.com/e/123",
            "description": "Live show",
            "venue": {
                "name": "The Comedy Club",
                "city": "New York",
                "region": "NY",
                "country": "United States",
                "postal_code": "10001",
            },
        }
        for k, v in overrides.items():
            if k.startswith("venue_"):
                event["venue"][k[6:]] = v
            else:
                event[k] = v
        return event

    def test_converts_valid_us_event(self):
        event = self._make_event()
        comedian = Comedian(name="Chris Kattan", uuid="uuid-1")
        club_handler = MagicMock()
        club = MagicMock()
        club.id = 99
        club.timezone = "America/New_York"
        club_handler.upsert_for_tour_date_venue.return_value = club

        show = _bandsintown_event_to_show(event, comedian, club_handler, "test")
        assert show is not None
        assert show.name == "Chris Kattan at The Comedy Club"
        assert show.club_id == 99
        assert comedian in show.lineup

    def test_skips_non_us_event(self):
        event = self._make_event(venue_country="Canada")
        comedian = Comedian(name="Chris Kattan", uuid="uuid-1")
        show = _bandsintown_event_to_show(event, comedian, MagicMock(), "test")
        assert show is None

    def test_skips_missing_venue_name(self):
        event = self._make_event(venue_name="")
        comedian = Comedian(name="Chris Kattan", uuid="uuid-1")
        show = _bandsintown_event_to_show(event, comedian, MagicMock(), "test")
        assert show is None

    def test_skips_non_us_state(self):
        event = self._make_event(venue_region="ON")
        comedian = Comedian(name="Chris Kattan", uuid="uuid-1")
        show = _bandsintown_event_to_show(event, comedian, MagicMock(), "test")
        assert show is None


# ------------------------------------------------------------------ #
# Integration: async extract_shows methods                             #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
class TestSquarespaceExtractShows:
    async def test_returns_none_for_non_events_page(self):
        html = '<script>Static.SQUARESPACE_CONTEXT = {"collection": {"type": 1, "id": "abc"}};</script>'
        result = await SquarespaceExtractorForComedian.extract_shows(
            scraping_url="https://test.squarespace.com/",
            html=html,
            comedian=Comedian(name="Test", uuid="u1"),
            club_handler=MagicMock(),
            fetch_json_fn=AsyncMock(),
            log_prefix="test",
        )
        assert result is None

    async def test_returns_empty_for_events_page_with_no_events(self):
        ctx = json.dumps({"collection": {"type": 10, "id": "abc123"}})
        html = f"<script>Static.SQUARESPACE_CONTEXT = {ctx};</script>"
        fetch_fn = AsyncMock(return_value=[])

        result = await SquarespaceExtractorForComedian.extract_shows(
            scraping_url="https://test.squarespace.com/shows",
            html=html,
            comedian=Comedian(name="Test", uuid="u1"),
            club_handler=MagicMock(),
            fetch_json_fn=fetch_fn,
            log_prefix="test",
        )
        assert result == []
        assert fetch_fn.call_count == 3  # 3 months


@pytest.mark.asyncio
class TestKomiExtractShows:
    async def test_returns_none_for_non_komi_url(self):
        result = await KomiExtractorForComedian.extract_shows(
            scraping_url="https://example.com",
            comedian=Comedian(name="Test", uuid="u1"),
            club_handler=MagicMock(),
            fetch_json_list_fn=AsyncMock(),
            log_prefix="test",
        )
        assert result is None

    async def test_returns_empty_for_no_events(self):
        result = await KomiExtractorForComedian.extract_shows(
            scraping_url="https://devonwalker.komi.io",
            comedian=Comedian(name="Devon Walker", uuid="u1"),
            club_handler=MagicMock(),
            fetch_json_list_fn=AsyncMock(return_value=[]),
            log_prefix="test",
        )
        assert result == []

    async def test_returns_shows_from_bandsintown(self):
        future_dt = (datetime.now(tz=timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        events = [{
            "id": "123",
            "datetime": future_dt,
            "url": "https://www.bandsintown.com/e/123",
            "description": "Live show",
            "venue": {
                "name": "Comedy Club",
                "city": "Austin",
                "region": "TX",
                "country": "United States",
                "postal_code": "78701",
            },
        }]
        club = MagicMock()
        club.id = 42
        club.timezone = "America/Chicago"
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = club

        result = await KomiExtractorForComedian.extract_shows(
            scraping_url="https://chriskattan.komi.io/",
            comedian=Comedian(name="Chris Kattan", uuid="u1"),
            club_handler=club_handler,
            fetch_json_list_fn=AsyncMock(return_value=events),
            log_prefix="test",
        )
        assert len(result) == 1
        assert result[0].name == "Chris Kattan at Comedy Club"
        assert result[0].club_id == 42
