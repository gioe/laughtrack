"""Complete public calendar with corroborated per-performance detail data."""

from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import StirCrazyEvent, StirCrazyPageData
from .extractor import TZ, calendar_items, extract_details


class StirCrazyTransformer(DataTransformer[StirCrazyEvent]):
    pass


class StirCrazyScraper(BaseScraper):
    key = "stir_crazy"

    def __init__(self, club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(StirCrazyTransformer(club))

    async def collect_scraping_targets(self):
        return [self.club.scraping_url]

    async def get_data(self, url):
        origin = f"https://{urlparse(url).netloc}"
        now = datetime.now(TZ)
        headers = {"Referer": f"{origin}/calendar?month={now.month}&year={now.year}",
                   "X-Requested-With": "XMLHttpRequest"}
        endpoint = origin + "/Services/Services.asmx/"
        maximum = await self.post_json(endpoint + "GetMaxMonths", {}, headers=headers)
        maximum = maximum.get("d") if isinstance(maximum, dict) else None
        if type(maximum) is not int or not 0 <= maximum <= 24:
            raise ValueError("Stir Crazy calendar horizon is invalid")
        groups = defaultdict(dict)
        for offset in range(maximum + 1):
            year, zero_month = divmod(now.year * 12 + now.month - 1 + offset, 12)
            month = zero_month + 1
            headers["Referer"] = f"{origin}/calendar?month={month}&year={year}"
            payload = await self.post_json(endpoint + "GetUpcomingShowsByMonth", {"Month": month, "Year": year}, headers=headers)
            for item in calendar_items(payload, year, month, origin):
                if item["start"] >= now:
                    key = item["start"]
                    prior = groups[item["url"]].get(key)
                    if prior and prior != item:
                        raise ValueError("Stir Crazy calendar has conflicting duplicate performances")
                    groups[item["url"]][key] = item
        events = []
        for detail_url, items in groups.items():
            html = await self.fetch_html(detail_url)
            if not html:
                raise ValueError(f"Stir Crazy mandatory detail returned no content: {detail_url}")
            events.extend(extract_details(html, detail_url, list(items.values()),
                performer_overrides=(self.club.source_metadata or {}).get("performer_overrides")))
        return StirCrazyPageData(events)
