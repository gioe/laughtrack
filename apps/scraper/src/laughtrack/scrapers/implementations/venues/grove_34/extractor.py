"""Grove34 data extraction utilities for the Webflow site."""

import json
from typing import List, Optional

from laughtrack.core.entities.event.grove34 import Grove34Event
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper
from laughtrack.foundation.infrastructure.logger.logger import Logger


class Grove34EventExtractor:
    """Utility class for extracting Grove34 event data from the Webflow site."""

    BASE_URL = "https://grove34.com"

    @staticmethod
    def extract_show_urls(html_content: str) -> List[str]:
        """
        Extract unique show detail page URLs from the Grove34 listing page HTML.

        Args:
            html_content: HTML of the main listing page (grove34.com/)

        Returns:
            Deduplicated list of absolute show detail URLs
        """
        try:
            elements = HtmlScraper.find_elements_by_selector(html_content, 'a[href]')
            seen = set()
            urls = []
            for el in elements:
                href = el.get("href", "")
                if "/shows/" not in href:
                    continue
                # Build absolute URL
                if href.startswith("http"):
                    full_url = href
                elif href.startswith("/"):
                    full_url = Grove34EventExtractor.BASE_URL + href
                else:
                    continue
                # Remove query params from show URLs (they're slugs, not paginated)
                if "?" in full_url:
                    full_url = full_url.split("?")[0]
                if full_url not in seen:
                    seen.add(full_url)
                    urls.append(full_url)
            return urls
        except Exception as e:
            Logger.error(f"Error extracting show URLs from listing page: {e}")
            return []

    @staticmethod
    def get_next_page_url(html_content: str, current_page_url: str) -> Optional[str]:
        """
        Find the pagination 'next page' URL in the listing page HTML.

        Args:
            html_content: HTML of the current listing page
            current_page_url: The URL of the current page (used to build absolute URL)

        Returns:
            Absolute URL of the next page, or None if no more pages
        """
        try:
            elements = HtmlScraper.find_elements_by_selector(html_content, 'a[href]')
            base = current_page_url.split("?")[0].rstrip("/")
            for el in elements:
                href = el.get("href", "")
                # Webflow CMS pagination uses a collection-specific query param
                if "1a7d9b18_page=" in href:
                    if href.startswith("?"):
                        return base + "/" + href
                    elif href.startswith("/"):
                        return Grove34EventExtractor.BASE_URL + href
                    else:
                        return href
            return None
        except Exception as e:
            Logger.error(f"Error finding next page URL: {e}")
            return None

    @staticmethod
    def extract_event(html_content: str, show_url: str) -> Optional[Grove34Event]:
        """
        Extract a Grove34Event from a show detail page using JSON-LD.

        Args:
            html_content: HTML of a show detail page
            show_url: The URL of this show page (stored on the event)

        Returns:
            Grove34Event or None if no valid Event JSON-LD found
        """
        try:
            script_contents = HtmlScraper.get_json_ld_script_contents(html_content)
            for content in script_contents:
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    continue

                if data.get("@type") != "Event":
                    continue

                name = data.get("name", "").replace("&amp;", "&").strip()
                start_date = data.get("startDate", "").strip()
                description = (data.get("description") or "").strip() or None

                if not name or not start_date:
                    Logger.warning(f"Grove34 show at {show_url} missing name or startDate in JSON-LD")
                    return None

                return Grove34Event(
                    title=name,
                    start_date=start_date,
                    show_page_url=show_url,
                    description=description,
                )

            Logger.warning(f"No Event JSON-LD found at {show_url}")
            return None
        except Exception as e:
            Logger.error(f"Error extracting Grove34 event from {show_url}: {e}")
            return None
