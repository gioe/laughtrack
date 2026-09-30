"""Replay captured cancelled pages through the real scraper, with venue writes mocked."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from curl_cffi.requests import AsyncSession
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.foundation.infrastructure.http.client import HttpClient
from laughtrack.scrapers.implementations.next_stop_comedy.scraper import NextStopComedyScraper

HERE = Path(__file__).resolve().parent


async def replay(cache):
    targets = json.loads((HERE / "repair-plan.json").read_text())
    ids = {r["id"] for r in targets}
    controls = [r for r in json.loads((HERE / "db-before.json").read_text())["rows"] if r["id"] not in ids][:3]
    pages = {}
    for r in targets:
        key = hashlib.sha256(r["show_page_url"].encode()).hexdigest()
        pages[r["show_page_url"]] = (cache / (key + ".html")).read_text()
    async with AsyncSession(impersonate="chrome") as session:
        for r in controls:
            pages[r["show_page_url"]] = await HttpClient.fetch_html(session, r["show_page_url"])
    proxy = Club(id=Club.SYNTHETIC_PROXY_PLACEHOLDER_ID, name="Next Stop Comedy", address="",
                 website="https://www.nextstopcomedy.com", popularity=0, zip_code="", phone_number="",
                 visible=False, is_synthetic=True)
    proxy.active_scraping_source = ScrapingSource(id=1, platform="custom", scraper_key="next_stop_comedy",
                                                source_url="https://www.nextstopcomedy.com/events")
    proxy.scraping_sources = [proxy.active_scraping_source]
    scraper = NextStopComedyScraper(proxy)
    listing = "".join(f'<a href="{url}">Show</a>' for url in pages)
    control_by_url = {r["show_page_url"]: r for r in controls}

    async def fetch(url):
        return listing if url == proxy.scraping_url else pages[url]

    async def venue(loop, event):
        # Any canceled page reaching venue persistence fails this assertion.
        assert event.event_url in control_by_url, event.event_url
        r = control_by_url[event.event_url]
        return Club(id=r["club_id"], name=event.venue_name, address=event.venue_address,
                    website="", popularity=0, zip_code=event.venue_zip, phone_number="", visible=True,
                    timezone=event.venue_timezone or "America/New_York")

    with patch.object(scraper, "_fetch_page", side_effect=fetch), \
         patch.object(scraper, "_collect_api_events", new=AsyncMock(return_value=[])), \
         patch.object(scraper, "_upsert_venue", side_effect=venue) as upsert:
        shows = await scraper.scrape_async()
    assert {s.show_page_url for s in shows} == set(control_by_url)
    assert upsert.call_count == len(controls)
    return {"cancelled_pages_replayed": len(targets), "cancelled_shows_emitted": 0,
            "scheduled_controls_emitted": len(shows), "venue_writes": "mocked", "production_writes": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(replay(args.cache))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
