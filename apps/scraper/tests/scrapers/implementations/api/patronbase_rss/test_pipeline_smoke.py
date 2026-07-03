"""Pipeline smoke tests for the generic PatronBase RSS scraper."""

from datetime import datetime, timedelta, timezone

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.implementations.api.patronbase_rss.extractor import (
    PatronBaseRssExtractor,
)
from laughtrack.scrapers.implementations.api.patronbase_rss.scraper import (
    PatronBaseRssScraper,
)


FEED_URL = "https://us.patronbase.com/_ComedyCabaret/Productions/RSS"


def _rss_item(
    title: str = "Best of Philly Region! Sat. 7/11 8:00PM",
    link: str = "https://us.patronbase.com/_ComedyCabaret/Productions/503/Performances",
    date_text: str = "11 Jul, 2026",
) -> str:
    return f"""
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description><![CDATA[
        BEST of Philly Region night!<br />
        Venue: Comedy Cabaret Comedy Club<br />
        Date: {date_text}
      ]]></description>
      <guid>{link}</guid>
    </item>
    """


def _rss(*items: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <title>What's on at Comedy Cabaret</title>
        {''.join(items)}
      </channel>
    </rss>
    """


def _future_date_text(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%d %b, %Y")


def _past_date_text(days: int = 7) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d %b, %Y")


def _club() -> Club:
    club = Club(
        id=99,
        name="Comedy Cabaret Comedy Club",
        address="625 N Main St, Doylestown, PA 18901, USA",
        website="https://comedycabaret.com/bucks-county-doylestown/",
        popularity=0,
        zip_code="18901",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )
    source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="patronbase_rss",
        source_url=FEED_URL,
        external_id=None,
        metadata={},
    )
    club.active_scraping_source = source
    club.scraping_sources = [source]
    return club


def test_extract_events_parses_rss_items_and_cleans_date_suffix():
    events = PatronBaseRssExtractor.extract_events(_rss(_rss_item(date_text=_future_date_text())))

    assert len(events) == 1
    event = events[0]
    assert event.title == "Best of Philly Region!"
    assert event.start.hour == 20
    assert event.start.minute == 0
    assert event.show_page_url == "https://us.patronbase.com/_ComedyCabaret/Productions/503/Performances"
    assert "BEST of Philly Region night!" in event.description
    assert event.venue == "Comedy Cabaret Comedy Club"


def test_extract_events_skips_past_or_malformed_items():
    events = PatronBaseRssExtractor.extract_events(
        _rss(
            _rss_item(title="Past Show Sat. 7/11 8:00PM", date_text=_past_date_text()),
            _rss_item(title="Missing Time", date_text=_future_date_text()),
            _rss_item(title="Future Show Sat. 7/11 8:00PM", date_text=_future_date_text()),
        )
    )

    assert [event.title for event in events] == ["Future Show"]


def test_event_to_show_uses_detail_link_for_ticket_url():
    event = PatronBaseRssExtractor.extract_events(_rss(_rss_item(date_text=_future_date_text())))[0]

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Best of Philly Region!"
    assert show.show_page_url == event.show_page_url
    assert show.tickets[0].purchase_url == event.show_page_url
    assert show.room == "Comedy Cabaret Comedy Club"


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_feed_url():
    scraper = PatronBaseRssScraper(_club())

    assert await scraper.collect_scraping_targets() == [FEED_URL]


@pytest.mark.asyncio
async def test_get_data_fetches_feed_and_returns_page_data(monkeypatch):
    scraper = PatronBaseRssScraper(_club())

    async def fake_fetch_html(url: str, **kwargs):
        assert url == FEED_URL
        return _rss(_rss_item(date_text=_future_date_text()))

    monkeypatch.setattr(scraper, "fetch_html", fake_fetch_html)

    result = await scraper.get_data(FEED_URL)

    assert isinstance(result, EventListContainer)
    assert len(result.event_list) == 1
    assert result.event_list[0].title == "Best of Philly Region!"
