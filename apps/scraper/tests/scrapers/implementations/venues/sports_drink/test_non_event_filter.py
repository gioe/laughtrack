"""Keep the captured purchase-confirmation card out of the show pipeline."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from laughtrack.scrapers.implementations.venues.sports_drink.extractor import SportsDrinkExtractor
from laughtrack.utilities.domain.show.validator import ShowValidator
from .test_pipeline_smoke import (
    LISTING_URL, _card_html, _club, _detail_page_html, _listing_page,
    _scraper_with_detail_pages,
)

CONFIRMATION_URL = "https://app.opendate.io/e/thank-you-for-your-purchase-december-31-2099-579525"
CAPTURE = Path(__file__).resolve().parents[5] / "docs/audits/2026-10-05-sports-drink-cleanup/listing-cards.html"


def test_captured_listing_preserves_every_real_card():
    html = CAPTURE.read_text()
    cards = BeautifulSoup(html, "html.parser").select("div.confirm-card")
    assert len(cards) == 119
    expected = [
        (card.select_one("a.stretched-link").get_text(strip=True),
         card.select_one("a.stretched-link")["href"])
        for card in cards
        if "579525" not in card.select_one("a.stretched-link")["href"]
    ]
    events = SportsDrinkExtractor.extract_events(html)
    assert len(events) == len(expected) == 118
    assert [(event.title, event.event_url) for event in events] == expected


@pytest.mark.parametrize("title,url", [
    ("Thank You For Your Purchase!!!", CONFIRMATION_URL + "?default_theme=true"),
    ("  THANK YOU  for your purchase!!!  ", CONFIRMATION_URL + "?default_theme=false"),
])
def test_confirmation_excluded_independently_of_date(title, url):
    assert SportsDrinkExtractor.extract_events(_card_html(title=title, event_url=url)) == []


@pytest.mark.parametrize("title,url", [
    ("Thank You For Your Purchase!!!", "https://app.opendate.io/e/real-comedy-123"),
    ("Thank You For Your Purchase: A Comedy Show", CONFIRMATION_URL),
    ("Thank You For Your Purchase!!!", CONFIRMATION_URL.replace("app.opendate.io", "example.com")),
])
def test_similar_legitimate_cards_are_preserved(title, url):
    events = SportsDrinkExtractor.extract_events(_card_html(title=title, event_url=url))
    assert [(event.title, event.event_url) for event in events] == [(title, url)]


def test_unrelated_far_future_show_still_reaches_date_validation():
    events = SportsDrinkExtractor.extract_events(_card_html(date_str="December 31, 2099"))
    assert len(events) == 1
    show = events[0].to_show(_club())
    assert show is not None
    valid, errors = ShowValidator.validate_shows([show])
    assert valid == []
    assert any("18 months in the future" in error for error in errors)


@pytest.mark.asyncio
async def test_confirmation_never_reaches_detail_fetch_or_transformation(monkeypatch):
    url = "https://app.opendate.io/e/real-comedy-123"
    listing = _listing_page([
        _card_html(title="Thank You For Your Purchase!!!", event_url=CONFIRMATION_URL,
                   date_str="December 31, 2099"),
        _card_html(title="Real Comedy", event_url=url),
    ])
    fetched = []
    scraper = _scraper_with_detail_pages(monkeypatch, listing, {url: _detail_page_html()}, fetched)
    data = await scraper.get_data(LISTING_URL)
    assert data is not None
    assert fetched == [url]
    shows = scraper.transformation_pipeline.transform(data)
    assert [(show.name, show.show_page_url) for show in shows] == [("Real Comedy", url)]
