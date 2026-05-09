from pathlib import Path

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.crowdwork.utils import (
    extract_lineup_names,
    extract_performances,
)


FIXTURE_DIR = Path(__file__).parent / "cassettes"


def _club() -> Club:
    return Club(
        id=1,
        name="iO Theater",
        address="",
        zip_code="60642",
        website="https://www.ioimprov.com",
        timezone="America/Chicago",
        popularity=0,
        phone_number="",
        visible=True,
    )


def _show(description_body: str) -> dict:
    return {
        "name": "Devil's Daughter",
        "url": "https://www.crowdwork.com/e/devils-daughter",
        "timezone": "Central Time (US & Canada)",
        "dates": ["2026-05-15T21:00:00.000-05:00"],
        "cost": {"formatted": "$15.00"},
        "description": {"body": description_body},
        "badges": {"spots": None},
    }


def test_extract_lineup_names_parses_cast_section_from_event_page_cassette():
    html = (FIXTURE_DIR / "devils_daughter_event_page.html").read_text()

    assert extract_lineup_names(html) == [
        "Lisa Burton",
        "Gretchen Eng",
        "Max Ganet",
        "Adonis Holmes",
        "Garrett Kelly",
        "TJ King",
        "Harrison Lott",
        "Scott Piebenga",
        "Brad Pike",
        "May Regan",
        "Annie Sullivan",
        "Mary Tilden",
    ]


def test_extract_lineup_names_parses_ft_title_and_with_description():
    html = (
        "<div>Join us for a night of long-form improv with The Late 90s, "
        "Little Heroes, and two opening guest teams!</div>"
    )

    assert extract_lineup_names(html, title="The Sunday Show ft. The Late 90s") == [
        "The Late 90s",
        "Little Heroes",
    ]


def test_extract_lineup_names_parses_parenthetical_featuring_description():
    html = (
        "<div>Dad Jokes (featuring Michael Johnson, Michael Smith, Justin "
        "Edmonds, Taylor Grote, and Rachel Ware) has been voted as one of the "
        "best improv shows at The Backline.</div>"
    )

    assert extract_lineup_names(html) == [
        "Michael Johnson",
        "Michael Smith",
        "Justin Edmonds",
        "Taylor Grote",
        "Rachel Ware",
    ]


def test_extract_lineup_names_ignores_generic_lowercase_with_phrase():
    html = (
        "<div>It's your favorite comedy open mic, at the same place, on the same "
        "day at an earlier time, and with a new updated format!</div>"
    )

    assert extract_lineup_names(html) == []


def test_extract_lineup_names_uses_named_act_title_as_fallback():
    assert extract_lineup_names("<div>Veteran Omaha comic.</div>", title="Bill Queen and Friends") == [
        "Bill Queen"
    ]


def test_extract_lineup_names_does_not_use_generic_open_mic_title_as_fallback():
    assert extract_lineup_names("<div>Anyone can sign up.</div>", title="Open Mic") == []


def test_extract_performances_carries_crowdwork_lineup_into_show():
    html = (FIXTURE_DIR / "devils_daughter_event_page.html").read_text()

    performance = extract_performances(_show(html))[0]
    show = performance.to_show(_club())

    assert [comedian.name for comedian in show.lineup] == [
        "Lisa Burton",
        "Gretchen Eng",
        "Max Ganet",
        "Adonis Holmes",
        "Garrett Kelly",
        "TJ King",
        "Harrison Lott",
        "Scott Piebenga",
        "Brad Pike",
        "May Regan",
        "Annie Sullivan",
        "Mary Tilden",
    ]
