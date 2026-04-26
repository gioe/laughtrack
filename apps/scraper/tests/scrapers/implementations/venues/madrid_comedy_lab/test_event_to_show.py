"""
Unit tests for _infer_comedian_name() and MadridComedyLabEvent.to_show().
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.madrid_comedy_lab import (
    MadridComedyLabEvent,
    _infer_comedian_name,
)

TZ = "Europe/Madrid"


def _club(**overrides) -> Club:
    defaults = dict(
        id=200,
        name="Madrid Comedy Lab",
        address="Calle del Amor de Dios 13",
        website="https://madridcomedylab.com",
        popularity=0,
        zip_code="28014",
        phone_number="",
        visible=True,
        timezone=TZ,
    )
    scraping_url = overrides.pop(
        "scraping_url",
        "https://fienta.com/api/v1/public/events?organizer=24814",
    )
    defaults.update(overrides)
    club = Club(**defaults)
    club.active_scraping_source = ScrapingSource(
        id=1, club_id=club.id, platform="fienta",
        scraper_key="madrid_comedy_lab", source_url=scraping_url, external_id=None,
    )
    club.scraping_sources = [club.active_scraping_source]
    return club


def _event(**overrides) -> MadridComedyLabEvent:
    defaults = dict(
        event_id=177670,
        title="Carlos García Live",
        starts_at="2099-01-01 20:30:00",
        ends_at="2099-01-01 22:00:00",
        url="https://fienta.com/carlos-garcia-live-177670",
        sale_status="onSale",
        description="<p>Stand-up comedy</p>",
    )
    defaults.update(overrides)
    return MadridComedyLabEvent(**defaults)


# ---------------------------------------------------------------------------
# _infer_comedian_name — valid names
# ---------------------------------------------------------------------------


class TestInferComedianNameValid:
    def test_two_word_name(self):
        assert _infer_comedian_name("John Smith") == "John Smith"

    def test_three_word_name(self):
        assert _infer_comedian_name("Jean Claude Van") == "Jean Claude Van"

    def test_four_word_name(self):
        assert _infer_comedian_name("Mary Jane Watson Parker") == "Mary Jane Watson Parker"

    def test_accented_name(self):
        assert _infer_comedian_name("José García") == "José García"

    def test_accented_multi_word(self):
        assert _infer_comedian_name("María del Carmen López") == "María del Carmen López"

    def test_strips_live_suffix(self):
        assert _infer_comedian_name("Carlos García Live") == "Carlos García"

    def test_strips_LIVE_suffix(self):
        assert _infer_comedian_name("Carlos García LIVE") == "Carlos García"

    def test_strips_dash_live_suffix(self):
        assert _infer_comedian_name("Carlos García - Live") == "Carlos García"

    def test_strips_dash_LIVE_suffix(self):
        assert _infer_comedian_name("Carlos García - LIVE") == "Carlos García"

    def test_live_not_in_keywords(self):
        # "live" is NOT in _SHOW_TITLE_KEYWORDS, so a title with "Live" as a word passes
        assert _infer_comedian_name("Live Oak Johnson") == "Live Oak Johnson"


# ---------------------------------------------------------------------------
# _infer_comedian_name — returns None
# ---------------------------------------------------------------------------


class TestInferComedianNameRejectsNonNames:
    def test_single_word_returns_none(self):
        assert _infer_comedian_name("Showcase") is None

    def test_five_words_returns_none(self):
        assert _infer_comedian_name("One Two Three Four Five") is None

    def test_keyword_open_mic(self):
        assert _infer_comedian_name("Open Mic Night") is None

    def test_keyword_comedy_show(self):
        assert _infer_comedian_name("Comedy Show") is None

    def test_keyword_stand_up(self):
        assert _infer_comedian_name("Stand-Up Showcase") is None

    def test_keyword_improv_night(self):
        assert _infer_comedian_name("Improv Night") is None

    def test_keyword_english(self):
        assert _infer_comedian_name("English Comedy") is None

    def test_keyword_spanish(self):
        assert _infer_comedian_name("Spanish Comedy") is None

    def test_keyword_lab(self):
        assert _infer_comedian_name("Comedy Lab") is None

    def test_keyword_madrid(self):
        assert _infer_comedian_name("Madrid Showcase") is None

    def test_keyword_workshop(self):
        assert _infer_comedian_name("Comedy Workshop") is None

    def test_keyword_festival(self):
        assert _infer_comedian_name("Comedy Festival") is None

    def test_empty_string(self):
        assert _infer_comedian_name("") is None

    def test_whitespace_only(self):
        assert _infer_comedian_name("   ") is None

    def test_keyword_with_punctuation(self):
        # Words are stripped of trailing :,! before keyword check
        assert _infer_comedian_name("Open Mic!") is None

    def test_keyword_case_insensitive(self):
        assert _infer_comedian_name("OPEN MIC") is None

    def test_live_suffix_reveals_single_word(self):
        # "Comedian Live" → strip "Live" → "Comedian" (1 word) → None
        assert _infer_comedian_name("Comedian Live") is None


# ---------------------------------------------------------------------------
# to_show() — basic conversion
# ---------------------------------------------------------------------------


class TestToShowBasic:
    def test_returns_show_with_correct_name(self):
        show = _event().to_show(_club())
        assert show is not None
        assert show.name == "Carlos García Live"

    def test_correct_club_id(self):
        show = _event().to_show(_club())
        assert show.club_id == 200

    def test_correct_date_components(self):
        show = _event(starts_at="2099-01-01 20:30:00").to_show(_club())
        assert show is not None
        assert show.date.year == 2099
        assert show.date.month == 1
        assert show.date.day == 1
        assert show.date.hour == 20
        assert show.date.minute == 30

    def test_timezone_is_europe_madrid(self):
        show = _event(starts_at="2099-01-01 20:30:00").to_show(_club())
        assert show is not None
        assert str(show.date.tzinfo) == "Europe/Madrid"

    def test_default_timezone_when_club_has_none(self):
        club = _club(timezone=None)
        show = _event(starts_at="2099-01-01 20:30:00").to_show(club)
        assert show is not None
        assert str(show.date.tzinfo) == "Europe/Madrid"

    def test_show_page_url(self):
        show = _event().to_show(_club())
        assert show.show_page_url == "https://fienta.com/carlos-garcia-live-177670"

    def test_custom_url_override(self):
        show = _event().to_show(_club(), url="https://custom.com/tickets")
        assert show is not None
        assert show.tickets[0].purchase_url == "https://custom.com/tickets"


# ---------------------------------------------------------------------------
# to_show() — returns None on invalid input
# ---------------------------------------------------------------------------


class TestToShowReturnsNone:
    def test_empty_title(self):
        assert _event(title="").to_show(_club()) is None

    def test_unparseable_starts_at(self):
        assert _event(starts_at="not-a-date").to_show(_club()) is None

    def test_malformed_date_format(self):
        assert _event(starts_at="09/04/2026 20:30").to_show(_club()) is None


# ---------------------------------------------------------------------------
# to_show() — tickets
# ---------------------------------------------------------------------------


class TestToShowTickets:
    def test_ticket_from_url(self):
        show = _event(url="https://fienta.com/comedy-night").to_show(_club())
        assert len(show.tickets) == 1
        assert "fienta.com" in show.tickets[0].purchase_url

    def test_sold_out_status(self):
        show = _event(sale_status="soldOut").to_show(_club())
        assert show.tickets[0].sold_out is True

    def test_on_sale_status(self):
        show = _event(sale_status="onSale").to_show(_club())
        assert show.tickets[0].sold_out is False


# ---------------------------------------------------------------------------
# to_show() — lineup inference
# ---------------------------------------------------------------------------


class TestToShowLineup:
    def test_lineup_from_comedian_name_title(self):
        show = _event(title="Carlos García Live").to_show(_club())
        assert len(show.lineup) == 1
        assert show.lineup[0].name == "Carlos García"

    def test_no_lineup_for_show_title(self):
        show = _event(title="Open Mic Night").to_show(_club())
        assert show.lineup == []

    def test_no_lineup_for_single_word_title(self):
        show = _event(title="Showcase").to_show(_club())
        assert show.lineup == []
