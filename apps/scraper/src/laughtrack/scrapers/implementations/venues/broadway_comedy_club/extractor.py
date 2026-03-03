"""Broadway Comedy Club data extraction utilities."""

import re
from typing import List

from laughtrack.core.entities.event.broadway import BroadwayEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper

class BroadwayEventExtractor:
    """Utility class for extracting Broadway Comedy Club event data from HTML content."""

    @staticmethod
    def extract_events(html_content: str) -> List[BroadwayEvent]:
        """
        Extract Broadway Comedy Club events from JavaScript arrays.

        Args:
            html_content: HTML content containing JavaScript
            extract_events_only: For compatibility with JSON-LD pattern (ignored)

        Returns:
            List of BroadwayEvent objects extracted from Broadway's JavaScript arrays
        """
        # Map Tessera card IDs to their anchor hrefs that wrap the title h3
        # We expect the listing cards to look like: <div class="tessera-show-card" id="18330"> ... <a ...><h3 class="card-title my-1"> ...
        id_to_href = HtmlScraper.extract_card_id_to_href_by_child(
            html=html_content,
            card_class="tessera-show-card",
            child_tag="h3",
            child_class="card-title my-1",
        )

        # Also map card IDs to room text inside the card footer
        # E.g., <div class="tessera-venue fw-bold"> Main Room</div>
        id_to_room = HtmlScraper.extract_card_id_to_child_text_by_class(
            html=html_content,
            card_class="tessera-show-card",
            child_tag="div",
            child_class="tessera-venue",
        )

        # Extract raw Broadway event data from JavaScript eventObjects.push({...}); blocks
        array_name = "eventObjects"
        pattern = rf"{re.escape(array_name)}\.push\((.+?)\);"
        matches = re.findall(pattern, html_content, re.DOTALL)

        broadway_events = []
        for match in matches:
            try:
                # Clean and parse JSON in one step
                cleaned_json = JSONUtils.comprehensive_clean(match.strip())
                event_data = JSONUtils.safe_json_loads(cleaned_json, logger_context={})

                # Convert to BroadwayEvent if valid dict (use from_dict for normalization + logging)
                if isinstance(event_data, dict):
                    # Attach show_page_url from matching card href when possible
                    ev_id = str(event_data.get("id", ""))
                    if ev_id and ev_id in id_to_href:
                        event_data["show_page_url"] = id_to_href[ev_id]
                        # If externalLink is empty, prefer the card URL for downstream consumers
                        if not event_data.get("externalLink"):
                            event_data["externalLink"] = id_to_href[ev_id]

                    # Attach room if we found it on the card
                    if ev_id and ev_id in id_to_room:
                        event_data["room"] = id_to_room[ev_id]

                    broadway_events.append(BroadwayEvent.from_dict(event_data))

            except (TypeError, ValueError) as e:
                # Log invalid event data but continue processing
                Logger.error(f"Failed to create BroadwayEvent from data: {event_data}, error: {e}")
                continue

        return broadway_events
