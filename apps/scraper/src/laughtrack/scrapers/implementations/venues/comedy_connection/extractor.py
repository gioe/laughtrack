"""Read the primary RSC event only; relatedEvents are recommendations."""

import json
import re
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from laughtrack.core.clients.rsc.extractor import extract_balanced, extract_push_payloads

from .data import ComedyConnectionEvent


class ComedyConnectionExtractor:
    @staticmethod
    def extract_events(html, url):
        payload = "".join(extract_push_payloads(html))
        event = None
        slug = urlparse(url).path.rstrip("/").split("/")[-1]
        for match in re.finditer(r'"event"\s*:\s*(\{)', payload):
            raw = extract_balanced(payload, match.start(1), "{", "}")
            if raw:
                candidate = json.loads(raw)
                if candidate.get("slug") == slug:
                    event = candidate
                    break
        if not event or not event.get("name") or not isinstance(event.get("shows"), list):
            raise ValueError(f"Comedy Connection primary event is missing for {url}")
        if not event["shows"] and not event.get("allShowsEnded"):
            raise ValueError(f"Comedy Connection unexpectedly empty show list for {url}")

        structured = {}
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            value = json.loads(script.string or script.get_text())
            nodes = value.get("@graph", [value]) if isinstance(value, dict) else value
            for node in nodes:
                if isinstance(node, dict) and node.get("@type") == "ComedyEvent":
                    structured[node.get("@id", "").split("#show-")[-1]] = node

        events = []
        seen = {}
        for show in event["shows"]:
            if not isinstance(show, dict) or not show.get("id"):
                raise ValueError(f"Comedy Connection invalid performance for {url}")
            show_id = str(show["id"])
            if show_id in seen:
                if seen[show_id] != show:
                    raise ValueError(f"Comedy Connection conflicting performance {show_id}")
                continue
            seen[show_id] = show
            if show.get("status") in {"cancelled", "canceled"}:
                continue
            ticket_url = show.get("ticketUrl", "")
            parsed = urlparse(ticket_url)
            if (
                parsed.scheme != "https"
                or parsed.hostname != "events.tixologi.com"
                or not re.fullmatch(r"/event/\d+/tickets/?", parsed.path)
            ):
                raise ValueError(f"Comedy Connection missing ticket URL for performance {show_id}")
            start = datetime.fromisoformat(show["startDate"].replace("Z", "+00:00"))
            if start.tzinfo is None:
                raise ValueError(f"Comedy Connection timezone missing for performance {show_id}")
            node = structured.get(show_id, {})
            offer = node.get("offers", {})
            price = offer.get("price") if isinstance(offer, dict) else None
            performers = node.get("performer", [])
            if isinstance(performers, dict):
                performers = [performers]
            events.append(
                ComedyConnectionEvent(
                    name=event["name"],
                    start=start,
                    ticket_url=ticket_url,
                    sold_out=show.get("status") == "sold-out",
                    price=float(price) if price is not None else None,
                    performers=[p["name"] for p in performers if isinstance(p, dict) and p.get("name")],
                )
            )
        return events
