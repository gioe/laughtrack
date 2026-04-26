"""Unit tests for Club.to_tuple()."""

from laughtrack.core.entities.club.model import Club, ScrapingSource


_LEGACY_KWARGS = {"scraping_url", "scraper", "eventbrite_id", "seatengine_id",
                  "ticketmaster_id", "ovationtix_client_id", "wix_comp_id",
                  "squadup_user_id"}


def _attach_source(club: Club, *, scraping_url=None, scraper=None,
                    eventbrite_id=None, seatengine_id=None,
                    ticketmaster_id=None, ovationtix_client_id=None,
                    wix_comp_id=None, squadup_user_id=None) -> None:
    if not any((scraping_url, scraper, eventbrite_id, seatengine_id,
                ticketmaster_id, ovationtix_client_id, wix_comp_id,
                squadup_user_id)):
        return
    if eventbrite_id is not None:
        platform, external_id = "eventbrite", eventbrite_id
    elif seatengine_id is not None:
        platform = "seatengine_v3" if scraper == "seatengine_v3" else "seatengine"
        external_id = seatengine_id
    elif ticketmaster_id is not None:
        platform, external_id = "ticketmaster", ticketmaster_id
    elif ovationtix_client_id is not None:
        platform, external_id = "ovationtix", ovationtix_client_id
    elif wix_comp_id is not None:
        platform, external_id = "wix_events", wix_comp_id
    elif squadup_user_id is not None:
        platform, external_id = "squadup", squadup_user_id
    elif scraper:
        platform, external_id = scraper, None
    else:
        platform, external_id = "custom", None
    club.active_scraping_source = ScrapingSource(
        id=1, club_id=club.id, platform=platform,
        scraper_key=scraper or "", source_url=scraping_url, external_id=external_id,
    )
    club.scraping_sources = [club.active_scraping_source]


def _make_club(**kwargs) -> Club:
    defaults = dict(
        id=1,
        name="Test Club",
        address="123 Main St",
        website="https://testclub.com",
        popularity=5,
        zip_code="10001",
        phone_number="555-1234",
        visible=True,
    )
    legacy_defaults = {"scraping_url": "https://testclub.com/events"}
    legacy = {k: kwargs.pop(k, legacy_defaults.get(k))
              for k in _LEGACY_KWARGS if k in kwargs or k in legacy_defaults}
    defaults.update(kwargs)
    club = Club(**defaults)
    _attach_source(club, **legacy)
    return club


class TestClubScrapingDomain:
    def test_returns_hostname_without_protocol(self):
        club = _make_club(scraping_url="https://testclub.com/events")
        assert club.scraping_domain == "testclub.com"

    def test_does_not_mutate_scraping_url(self):
        club = _make_club(scraping_url="https://testclub.com/events")
        _ = club.scraping_domain
        assert club.scraping_url == "https://testclub.com/events"

    def test_idempotent_on_repeated_access(self):
        club = _make_club(scraping_url="https://testclub.com/events")
        assert club.scraping_domain == "testclub.com"
        assert club.scraping_domain == "testclub.com"
        assert club.scraping_url == "https://testclub.com/events"

    def test_works_without_protocol(self):
        club = _make_club(scraping_url="testclub.com/events")
        assert club.scraping_domain == "testclub.com"


class TestClubToTuple:
    def test_includes_city_and_state_when_set(self):
        club = _make_club(city="New York", state="NY")
        t = club.to_tuple()
        assert club.city in t
        assert club.state in t

    def test_city_and_state_none_when_not_set(self):
        club = _make_club()
        t = club.to_tuple()
        # city and state are the last two elements; both default to None
        assert t[-2] is None
        assert t[-1] is None

    def test_tuple_ends_with_city_state(self):
        club = _make_club(city="Chicago", state="IL")
        t = club.to_tuple()
        assert t[-2] == "Chicago"
        assert t[-1] == "IL"


class TestClubFromDbRow:
    def _base_row(self, **kwargs):
        row = {
            "id": 1,
            "name": "Test Club",
            "address": "123 Main St",
            "website": "https://testclub.com",
            "scraping_url": "https://testclub.com/events",
            "popularity": 5,
            "zip_code": "10001",
            "phone_number": "555-1234",
            "visible": True,
        }
        row.update(kwargs)
        return row

    def test_defaults_status_to_active_when_key_absent(self):
        row = self._base_row()
        assert "status" not in row
        club = Club.from_db_row(row)
        assert club.status == "active"

    def test_reads_explicit_status_value(self):
        row = self._base_row(status="closed")
        club = Club.from_db_row(row)
        assert club.status == "closed"
