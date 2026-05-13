"""Tests for platform-specific comedian website extractors."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.scrapers.implementations.api.comedian_websites.platform_extractors import (
    KomiExtractorForComedian,
    SeatedTourListExtractorForComedian,
    ShubertSingleEventExtractorForComedian,
    ShopifyTourListExtractorForComedian,
    SquarespaceExtractorForComedian,
    StructuredTourListExtractorForComedian,
    TicketNetworkTourListExtractorForComedian,
    TextTourListExtractorForComedian,
    VividSeatsExtractorForComedian,
    WixExtractorForComedian,
    _bandsintown_event_to_venue,
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

    def test_vividseats_domain(self):
        assert detect_website_platform("https://www.vividseats.com/nurse-john-tickets") == "vividseats"

    def test_shubert_domain(self):
        assert detect_website_platform("https://www.shubert.com/events/detail/example") == "shubert"

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

    def test_generated_tour_listing_marker(self):
        html = '<div class="date" data-date="2027-05-15T21:30:00"><span class="venue-name">Club</span></div>'
        assert detect_website_platform_from_html(html) == "tour_listing"

    def test_shopify_tour_marker(self):
        html = '<script src="//example/cdn/shopifycloud/x.js"></script><div class="tour-date-article-container"></div>'
        assert detect_website_platform_from_html(html) == "shopify_tour"

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
# Static tour-page extractors                                          #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
class TestStructuredTourListExtractor:
    async def test_upserts_generated_tour_listing_rows(self):
        html = """
        <div class="date" data-country="USA" data-date="2027-05-15T21:30:00">
          <span class="venue-name">Chicago Improv Comedy Club</span>
          <span class="venue-location">Schaumburg, IL</span>
          <a href="https://tickets.example/show">Buy Tickets</a>
        </div>
        """
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await StructuredTourListExtractorForComedian.extract_venues(
            scraping_url="https://dlhughleytour.com/",
            html=html,
            comedian=Comedian(name="D.L. Hughley", uuid="comic-1"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 1
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "Chicago Improv Comedy Club"
        assert venue["address"] == "Schaumburg, IL"
        assert venue["discovery_metadata"]["platform_hints"] == ["tour_listing"]
        assert venue["discovery_metadata"]["comedian_refs"] == [{"uuid": "comic-1", "name": "D.L. Hughley"}]


@pytest.mark.asyncio
class TestShopifyTourListExtractor:
    async def test_upserts_steveo_tour_rows(self):
        html = """
        <div class="tour-date-article-container">
          <a href="https://ticket.example/steve-o">
            <div class="td-but1"><h3><span>MAY<br>21</span></h3></div>
            <div class="td-but2">
              <h3><span>Corpus Christi, TX (1ST SHOW)</span></h3>
              <h4><strong><span>Mesquite Street</span></strong></h4>
            </div>
          </a>
        </div>
        """
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await ShopifyTourListExtractorForComedian.extract_venues(
            scraping_url="https://www.steveo.com/pages/tour-dates",
            html=html,
            comedian=Comedian(name="Steve-O", uuid="comic-1"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 1
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "Mesquite Street"
        assert venue["address"] == "Corpus Christi, TX"
        assert venue["discovery_metadata"]["platform_hints"] == ["shopify_tour"]

    async def test_upserts_andrew_schulz_tour_rows(self):
        html = """
        <div class="fa_date_item">
          <h3>June 5-6, 2027</h3>
          <div class="location__container">Virginia Beach, VA</div>
          <div class="venue__container">Funny Bone Comedy Club</div>
          <a href="https://tickets.example/andrew">Get Tickets</a>
        </div>
        """
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await ShopifyTourListExtractorForComedian.extract_venues(
            scraping_url="https://theandrewschulz.com/pages/upcoming-shows",
            html=html,
            comedian=Comedian(name="Andrew Schulz", uuid="comic-2"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 1
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "Funny Bone Comedy Club"
        assert venue["address"] == "Virginia Beach, VA"


@pytest.mark.asyncio
class TestShubertSingleEventExtractor:
    async def test_skips_past_shubert_event(self):
        html = '<span class="m-date__singleDate">Saturday, June 28, 2025</span>'
        club_handler = MagicMock()

        count = await ShubertSingleEventExtractorForComedian.extract_venues(
            scraping_url="https://www.shubert.com/events/detail/marlon-wayans-wild-child-tour",
            html=html,
            comedian=Comedian(name="Marlon Wayans", uuid="comic-3"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 0
        club_handler.upsert_for_tour_date_venue.assert_not_called()


@pytest.mark.asyncio
class TestVividSeatsExtractor:
    async def test_upserts_rendered_vividseats_rows(self):
        html = """
        <a href="/nurse-john/show">
          Thu Jul 16 7:30pm Nurse John (21+ Event) Oxnard Levity Live • Oxnard, CA From $94
        </a>
        """
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await VividSeatsExtractorForComedian.extract_venues(
            scraping_url="https://www.vividseats.com/nurse-john-tickets--theater-comedy/performer/182803",
            html=html,
            comedian=Comedian(name="Nurse John", uuid="comic-4"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 1
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "Oxnard Levity Live"
        assert venue["address"] == "Oxnard, CA"
        assert venue["discovery_metadata"]["platform_hints"] == ["vividseats"]


@pytest.mark.asyncio
class TestSeatedTourListExtractor:
    async def test_upserts_seated_event_rows(self):
        html = """
        <div class="seated-event-row">
          <a href="https://tickets.example/gary"></a>
          <div class="seated-event-date-cell">May 14, 2027</div>
          <div class="seated-event-venue-name">The Moore Theatre</div>
          <div class="seated-event-venue-location">Seattle, WA</div>
        </div>
        """
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await SeatedTourListExtractorForComedian.extract_venues(
            scraping_url="https://www.garyowen.live/tour-1",
            html=html,
            comedian=Comedian(name="Gary Owen", uuid="comic-5"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 1
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "The Moore Theatre"
        assert venue["address"] == "Seattle, WA"
        assert venue["discovery_metadata"]["platform_hints"] == ["seated"]

    async def test_upserts_seated_api_events_from_embedded_artist_id(self):
        html = """
        <div id="seated-55fdf2c0" data-artist-id="artist-123" data-css-version="2"></div>
        <script src="https://widget.seated.com/app.js"></script>
        """
        response = {
            "included": [
                {
                    "id": "event-123",
                    "type": "tour-events",
                    "attributes": {
                        "starts-at": "2027-05-14T03:00:00Z",
                        "venue-name": "The Moore Theatre",
                        "formatted-address": "Seattle, WA",
                    },
                }
            ]
        }
        fetch_json = AsyncMock(return_value=response)
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await SeatedTourListExtractorForComedian.extract_venues(
            scraping_url="https://www.garyowen.live/tour-1",
            html=html,
            comedian=Comedian(name="Gary Owen", uuid="comic-5"),
            club_handler=club_handler,
            log_prefix="test",
            fetch_json_fn=fetch_json,
        )

        assert count == 1
        assert fetch_json.call_args.args[0] == "https://cdn.seated.com/api/tour/artist-123?include=tour-events"
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "The Moore Theatre"
        assert venue["address"] == "Seattle, WA"
        assert venue["discovery_metadata"]["event_urls"] == ["https://link.seated.com/event-123"]


@pytest.mark.asyncio
class TestTicketNetworkTourListExtractor:
    async def test_upserts_ticketnetwork_widget_events(self):
        html = """
        <script>
        params.specialFilters = "&performerFilter=text/name eq 'Vinny Guadagnino'&includeFacets=true";
        csctnCall(params);
        </script>
        """
        response = {
            "results": [
                {
                    "date": {"datetimeOffset": "2027-05-22T19:00:00-04:00"},
                    "country": {"alphaCode": "US"},
                    "stateProvince": {"text": {"abbr": "OH"}},
                    "city": {"text": {"name": "Cleveland"}},
                    "venue": {"text": {"name": "Hilarities 4th Street Theatre At Pickwick & Frolic"}},
                    "_links": [{"rel": "self", "href": "https://www.tn-apis.com/catalog/v2/events/7917947"}],
                }
            ]
        }
        fetch_json = AsyncMock(return_value=response)
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await TicketNetworkTourListExtractorForComedian.extract_venues(
            scraping_url="https://www.vinnyguadagninotour.com/",
            html=html,
            comedian=Comedian(name="Vinny Guadagnino", uuid="comic-6"),
            club_handler=club_handler,
            fetch_json_fn=fetch_json,
            log_prefix="test",
        )

        assert count == 1
        assert "performerFilter=text%2Fname+eq+%27Vinny+Guadagnino%27" in fetch_json.call_args.args[0]
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "Hilarities 4th Street Theatre At Pickwick & Frolic"
        assert venue["address"] == "Cleveland, OH"
        assert venue["discovery_metadata"]["platform_hints"] == ["ticketnetwork"]


@pytest.mark.asyncio
class TestTextTourListExtractor:
    async def test_upserts_location_first_squarespace_text_rows(self):
        html = """
        <section>
          <div>May 15 '27 San Antonio, TX Aztec Theatre Bobby Lee TICKETS</div>
        </section>
        """
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await TextTourListExtractorForComedian.extract_venues(
            scraping_url="https://www.bobbylee.live/tour",
            html=html,
            comedian=Comedian(name="Bobby Lee", uuid="comic-7"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 1
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "Aztec Theatre"
        assert venue["address"] == "San Antonio, TX"
        assert venue["discovery_metadata"]["platform_hints"] == ["text_tour_list"]

    async def test_upserts_venue_first_ticket_table_rows(self):
        html = """
        <div class="ticket-table">June 12-14, 2027 Mic Drop San Diego, CA TOKENS</div>
        """
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await TextTourListExtractorForComedian.extract_venues(
            scraping_url="https://deraydavis.com/shows/",
            html=html,
            comedian=Comedian(name="DeRay Davis", uuid="comic-8"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 1
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "Mic Drop"
        assert venue["address"] == "San Diego, CA"

    async def test_upserts_venue_first_pete_holmes_rows(self):
        html = """
        <div class="group">JUN 10 Wheeler Opera House Aspen, CO calendar_today Buy Tickets</div>
        """
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await TextTourListExtractorForComedian.extract_venues(
            scraping_url="https://peteholmes.com/",
            html=html,
            comedian=Comedian(name="Pete Holmes", uuid="comic-9"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 1
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "Wheeler Opera House"
        assert venue["address"] == "Aspen, CO"

    async def test_upserts_ed_bassmaster_location_first_rows(self):
        html = """
        <div>MAY 8 Tyler, TX The New Rose City Comedy Buy Tickets</div>
        """
        club_handler = MagicMock()
        club_handler.upsert_for_tour_date_venue.return_value = MagicMock(id=1)

        count = await TextTourListExtractorForComedian.extract_venues(
            scraping_url="https://www.edbassmaster.com/tour",
            html=html,
            comedian=Comedian(name="Ed Bassmaster", uuid="comic-10"),
            club_handler=club_handler,
            log_prefix="test",
        )

        assert count == 1
        venue = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue["name"] == "The New Rose City Comedy"
        assert venue["address"] == "Tyler, TX"


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


class TestBandsintownEventToVenue:
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

    def test_upserts_valid_us_venue(self):
        event = self._make_event()
        club_handler = MagicMock()
        club = MagicMock()
        club.id = 99
        club_handler.upsert_for_tour_date_venue.return_value = club

        result = _bandsintown_event_to_venue(event, club_handler, "test")
        assert result is True
        club_handler.upsert_for_tour_date_venue.assert_called_once()
        venue_dict = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue_dict["discovery_metadata"] == {
            "source": "comedian_websites",
            "event_urls": ["https://www.bandsintown.com/e/123"],
            "platform_hints": ["bandsintown"],
        }

    def test_skips_non_us_event(self):
        event = self._make_event(venue_country="Canada")
        result = _bandsintown_event_to_venue(event, MagicMock(), "test")
        assert result is False

    def test_skips_missing_venue_name(self):
        event = self._make_event(venue_name="")
        result = _bandsintown_event_to_venue(event, MagicMock(), "test")
        assert result is False

    def test_skips_non_us_state(self):
        event = self._make_event(venue_region="ON")
        result = _bandsintown_event_to_venue(event, MagicMock(), "test")
        assert result is False


# ------------------------------------------------------------------ #
# Integration: async extract_shows methods                             #
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
class TestSquarespaceExtractEventCount:
    async def test_returns_none_for_non_events_page(self):
        html = '<script>Static.SQUARESPACE_CONTEXT = {"collection": {"type": 1, "id": "abc"}};</script>'
        result = await SquarespaceExtractorForComedian.extract_event_count(
            scraping_url="https://test.squarespace.com/",
            html=html,
            comedian=Comedian(name="Test", uuid="u1"),
            fetch_json_fn=AsyncMock(),
            log_prefix="test",
        )
        assert result is None

    async def test_returns_zero_for_events_page_with_no_events(self):
        ctx = json.dumps({"collection": {"type": 10, "id": "abc123"}})
        html = f"<script>Static.SQUARESPACE_CONTEXT = {ctx};</script>"
        fetch_fn = AsyncMock(return_value=[])

        result = await SquarespaceExtractorForComedian.extract_event_count(
            scraping_url="https://test.squarespace.com/shows",
            html=html,
            comedian=Comedian(name="Test", uuid="u1"),
            fetch_json_fn=fetch_fn,
            log_prefix="test",
        )
        assert result == 0
        assert fetch_fn.call_count == 3  # 3 months


@pytest.mark.asyncio
class TestKomiExtractVenues:
    async def test_returns_zero_for_non_komi_url(self):
        result = await KomiExtractorForComedian.extract_venues(
            scraping_url="https://example.com",
            comedian=Comedian(name="Test", uuid="u1"),
            club_handler=MagicMock(),
            fetch_json_list_fn=AsyncMock(),
            log_prefix="test",
        )
        assert result == 0

    async def test_returns_zero_for_no_events(self):
        result = await KomiExtractorForComedian.extract_venues(
            scraping_url="https://devonwalker.komi.io",
            comedian=Comedian(name="Devon Walker", uuid="u1"),
            club_handler=MagicMock(),
            fetch_json_list_fn=AsyncMock(return_value=[]),
            log_prefix="test",
        )
        assert result == 0

    async def test_upserts_venues_from_bandsintown(self):
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

        result = await KomiExtractorForComedian.extract_venues(
            scraping_url="https://chriskattan.komi.io/",
            comedian=Comedian(name="Chris Kattan", uuid="u1"),
            club_handler=club_handler,
            fetch_json_list_fn=AsyncMock(return_value=events),
            log_prefix="test",
        )
        assert result == 1
        club_handler.upsert_for_tour_date_venue.assert_called_once()
        venue_dict = club_handler.upsert_for_tour_date_venue.call_args.args[0]
        assert venue_dict["discovery_metadata"] == {
            "source": "comedian_websites",
            "comedian_refs": [{"uuid": "u1", "name": "Chris Kattan"}],
            "sample_urls": ["https://chriskattan.komi.io/"],
            "event_urls": ["https://www.bandsintown.com/e/123"],
            "platform_hints": ["komi", "bandsintown"],
        }
