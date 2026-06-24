"""Opt-in LIVE verification of the multi-date TicketSpice extractor (TASK-3254).

Network test — skipped unless TICKETSPICE_LIVE=1. Fetches the real Comedy
Uncorked @ Retzlaff Vineyards form and asserts the extractor pulls more than one
upcoming dated show from the single form (the multi-date inventory). Not part of
the offline gate; used to confirm criterion #10629 end-to-end without a DB write.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TICKETSPICE_LIVE") != "1",
    reason="set TICKETSPICE_LIVE=1 to run the live network check",
)

_RETZLAFF_URL = "https://comedy.ticketspice.com/2026-comedy-uncorked-retzlaff-vineyards"


def test_live_retzlaff_form_yields_multiple_dates():
    import asyncio

    from laughtrack.core.entities.club.model import Club, ScrapingSource
    from laughtrack.scrapers.implementations.api.ticketspice.scraper import (
        TicketSpiceScraper,
    )

    club = Club(
        id=999999,
        name="Comedy Uncorked at Retzlaff Vineyards",
        address="1356 S Livermore Ave, Livermore, CA 94550, USA",
        website="https://comedyuncorked.com/livermore/",
        popularity=0,
        zip_code="94550",
        phone_number="",
        visible=True,
        timezone="America/Los_Angeles",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="ticketspice",
        source_url=_RETZLAFF_URL,
        metadata={},
    )
    club.scraping_sources = [club.active_scraping_source]

    scraper = TicketSpiceScraper(club)
    shows = asyncio.get_event_loop().run_until_complete(scraper.scrape_async())

    print(f"LIVE: {len(shows)} shows -> " + ", ".join(str(s.date) for s in shows))
    # Multi-date form: expect more than one upcoming dated show from ONE form.
    assert len(shows) >= 2
    assert all(s.club_id == 999999 for s in shows)
    assert all(s.show_page_url == _RETZLAFF_URL for s in shows)
    # Distinct dates (the whole point of multi-date parsing).
    assert len({s.date.date() for s in shows}) == len(shows)
