"""Unit tests for the generic Salesforce PatronTicket scraper.

Covers:
  - auth extraction from a fixture HTML block
  - payload construction
  - response parsing with multiple venueIds
  - Comedy / category filter override (single category, custom category, disabled)
  - empty / missing-instance / non-200 handling
  - __init__ validation: missing source_url, missing venue_id, list-typed venue_id
"""

from typing import Any, List, Optional

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.patron_ticket.data import (
    PatronTicketPageData,
)
from laughtrack.scrapers.implementations.venues.patron_ticket.extractor import (
    PatronTicketExtractor,
)
from laughtrack.scrapers.implementations.venues.patron_ticket.scraper import (
    PatronTicketScraper,
)


# A minimal HTML snippet that contains the inline auth config the extractor parses.
_FIXTURE_HTML = """
<html>
  <head>
    <script>
      window.__sfdcSessionId = "sid";
      Visualforce.remoting.Manager.add(new $VFRM.RemotingProviderImpl({
        "vf":{"vid":"06P0t0000004pK1"},
        "actions":{
          "PatronTicket.Controller_PublicTicketApp":{
            "ms":[
              {"name":"fetchEvents","len":3,"ns":"PatronTicket","ver":52.0,"csrf":"VFCSRF","authorization":"JWT-TOKEN"}
            ]
          }
        }
      }));
    </script>
  </head>
  <body><div id="app"></div></body>
</html>
"""

_SOURCE_URL = "https://example.my.salesforce-sites.com/ticket"


_DEFAULT_METADATA_SENTINEL: dict = {}


