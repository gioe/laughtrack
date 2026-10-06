"""Read-only classic venue identity -> official website structured geo evidence.

The API does not expose an address. Only a website it authorizes and one
unambiguous venue-level EventVenue address can resolve geography. No DB writes,
Google search, prose extraction, or guessed corrections occur here.
"""

import asyncio
import json
import re
from urllib.parse import urlsplit

from laughtrack.core.clients.seatengine.client import SeatEngineClient
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


def text(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def identity_url(value):
    if not isinstance(value, str):
        return None
    p = urlsplit(value)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        return None
    return (p.hostname.lower().removeprefix("www."), p.path.rstrip("/"))


def structured_geo(html, website, venue_name):
    """Reject branch/venue ambiguity, including conflicting address records."""

    def nodes(value):
        if isinstance(value, list):
            for item in value:
                yield from nodes(item)
        elif isinstance(value, dict):
            yield value
            if "@graph" in value:
                yield from nodes(value["@graph"])

    candidates = []
    malformed = False
    for raw in HtmlScraper.get_json_ld_script_contents(html):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            malformed = True
            continue
        for node in nodes(parsed):
            kinds = node.get("@type", [])
            if isinstance(kinds, str):
                kinds = [kinds]
            if not isinstance(kinds, list) or not any(
                str(k).rstrip("/").rsplit("/", 1)[-1] == "EventVenue" for k in kinds
            ):
                continue
            candidates.append(node)
    if malformed:
        return dict(status="conflicting_metadata", reason="malformed_jsonld")
    if not candidates:
        return dict(status="missing_metadata", reason="no_eventvenue_jsonld")
    evidence = []
    for node in candidates:
        address = node.get("address")
        evidence.append(
            dict(
                name=node.get("name") if isinstance(node.get("name"), str) else None,
                url=node.get("url") if isinstance(node.get("url"), str) else None,
                address={
                    key: value
                    for key, value in (address.items() if isinstance(address, dict) else [])
                    if key in ("streetAddress", "addressLocality", "addressRegion", "postalCode")
                    and isinstance(value, str)
                },
            )
        )
    addresses = []
    for node in candidates:
        address = node.get("address")
        if not isinstance(address, dict) or any(
            not text(address.get(k)) for k in ("streetAddress", "addressLocality", "addressRegion")
        ):
            return dict(status="conflicting_metadata", reason="incomplete_eventvenue_address", candidates=evidence)
        bound = node.get("url") or node.get("@id")
        if identity_url(bound) != identity_url(website) or text(node.get("name")) != text(venue_name):
            return dict(status="conflicting_metadata", reason="unbound_or_multiple_venues", candidates=evidence)
        state = address["addressRegion"].strip().upper()
        if not re.fullmatch("[A-Z]{2}", state):
            return dict(status="conflicting_metadata", reason="unrecognized_state", candidates=evidence)
        addresses.append(
            dict(
                name=node["name"],
                city=address["addressLocality"].strip(),
                state=state,
                street_address=address["streetAddress"].strip(),
                postal_code=address.get("postalCode") if isinstance(address.get("postalCode"), str) else None,
                structured_url=bound,
            )
        )
    keys = {(text(a["street_address"]), text(a["city"]), a["state"]) for a in addresses}
    if len(keys) != 1:
        return dict(status="conflicting_metadata", reason="conflicting_venue_addresses", addresses=addresses)
    postals = sorted({str(a["postal_code"]).strip() for a in addresses if a["postal_code"]})
    result = dict(addresses[0], status="resolved", postal_codes=postals, warnings=[])
    if len(postals) > 1:
        result["postal_code"] = None
        result["warnings"].append("conflicting_structured_postal_codes")
    return result


def client_for(venue_id):
    club = Club(
        id=0,
        name="SeatEngine geo audit",
        address="",
        website="https://services.seatengine.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=False,
    )
    club.active_scraping_source = ScrapingSource(
        id=0,
        club_id=0,
        platform="seatengine",
        scraper_key="seatengine",
        seatengine_id=int(venue_id),
        source_url="https://services.seatengine.com",
    )
    return SeatEngineClient(club)


async def resolve_venue(venue_id, *, timeout=25, client_factory=client_for):
    """Bound two native HTTP operations; exception messages never enter evidence."""
    api_url = f"https://services.seatengine.com/api/v1/venues/{venue_id}"
    evidence = dict(venue_id=str(venue_id), api_url=api_url)

    async def resolve():
        if not re.fullmatch("[1-9][0-9]*", str(venue_id)):
            return dict(evidence, status="invalid_id")
        client = client_factory(venue_id)
        venue = await client.fetch_venue_details(str(venue_id))
        if not isinstance(venue, dict):
            return dict(evidence, status="fetch_error", reason="venue_api_unavailable")
        if str(venue.get("id")) != str(venue_id):
            return dict(evidence, status="conflicting_metadata", reason="api_identity_mismatch")
        website = venue.get("website")
        if not identity_url(website):
            return dict(evidence, status="missing_metadata", reason="missing_authorized_website")
        evidence["website_url"] = website
        html = await client.fetch_html(website, headers={"accept": "text/html"}, timeout=timeout)
        if not html:
            return dict(evidence, status="fetch_error", reason="official_website_unavailable")
        return dict(evidence, **structured_geo(html, website, venue.get("name")))

    try:
        return await asyncio.wait_for(resolve(), timeout=timeout)
    except asyncio.TimeoutError:
        return dict(evidence, status="fetch_error", reason="timeout")
    except Exception as exc:
        return dict(evidence, status="fetch_error", reason=type(exc).__name__)


async def resolve_venues(venue_ids, *, max_resolve=None, concurrency=4, timeout=25):
    ids = sorted(set(map(str, venue_ids)))
    selected = ids if max_resolve is None else ids[:max_resolve]
    semaphore = asyncio.Semaphore(concurrency)

    async def one(ident):
        async with semaphore:
            return ident, await resolve_venue(ident, timeout=timeout)

    result = dict(await asyncio.gather(*(one(i) for i in selected)))
    result.update({i: dict(status="capped", reason="max_resolve_limit", venue_id=i) for i in ids if i not in result})
    return result
