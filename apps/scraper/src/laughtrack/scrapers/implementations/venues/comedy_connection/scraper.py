"""Comedy Connection's native Next.js calendar with Tixologi checkout links."""

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from laughtrack.core.clients.rsc.extractor import extract_push_payloads, find_json_array
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .data import ComedyConnectionEvent, ComedyConnectionPageData
from .extractor import ComedyConnectionExtractor


class ComedyConnectionTransformer(DataTransformer[ComedyConnectionEvent]):
    pass


class ComedyConnectionScraper(BaseScraper):
    key = "comedy_connection"

    def __init__(self, club, **kwargs):
        super().__init__(club, **kwargs)
        self.transformation_pipeline.register_transformer(ComedyConnectionTransformer(club))

    async def collect_scraping_targets(self):
        url = self.club.scraping_url
        html = await self.fetch_html(url)
        if not html:
            raise ValueError("Comedy Connection calendar returned no content")
        targets = []
        for link in BeautifulSoup(html, "html.parser").find_all("a", href=True):
            target = urljoin(url, link["href"])
            parsed = urlparse(target)
            if (
                parsed.scheme == "https"
                and parsed.netloc == urlparse(url).netloc
                and re.fullmatch(r"/events/[a-z0-9-]+/?", parsed.path)
            ):
                targets.append(target.split("?")[0].split("#")[0].rstrip("/"))
        if not targets:
            raise ValueError("Comedy Connection calendar has no event links")
        # The listing currently renders every native event, not just one page.
        # Detect a future pagination/rendering change before accepting a subset.
        events = find_json_array("".join(extract_push_payloads(html)), "events")
        if not isinstance(events, list) or not events:
            raise ValueError("Comedy Connection calendar event payload is missing")
        slugs = {event.get("slug") for event in events if isinstance(event, dict)}
        if not slugs or None in slugs or any(not isinstance(event, dict) for event in events):
            raise ValueError("Comedy Connection calendar event payload is invalid")
        if slugs != {urlparse(target).path.split("/")[-1] for target in targets}:
            raise ValueError("Comedy Connection calendar links do not cover its full event payload")
        return list(dict.fromkeys(targets))

    async def get_data(self, url):
        html = await self.fetch_html(url)
        if not html:
            raise ValueError(f"Comedy Connection detail returned no content: {url}")
        return ComedyConnectionPageData(ComedyConnectionExtractor.extract_events(html, url))