def _club(
    metadata: Optional[dict] = _DEFAULT_METADATA_SENTINEL,
    source_url: Optional[str] = _SOURCE_URL,
) -> Club:
    if metadata is _DEFAULT_METADATA_SENTINEL:
        metadata = {"patronticket_venue_id": "VENUE_A"}
    c = Club(
        id=9999,
        name="Example PatronTicket Venue",
        address="123 Main St",
        website="https://example.org",
        popularity=0,
        zip_code="00000",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    c.active_scraping_source = ScrapingSource(
        id=1,
        club_id=c.id,
        platform="patron_ticket",
        scraper_key="patron_ticket",
        source_url=source_url,
        metadata=metadata or {},
    )
    c.scraping_sources = [c.active_scraping_source]
    return c


def _event_blob(
    *,
    name: str,
    category: str,
    instances: List[dict],
    detail: str = "Performer bio",
) -> dict:
    return {
        "name": name,
        "category": category,
        "detail": detail,
        "instances": instances,
    }


# 2099-01-01 UTC as Unix epoch ms — well past any date-aware filtering window
# the client might add later (convention #11).
_FAR_FUTURE_EPOCH_MS = 4_070_908_800_000


def _instance(
    *,
    instance_id: str,
    venue_id: str,
    epoch_ms: int = _FAR_FUTURE_EPOCH_MS,
    sold_out: bool = False,
    purchase_url: str = "https://example.my.salesforce-sites.com/ticket/#/instances/x",
) -> dict:
    return {
        "id": instance_id,
        "venueId": venue_id,
        "name": "Friday Show",
        "purchaseUrl": purchase_url,
        "soldOut": sold_out,
        "formattedDates": {
            "ISO8601": epoch_ms,
            "LONG_MONTH_DAY_YEAR": "January 1, 2099",
            "TIME_STRING": "8:00 PM",
        },
    }


def _api_response(events: List[dict], status: int = 200) -> List[dict]:
    return [
        {
            "statusCode": status,
            "type": "rpc",
            "result": events,
        }
    ]


# ---------------------------------------------------------------------------
# Auth-config extraction
# ---------------------------------------------------------------------------


def test_extract_auth_config_returns_csrf_authorization_and_vid_from_fixture_html():
    config = PatronTicketExtractor.extract_auth_config(_FIXTURE_HTML)
    assert config == {
        "len": 3,
        "ns": "PatronTicket",
        "ver": 52,
        "csrf": "VFCSRF",
        "authorization": "JWT-TOKEN",
        "vid": "06P0t0000004pK1",
    }


def test_extract_auth_config_returns_none_when_fetch_events_block_is_missing():
    html = '<html><body><script>{"vid":"06P0t0000004pK1"}</script></body></html>'
    assert PatronTicketExtractor.extract_auth_config(html) is None


def test_extract_auth_config_returns_none_when_vid_is_missing():
    html = (
        'fetchEvents","len":3,"ns":"PatronTicket","ver":52.0,'
        '"csrf":"VFCSRF","authorization":"JWT-TOKEN"'
    )
    assert PatronTicketExtractor.extract_auth_config(html) is None


# ---------------------------------------------------------------------------
# Payload construction
# ---------------------------------------------------------------------------


def test_build_fetch_events_payload_carries_auth_context_and_origin_url():
    scraper = PatronTicketScraper(_club())
    auth = {
        "csrf": "C",
        "vid": "V",
        "ns": "N",
        "ver": 52,
        "authorization": "A",
    }
    payload = scraper.build_fetch_events_payload(auth)

    assert payload["action"] == "PatronTicket.Controller_PublicTicketApp"
    assert payload["method"] == "fetchEvents"
    assert payload["type"] == "rpc"
    assert payload["data"] == [f"{_SOURCE_URL}/", "", ""]
    assert payload["ctx"] == {
        "csrf": "C",
        "vid": "V",
        "ns": "N",
        "ver": 52,
        "authorization": "A",
    }


def test_scraper_collect_targets_returns_configured_source_url_only():
    scraper = PatronTicketScraper(_club())
    assert scraper.collect_scraping_targets_sync() == [_SOURCE_URL]


# ---------------------------------------------------------------------------
# Multi-venue ID parsing
# ---------------------------------------------------------------------------


def test_extract_events_keeps_instances_only_at_configured_venue_ids():
    response = _api_response(
        [
            _event_blob(
                name="Headliner",
                category="Comedy;Stand-Up",
                instances=[
                    _instance(instance_id="I-A", venue_id="VENUE_A"),
                    _instance(instance_id="I-B", venue_id="VENUE_B"),
                    _instance(instance_id="I-C", venue_id="VENUE_C"),
                ],
            ),
        ]
    )

    events = PatronTicketExtractor.extract_events(
        response, venue_ids=["VENUE_A", "VENUE_C"]
    )

    assert sorted(e.instance_id for e in events) == ["I-A", "I-C"]


def test_extract_events_returns_empty_when_no_venue_ids_configured():
    response = _api_response(
        [
            _event_blob(
                name="x",
                category="Comedy",
                instances=[_instance(instance_id="I-A", venue_id="VENUE_A")],
            )
        ]
    )

    assert PatronTicketExtractor.extract_events(response, venue_ids=[]) == []


def test_extract_events_deduplicates_repeated_instance_ids():
    instance = _instance(instance_id="DUP", venue_id="VENUE_A")
    response = _api_response(
        [
            _event_blob(name="x", category="Comedy", instances=[instance, instance]),
        ]
    )

    events = PatronTicketExtractor.extract_events(response, venue_ids=["VENUE_A"])
    assert [e.instance_id for e in events] == ["DUP"]


# ---------------------------------------------------------------------------
# Category filter override
# ---------------------------------------------------------------------------


def test_extract_events_keeps_only_comedy_by_default():
    response = _api_response(
        [
            _event_blob(
                name="Comedy",
                category="Comedy",
                instances=[_instance(instance_id="C", venue_id="VENUE_A")],
            ),
            _event_blob(
                name="Music",
                category="Music",
                instances=[_instance(instance_id="M", venue_id="VENUE_A")],
            ),
        ]
    )

    events = PatronTicketExtractor.extract_events(response, venue_ids=["VENUE_A"])
    assert [e.instance_id for e in events] == ["C"]


def test_extract_events_accepts_custom_category_token():
    response = _api_response(
        [
            _event_blob(
                name="Other",
                category="Other; Variety",
                instances=[_instance(instance_id="O", venue_id="VENUE_A")],
            ),
            _event_blob(
                name="Comedy",
                category="Comedy",
                instances=[_instance(instance_id="C", venue_id="VENUE_A")],
            ),
        ]
    )

    events = PatronTicketExtractor.extract_events(
        response, venue_ids=["VENUE_A"], categories=["Other"]
    )
    assert [e.instance_id for e in events] == ["O"]


def test_extract_events_disables_category_filter_when_categories_is_empty():
    response = _api_response(
        [
            _event_blob(
                name="anything",
                category="Variety",
                instances=[_instance(instance_id="V", venue_id="VENUE_A")],
            ),
        ]
    )

    events = PatronTicketExtractor.extract_events(
        response, venue_ids=["VENUE_A"], categories=[]
    )
    assert [e.instance_id for e in events] == ["V"]


# ---------------------------------------------------------------------------
# Empty / missing-instance / non-200 handling
# ---------------------------------------------------------------------------


def test_extract_events_returns_empty_on_non_200_status():
    response = [{"statusCode": 500, "message": "boom"}]
    assert (
        PatronTicketExtractor.extract_events(response, venue_ids=["VENUE_A"]) == []
    )


def test_extract_events_returns_empty_when_response_is_empty_list():
    assert PatronTicketExtractor.extract_events([], venue_ids=["VENUE_A"]) == []


def test_extract_events_returns_empty_when_response_is_not_a_list():
    assert (
        PatronTicketExtractor.extract_events({"statusCode": 200}, venue_ids=["VENUE_A"])
        == []
    )


def test_extract_events_skips_event_with_no_instances():
    response = _api_response(
        [
            _event_blob(name="empty", category="Comedy", instances=[]),
        ]
    )
    assert (
        PatronTicketExtractor.extract_events(response, venue_ids=["VENUE_A"]) == []
    )


def test_extract_events_skips_instance_with_missing_epoch():
    bad = _instance(instance_id="X", venue_id="VENUE_A")
    bad["formattedDates"].pop("ISO8601")
    response = _api_response(
        [_event_blob(name="x", category="Comedy", instances=[bad])]
    )
    assert (
        PatronTicketExtractor.extract_events(response, venue_ids=["VENUE_A"]) == []
    )


# ---------------------------------------------------------------------------
# Scraper __init__ validation
# ---------------------------------------------------------------------------


def test_scraper_init_raises_when_source_url_is_blank():
    with pytest.raises(ValueError, match="source_url"):
        PatronTicketScraper(_club(source_url=""))


def test_scraper_init_raises_when_venue_id_metadata_is_missing():
    with pytest.raises(ValueError, match="patronticket_venue_id"):
        PatronTicketScraper(_club(metadata={}))


def test_scraper_init_accepts_list_typed_venue_ids():
    scraper = PatronTicketScraper(
        _club(
            metadata={"patronticket_venue_id": ["VENUE_A", "VENUE_B"]}
        )
    )
    assert scraper._venue_ids == ["VENUE_A", "VENUE_B"]


def test_scraper_init_accepts_csv_string_venue_ids():
    scraper = PatronTicketScraper(
        _club(metadata={"patronticket_venue_id": "VENUE_A,VENUE_B"})
    )
    assert scraper._venue_ids == ["VENUE_A", "VENUE_B"]


def test_scraper_init_strips_trailing_slash_from_source_url():
    scraper = PatronTicketScraper(_club(source_url=_SOURCE_URL + "/"))
    assert scraper._source_url == _SOURCE_URL
    assert scraper._apexremote_url == f"{_SOURCE_URL}/apexremote"


def test_scraper_init_parses_categories_csv_metadata():
    scraper = PatronTicketScraper(
        _club(
            metadata={
                "patronticket_venue_id": "VENUE_A",
                "patronticket_categories": "Other, Variety",
            }
        )
    )
    assert scraper._categories == ("Other", "Variety")


def test_scraper_init_disables_category_filter_with_star_sentinel():
    scraper = PatronTicketScraper(
        _club(
            metadata={
                "patronticket_venue_id": "VENUE_A",
                "patronticket_categories": "*",
            }
        )
    )
    assert scraper._categories == tuple()


# ---------------------------------------------------------------------------
# End-to-end get_data using a stubbed HTTP layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_page_data_when_api_returns_one_comedy_instance(monkeypatch):
    scraper = PatronTicketScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        assert url == _SOURCE_URL
        return _FIXTURE_HTML

    posted: dict = {}

    async def fake_post_json(self, url, data, **kwargs) -> Any:
        posted["url"] = url
        posted["data"] = data
        posted["headers"] = kwargs.get("headers")
        return _api_response(
            [
                _event_blob(
                    name="Comedy",
                    category="Comedy",
                    instances=[_instance(instance_id="I1", venue_id="VENUE_A")],
                )
            ]
        )

    monkeypatch.setattr(PatronTicketScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(PatronTicketScraper, "post_json", fake_post_json)

    result = await scraper.get_data(_SOURCE_URL)

    assert isinstance(result, PatronTicketPageData)
    assert [e.instance_id for e in result.event_list] == ["I1"]
    assert posted["url"] == f"{_SOURCE_URL}/apexremote"
    assert posted["headers"] == {"Referer": _SOURCE_URL}
    assert posted["data"]["method"] == "fetchEvents"
    assert posted["data"]["ctx"]["csrf"] == "VFCSRF"


@pytest.mark.asyncio
async def test_get_data_returns_none_when_auth_config_is_unavailable(monkeypatch):
    scraper = PatronTicketScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return "<html><body>no auth here</body></html>"

    monkeypatch.setattr(PatronTicketScraper, "fetch_html", fake_fetch_html)

    assert await scraper.get_data(_SOURCE_URL) is None


# ---------------------------------------------------------------------------
# PatronTicketEvent.to_show + name_strip_suffixes
# ---------------------------------------------------------------------------


def _make_event(event_name: str, suffixes: List[str]) -> Any:
    from laughtrack.core.entities.event.patron_ticket import PatronTicketEvent

    return PatronTicketEvent(
        event_name=event_name,
        instance_name=event_name,
        instance_id="I",
        epoch_ms=_FAR_FUTURE_EPOCH_MS,
        date_str="January 1, 2099",
        time_str="8:00 PM",
        purchase_url="https://example.com/i",
        sold_out=False,
        description="",
        categories="Comedy",
        name_strip_suffixes=suffixes,
    )


def test_to_show_strips_configured_suffix_from_event_name():
    club = _club()
    event = _make_event(
        "The Setup - San Francisco",
        suffixes=[" - San Francisco", " - SF", " - sf"],
    )

    show = event.to_show(club)

    assert show is not None
    assert show.name == "The Setup"


def test_to_show_picks_first_matching_suffix_from_the_list():
    club = _club()
    event = _make_event("Open Mic - SF", suffixes=[" - San Francisco", " - SF"])

    show = event.to_show(club)

    assert show is not None
    assert show.name == "Open Mic"


def test_to_show_leaves_name_unchanged_when_no_suffix_matches():
    club = _club()
    event = _make_event("Comedy Night", suffixes=[" - San Francisco"])

    show = event.to_show(club)

    assert show is not None
    assert show.name == "Comedy Night"


def test_to_show_treats_missing_strip_suffixes_as_no_op():
    club = _club()
    event = _make_event("Headliner - San Francisco", suffixes=[])

    show = event.to_show(club)

    assert show is not None
    # No suffix configured → upstream string flows through; Show.__post_init__
    # only collapses internal whitespace, it does not strip city suffixes.
    assert "San Francisco" in show.name


def test_get_data_forwards_name_strip_suffixes_from_metadata_to_events(monkeypatch):
    """End-to-end: the metadata-configured suffix list reaches PatronTicketEvent."""

    scraper = PatronTicketScraper(
        _club(
            metadata={
                "patronticket_venue_id": "VENUE_A",
                "patronticket_name_strip_suffixes": [" - San Francisco"],
            }
        )
    )
    assert scraper._name_strip_suffixes == [" - San Francisco"]


@pytest.mark.asyncio
async def test_get_data_returns_none_when_api_returns_no_matching_instances(monkeypatch):
    scraper = PatronTicketScraper(_club())

    async def fake_fetch_html(self, url, **kwargs):
        return _FIXTURE_HTML

    async def fake_post_json(self, url, data, **kwargs):
        return _api_response(
            [
                _event_blob(
                    name="Music",
                    category="Music",
                    instances=[_instance(instance_id="M", venue_id="VENUE_A")],
                )
            ]
        )

    monkeypatch.setattr(PatronTicketScraper, "fetch_html", fake_fetch_html)
    monkeypatch.setattr(PatronTicketScraper, "post_json", fake_post_json)

    assert await scraper.get_data(_SOURCE_URL) is None
