"""Pipeline smoke tests for the Kenosha Comedy Club scraper.

The live source is a Happenings Magazine WordPress category where each club show
is a plain post. Titles carry show dates, so date inference is tested with an
injected ``today`` to keep the suite stable.
"""

from datetime import date

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.kenosha_comedy_club import KenoshaComedyClubEvent
from laughtrack.scrapers.implementations.venues.kenosha_comedy_club.extractor import (
    KenoshaComedyClubExtractor,
)

SOURCE_URL = (
    "https://happeningsmag.com/wp-json/wp/v2/posts?"
    "categories=506&per_page=20&_fields=id,date,modified,link,title,excerpt,categories"
)


def _post(title: str, link: str = "https://happeningsmag.com/example/") -> dict:
    return {
        "id": 1,
        "link": link,
        "title": {"rendered": title},
        "excerpt": {"rendered": "<p>Stand-up comedy bio.</p>"},
        "categories": [506, 97],
    }


def _club() -> Club:
    club = Club(
        id=9991,
        name="Kenosha Comedy Club",
        address="5125 6th Ave",
        website="https://www.kenoshacomedyclub.com/",
        popularity=0,
        zip_code="53140",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        city="Kenosha",
        state="WI",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="kenosha_comedy_club",
        source_url=SOURCE_URL,
        external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def test_extracts_one_event_for_each_date_in_title():
    events = KenoshaComedyClubExtractor.extract_events(
        [_post("Emo Philips w/Tim Cavanagh: June 19 &amp; 20 at 8PM")],
        today=date(2026, 6, 1),
    )

    assert [e.name for e in events] == [
        "Emo Philips w/Tim Cavanagh",
        "Emo Philips w/Tim Cavanagh",
    ]
    assert [e.start_date for e in events] == [
        "2026-06-19 20:00:00",
        "2026-06-20 20:00:00",
    ]
    assert events[0].description == "Stand-up comedy bio."


def test_extracts_titles_with_minutes():
    events = KenoshaComedyClubExtractor.extract_events(
        [_post("Mentalist Jym Elders: June 26 &amp; 27 at 7:00PM")],
        today=date(2026, 6, 1),
    )

    assert [e.start_date for e in events] == [
        "2026-06-26 19:00:00",
        "2026-06-27 19:00:00",
    ]


def test_past_month_day_rolls_forward_one_year():
    events = KenoshaComedyClubExtractor.extract_events(
        [_post("Craig Shoemaker: January 9 & 10 at 8PM")],
        today=date(2026, 12, 20),
    )

    assert [e.start_date for e in events] == [
        "2027-01-09 20:00:00",
        "2027-01-10 20:00:00",
    ]


def test_skips_posts_without_machine_readable_time():
    events = KenoshaComedyClubExtractor.extract_events(
        [_post("Jamie Lissow: June 26 &amp; 27")],
        today=date(2026, 6, 1),
    )

    assert events == []


def test_to_show_builds_central_time_show_with_ticket():
    event = KenoshaComedyClubEvent(
        name="Taylor Mason",
        start_date="2026-07-10 20:00:00",
        url="https://happeningsmag.com/taylor-mason-july-10-11-at-8pm/",
        description="Comedy Central special.",
    )

    show = event.to_show(_club())

    assert show is not None
    assert show.name == "Taylor Mason"
    assert show.date.year == 2026 and show.date.month == 7 and show.date.day == 10
    assert show.date.hour == 20
    assert show.show_page_url == "https://happeningsmag.com/taylor-mason-july-10-11-at-8pm"
    assert len(show.tickets) == 1
    assert show.tickets[0].purchase_url == "https://happeningsmag.com/taylor-mason-july-10-11-at-8pm/"
