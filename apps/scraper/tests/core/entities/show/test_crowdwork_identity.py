"""Crowdwork URL/occurrence identity survives real persistence and refreshes."""

from datetime import datetime, timedelta, timezone

import pytest
import time_machine

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.philly_improv import PhillyImprovShow, crowdwork_performance_identity
from tests.core.entities.show.test_source_performance_identity import database, handler_for  # noqa: F401

START = datetime(2036, 10, 3, 2, 30, tzinfo=timezone.utc)


def club(enabled=True):
    source = ScrapingSource(
        id=45,
        club_id=182,
        platform="custom",
        scraper_key="crowdwork",
        source_url="https://crowdwork.com/api/v2/iotheater/shows",
        metadata={"source_performance_identity": enabled},
    )
    return Club(
        id=182,
        name="iO Theater",
        address="1501 N Kingsbury St",
        website="https://ioimprov.com",
        popularity=0,
        zip_code="60642",
        phone_number="",
        visible=True,
        timezone="America/Chicago",
        active_scraping_source=source,
        scraping_sources=[source],
    )


def performance(slug="people-being-funny", enabled=True, instant=START):
    return PhillyImprovShow(
        name="Comedy",
        date_str=instant.isoformat(),
        timezone="America/Chicago",
        url=f"https://www.crowdwork.com/e/{slug}",
        cost_formatted="$15",
    ).to_show(club(enabled), enhanced=False)


def test_conversion_preserves_simultaneous_distinct_urls_without_rooms():
    first, second = performance(), performance("paranormal-laughtivity")
    assert first.room == second.room == ""
    assert first.date == second.date
    assert first.to_unique_key() != second.to_unique_key()
    assert performance().to_unique_key() == first.to_unique_key()
    assert performance(enabled=False).source_performance_id is None
    assert performance(enabled="true").source_performance_id is None
    assert performance(instant=START.astimezone(timezone(timedelta(hours=-5)))).to_unique_key() == first.to_unique_key()


def test_identity_normalizes_timezone_and_preserves_url_and_occurrence():
    url = "https://www.crowdwork.com/e/people-being-funny"
    identity = crowdwork_performance_identity(url, START)
    assert identity == crowdwork_performance_identity(url, START.replace(tzinfo=None))
    assert identity == crowdwork_performance_identity(url, START.astimezone(timezone(timedelta(hours=-5))))
    assert identity != crowdwork_performance_identity(url, START + timedelta(days=1))
    assert identity != crowdwork_performance_identity(url + "?date=other", START)
    assert identity != crowdwork_performance_identity(url + "/", START)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://example.com/e/show",
        "https://www.crowdwork.com/",
        "https://www.crowdwork.com/e/",
        "https://www.crowdwork.com/e/show#other",
        "https://user@www.crowdwork.com/e/show",
        "https://www.crowdwork.com:bad/e/show",
        "https://www.crowdwork.com/e/show\n",
    ],
)
def test_invalid_enabled_identity_cannot_fall_back_to_legacy_slot(url):
    assert crowdwork_performance_identity(url, START) is None
    event = PhillyImprovShow("Comedy", START.isoformat(), "America/Chicago", url)
    with pytest.raises(ValueError, match="valid event URL"):
        event.to_show(club())


@pytest.mark.parametrize("batch_size", [1, 100])
@pytest.mark.parametrize("reverse", [False, True])
@time_machine.travel("2036-10-01T00:00:00Z", tick=False)
def test_database_preserves_both_orders_batches_duplicates_and_references(database, batch_size, reverse):
    handler = handler_for(database)
    # Exercise the actual cross-batch identity guard as well as SQL persistence.
    del handler._collapse_cross_batch_duplicates
    slugs = ["people-being-funny", "paranormal-laughtivity"]
    if reverse:
        slugs.reverse()
    shows = [performance(slug) for slug in slugs]
    result = handler.insert_shows(shows, batch_size=batch_size, scraper_key="crowdwork")
    assert result.errors == result.db_errors == result.validation_errors == 0
    assert result.inserts == 2
    ids = {slug: show.id for slug, show in zip(slugs, shows)}
    assert len(set(ids.values())) == 2
    with database.cursor() as cur:
        for index, show in enumerate(shows, 1):
            cur.execute("INSERT INTO saved_shows VALUES (%s,%s)", (str(index), show.id))
            cur.execute("INSERT INTO ticket_purchase_click_events VALUES (%s,%s)", (index, show.id))

    refreshed = [performance(slug) for slug in reversed(slugs)]
    result = handler.insert_shows(refreshed, batch_size=batch_size, scraper_key="crowdwork")
    assert result.updates == 2
    assert {slug: show.id for slug, show in zip(reversed(slugs), refreshed)} == ids
    duplicates = [performance(slugs[0]), performance(slugs[0])]
    result = handler.insert_shows(duplicates, batch_size=batch_size, scraper_key="crowdwork")
    assert result.inserts == 0
    assert result.errors == result.db_errors == 0
    with database.cursor() as cur:
        cur.execute("SELECT id,room FROM shows WHERE club_id=182 ORDER BY id")
        assert cur.fetchall() == [(ident, "") for ident in sorted(ids.values())]
        cur.execute("SELECT show_id,purchase_url FROM tickets ORDER BY show_id")
        assert cur.fetchall() == sorted((ids[slug], f"https://www.crowdwork.com/e/{slug}") for slug in slugs)
        cur.execute("SELECT show_id FROM saved_shows WHERE profile_id<>'legacy-user' ORDER BY show_id")
        assert cur.fetchall() == [(ident,) for ident in sorted(ids.values())]
        cur.execute("SELECT show_id FROM ticket_purchase_click_events ORDER BY show_id")
        assert cur.fetchall() == [(ident,) for ident in sorted(ids.values())]
