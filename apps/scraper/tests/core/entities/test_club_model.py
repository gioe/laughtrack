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
        platform, typed_id = "eventbrite", {"eventbrite_id": eventbrite_id}
    elif seatengine_id is not None:
        platform = "seatengine_v3" if scraper == "seatengine_v3" else "seatengine"
        typed_id = {"seatengine_v3_id": seatengine_id} if platform == "seatengine_v3" else {"seatengine_id": int(seatengine_id)}
    elif ticketmaster_id is not None:
        platform, typed_id = "ticketmaster", {"ticketmaster_id": ticketmaster_id}
    elif ovationtix_client_id is not None:
        platform, typed_id = "ovationtix", {"ovationtix_id": ovationtix_client_id}
    elif wix_comp_id is not None:
        platform, typed_id = "wix_events", {"wix_event_id": wix_comp_id}
    elif squadup_user_id is not None:
        platform, typed_id = "squadup", {"squadup_id": squadup_user_id}
    elif scraper:
        platform, typed_id = scraper, {}
    else:
        platform, typed_id = "custom", {}
    club.active_scraping_source = ScrapingSource(
        id=1, club_id=club.id, platform=platform,
        scraper_key=scraper or "", source_url=scraping_url, **typed_id,
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

    def test_reads_typed_scraping_source_ids(self):
        row = self._base_row(
            scraping_sources=[
                {
                    "id": 10,
                    "club_id": 1,
                    "platform": "seatengine",
                    "scraper_key": "seatengine",
                    "source_url": "https://example.com",
                    "seatengine_id": 502,
                    "eventbrite_id": None,
                    "ticketmaster_id": None,
                    "wix_event_id": None,
                    "ovationtix_id": None,
                    "squadup_id": None,
                    "seatengine_v3_id": None,
                }
            ],
        )

        club = Club.from_db_row(row)

        assert club.seatengine_id == "502"
        assert club.scraping_sources[0].seatengine_id == 502

    def test_reads_chain_default_resolved_sources_for_multiple_clubs(self):
        rows = [
            self._base_row(
                id=1,
                name="Zanies Nashville",
                chain_id=42,
                scraping_sources=[
                    {
                        "id": 10,
                        "club_id": 1,
                        "platform": "custom",
                        "scraper_key": "zanies",
                        "source_url": "https://nashville.zanies.com",
                        "priority": 0,
                        "enabled": True,
                        "metadata": {"default_calendar": "main"},
                        "chain_scraping_default_id": 7,
                        "chain_id": 42,
                    }
                ],
            ),
            self._base_row(
                id=2,
                name="Zanies Chicago",
                chain_id=42,
                scraping_sources=[
                    {
                        "id": 11,
                        "club_id": 2,
                        "platform": "custom",
                        "scraper_key": "zanies",
                        "source_url": "https://chicago.zanies.com",
                        "priority": 0,
                        "enabled": True,
                        "metadata": {"default_calendar": "main"},
                        "chain_scraping_default_id": 7,
                        "chain_id": 42,
                    }
                ],
            ),
        ]

        clubs = [Club.from_db_row(row) for row in rows]

        assert [club.scraper for club in clubs] == ["zanies", "zanies"]
        assert [club.scraping_url for club in clubs] == [
            "https://nashville.zanies.com",
            "https://chicago.zanies.com",
        ]
        assert {club.scraping_sources[0].chain_scraping_default_id for club in clubs} == {7}

    def test_club_source_override_keeps_explicit_scraper_key(self):
        row = self._base_row(
            chain_id=42,
            scraping_sources=[
                {
                    "id": 12,
                    "club_id": 1,
                    "platform": "custom",
                    "scraper_key": "zanies_custom_override",
                    "source_url": "https://override.example.com",
                    "priority": 0,
                    "enabled": True,
                    "metadata": {"default_calendar": "main", "calendar": "override"},
                    "chain_scraping_default_id": 7,
                    "chain_id": 42,
                }
            ],
        )

        club = Club.from_db_row(row)

        assert club.scraper == "zanies_custom_override"
        assert club.scraping_url == "https://override.example.com"
        assert club.source_metadata["calendar"] == "override"

    def test_platform_properties_read_their_typed_columns(self):
        cases = [
            ("eventbrite", {"eventbrite_id": "295549203"}, "eventbrite_id", "295549203"),
            ("ticketmaster", {"ticketmaster_id": "KovZ917ARvk"}, "ticketmaster_id", "KovZ917ARvk"),
            ("seatengine_v3", {"seatengine_v3_id": "364f13ff-86b9-479f-9720-bd191e285ac3"}, "seatengine_id", "364f13ff-86b9-479f-9720-bd191e285ac3"),
            ("ovationtix", {"ovationtix_id": "client-123"}, "ovationtix_client_id", "client-123"),
            ("wix_events", {"wix_event_id": "comp-test"}, "wix_comp_id", "comp-test"),
            ("squadup", {"squadup_id": "99999"}, "squadup_user_id", "99999"),
        ]

        for platform, typed_id, property_name, expected in cases:
            source = ScrapingSource.from_dict(
                {
                    "platform": platform,
                    "scraper_key": platform,
                    "source_url": "https://example.com",
                    **typed_id,
                }
            )
            club = _make_club(scraping_url=None)
            club.active_scraping_source = source
            club.scraping_sources = [source]

            assert getattr(club, property_name) == expected
