from datetime import datetime, timezone

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.core.entities.show.model import Show
from laughtrack.utilities.domain.show.classifier import classify_show_type


def _show(
    name: str,
    *,
    description: str = "",
    supplied_tags: list[str] | None = None,
) -> Show:
    return Show(
        name=name,
        club_id=42,
        date=datetime(2026, 4, 15, 20, 0, 0, tzinfo=timezone.utc),
        show_page_url="https://example.com/show",
        description=description,
        supplied_tags=supplied_tags or [],
    )


def _club(name: str, *, website: str = "https://example.com") -> Club:
    return Club(
        id=42,
        name=name,
        address="123 Main St",
        website=website,
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
    )


def test_classifies_open_mic_before_general_standup():
    show = _show("Stand-Up Open Mic Night")

    assert classify_show_type(show) == "open_mic"


def test_classifies_standup_from_title_and_description():
    show = _show("Friday Night Laughs", description="A stand-up comedy showcase.")

    assert classify_show_type(show) == "standup"


def test_classifies_improv_from_tags():
    show = _show("Mainstage", supplied_tags=["Comedy", "Improv"])

    assert classify_show_type(show) == "improv"


def test_classifies_theater_from_title():
    show = _show("Hamlet by William Shakespeare")

    assert classify_show_type(show) == "theater"


def test_classifies_music_from_platform_category():
    show = _show("Late Night Brass Band")

    assert classify_show_type(show, source_metadata={"category": "Concerts"}) == "music"


def test_classifies_high_confidence_standup_venue_default():
    show = _show("Jane Doe")

    assert classify_show_type(show, club=_club("Stand Up NY", website="https://standupny.com")) == "standup"


def test_ambiguous_show_remains_unknown():
    show = _show("Jane Doe")

    assert classify_show_type(show) == "unknown"


def test_show_handler_stamps_missing_show_type_before_persistence():
    show = _show("Monday Open Mic")
    handler = object.__new__(ShowHandler)

    handler._classify_missing_show_types([show])

    assert show.show_type == "open_mic"
