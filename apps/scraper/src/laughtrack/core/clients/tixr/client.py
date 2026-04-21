"""
Simplified Tixr API client for fetching event details.
"""

import html
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from curl_cffi.requests import AsyncSession

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.foundation.models.types import JSONDict
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.core.clients.base import BaseApiClient
from laughtrack.core.clients.tixr.tixr_failure_monitor import FailureType
from laughtrack.foundation.infrastructure.http.client import _bot_block_reason, _get_js_browser
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.foundation.utilities.url import URLUtils


class TixrApiException(Exception):
    """Custom exception for Tixr API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class TixrClient(BaseApiClient):
    """
    Simplified client for interfacing with the Tixr API to fetch event details.

    Uses BaseApiClient for HTTP operations and focuses on core functionality.
    """

    def __init__(self, club: Club, proxy_pool: Optional[ProxyPool] = None):
        """
        Initialize the Tixr client.

        Args:
            club: Club instance for configuration
            proxy_pool: Optional ProxyPool for rotating proxy support
        """
        super().__init__(club, proxy_pool=proxy_pool)

        # Tixr API configuration
        self.base_api_url = "https://api.tixr.com/api/events"
        self.base_url = "https://www.tixr.com"

        # Override headers for Tixr API
        self.headers.update(
            {
                "Accept": "application/json",
                "Referer": self.base_url,
            }
        )

        self._failure_monitor = self._resolve_failure_monitor()

    def _resolve_failure_monitor(self) -> Optional[Any]:
        # Lazy — imported inside the method to avoid a module-level import cycle
        # between core.clients.tixr.client and infrastructure.monitoring.integrations.tixr
        # (the latter imports TixrClient in its create_monitored_client path).
        try:
            from laughtrack.infrastructure.monitoring.client_integration import (
                get_tixr_failure_monitor,
            )

            return get_tixr_failure_monitor(self.club)
        except Exception as exc:
            # Surface the misconfiguration — a silent None means every group-page
            # DataDome block goes unrecorded, which is itself a triage event.
            Logger.warn(
                f"[TixrClient] Tixr failure monitor unavailable: {exc} — "
                f"group-page DataDome blocks will not be recorded",
                {"club_name": getattr(self.club, "name", "-")},
            )
            return None

    async def get_event_detail(self, event_id: str) -> Optional[TixrEvent]:
        """
        Get event details from Tixr API for a specific event ID.

        Args:
            event_id: The Tixr event ID

        Returns:
            TixrEvent object if successful, None otherwise
        """
        api_url = f"{self.base_api_url}/{event_id}"

        try:
            data = await self.fetch_json(url=api_url, logger_context={"event_id": event_id})

            if not data:
                self.log_warning(f"No data returned for event {event_id}")
                return None

            # Create Show object from the data
            show = self._create_show_from_data(data)
            if not show:
                self.log_warning(f"Failed to create show from data for event {event_id}")
                return None

            # Return TixrEvent wrapping the Show
            return TixrEvent.from_tixr_show(show=show, source_url=api_url, event_id=event_id)

        except Exception as e:
            self.log_error(f"Failed to fetch event {event_id}: {e}")
            return None

    async def get_event_detail_from_url(self, url: str) -> Optional[TixrEvent]:
        """
        Fetch event details by scraping the Tixr event page for JSON-LD structured data.

        The Tixr JSON API (api.tixr.com) requires authentication and returns HTML for
        unauthenticated requests. Instead, we fetch the public event page and parse the
        JSON-LD @type=Event block, which Tixr embeds for SEO purposes.

        Args:
            url: Tixr event page URL (e.g. tixr.com/groups/{group}/events/{slug})

        Returns:
            TixrEvent object if successful, None otherwise
        """
        # Tixr's DataDome protection blocks requests that carry certain header
        # combinations (e.g. Accept-Language + Cache-Control + Pragma together).
        # curl_cffi's impersonation sets a clean, browser-consistent fingerprint
        # on its own — passing *any* custom headers breaks that fingerprint and
        # triggers the 403. Fetch directly without extra headers.
        html = await self._fetch_tixr_page(url)
        if not html:
            self.log_warning(f"No HTML content returned for {url}")
            return None

        jsonld = self._extract_jsonld_event(html)
        if not jsonld:
            # Some Tixr event pages — particularly those with the --{id} double-dash
            # URL format — do not embed JSON-LD when the page is client-side rendered.
            # Event data for these pages is fetched via www.tixr.com/api/events/{id}
            # which requires a DataDome CAPTCHA-solved JS session; curl_cffi cannot
            # bypass it. No fallback is available without full browser execution.
            # Note: not all --{id} URLs lack JSON-LD; those listed in the venue's
            # Organization JSON-LD block (e.g. on a group page) typically do embed it.
            if re.search(r"--\d+(?:[/?#]|$)", url):
                self.log_warning(
                    f"Tixr special-event page (--ID format) has no JSON-LD; "
                    f"data requires JS execution — skipping: {url}"
                )
            else:
                self.log_warning(f"No JSON-LD Event block found in page: {url}")
            return None

        show = self._create_show_from_jsonld(jsonld, url)
        if not show:
            self.log_warning(f"Failed to create Show from JSON-LD for {url}")
            return None

        event_id = URLUtils.extract_id_from_url(url, ["/events/"])
        if event_id is None:
            # Slug-only URL (e.g. /events/standup-saturday) — use full slug as event_id
            parsed_path = urlparse(url).path
            if "/events/" in parsed_path:
                segment = parsed_path.split("/events/", 1)[-1].split("/")[0]
                event_id = segment or ""
            else:
                event_id = ""
        return TixrEvent.from_tixr_show(show=show, source_url=url, event_id=event_id)

    async def fetch_events(self, *args, **kwargs) -> List[JSONDict]:
        """
        Fetch events from Tixr API.

        Note: TixrClient is designed to work with specific event IDs/URLs
        rather than fetching lists of events. This method is required by
        the BaseApiClient interface.

        Returns:
            Empty list (Tixr client works with specific event requests)
        """
        self.log_info("TixrClient works with specific event IDs/URLs, not general event fetching")
        return []

    async def _fetch_tixr_page(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Fetch a Tixr group/event page HTML without application-level custom headers.

        Tixr's DataDome bot-detection blocks requests that carry specific header
        combinations (e.g. Accept-Language + Cache-Control + Pragma together).
        curl_cffi's Chrome impersonation sends a browser-consistent fingerprint on
        its own — passing our API header dict disrupts that fingerprint and
        triggers 403s. This method therefore sends only curl_cffi's built-in
        impersonation headers.

        The request is performed inline (not via ``HttpClient.fetch_html``) so
        the raw response can be inspected for DataDome signatures *before* any
        Playwright rescue — a successful rescue would otherwise hide the block
        from ``TixrFailureMonitor`` and silently degrade group-page fetches to
        "0 URLs extracted" in triage. After recording the block, the shared
        bot-block → Playwright fallback machinery from
        ``foundation.infrastructure.http.client`` is reused so the recovery
        behavior remains identical to the previous ``HttpClient.fetch_html``
        path.

        When a ``proxy_pool`` is configured on this client, the curl-cffi GET
        and the Playwright fallback are routed through the next pool proxy so
        group-page fetches participate in the same rotation as event-detail
        and JSON API calls. Proxy outcome accounting mirrors
        ``BaseApiClient.fetch_html``: a non-``None`` final return reports
        success to the pool; ``None`` reports failure.

        Args:
            url: Tixr event page URL
            timeout: Request timeout in seconds (default 30)

        Returns:
            HTML string on success (from curl_cffi or the Playwright fallback),
            ``None`` when both the direct fetch and the fallback fail.
        """
        normalized_url = URLUtils.normalize_url(url)
        logger_context = {
            "club_name": getattr(self.club, "name", "-"),
            "url": normalized_url,
        }

        proxy_url = self._get_proxy_url()
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        try:
            async with AsyncSession(
                impersonate=self._get_impersonation_target(url),
                timeout=timeout,
            ) as session:
                await self._apply_rate_limit(url)
                response = await session.get(normalized_url, proxies=proxies)
                # Materialize everything we need from the response *inside* the
                # session context so we don't depend on curl_cffi keeping a
                # fully-buffered body around after the session closes.
                status = response.status_code
                response_headers = self._response_headers_dict(response)
                body = response.text or ""
        except Exception as e:
            self._report_proxy_outcome(proxy_url, success=False)
            self.log_error(f"Failed to fetch Tixr page {url}: {e}")
            return None

        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_response(status)

        # 5xx is a server-side failure and Playwright cannot rescue it — short-
        # circuit before DataDome classification so a 5xx that happens to carry
        # a DataDome marker does not log a WARN pair (the monitor would also
        # reclassify it as NETWORK_ERROR anyway).
        if 500 <= status < 600:
            self.log_warning(f"Tixr HTTP {status} fetching group page: {normalized_url}")
            self._report_proxy_outcome(proxy_url, success=False)
            return None

        datadome_type = self._classify_datadome(response_headers, body)
        if datadome_type is not None:
            self.log_warning(
                f"Tixr group-page DataDome interstitial detected "
                f"(type={datadome_type.value}, status={status}): {normalized_url}"
            )
            self._record_group_page_datadome(
                url=normalized_url,
                status_code=status,
                response_headers=response_headers,
                response_body=body,
            )

        fallback_reason: Optional[str] = None
        if status != 200:
            fallback_reason = f"HTTP {status}"
            if body:
                sig = _bot_block_reason(body)
                if sig is not None:
                    if diagnostics is not None:
                        diagnostics.record_bot_block(sig)
                    fallback_reason = sig
        elif not body.strip():
            fallback_reason = "empty body"
        else:
            sig = _bot_block_reason(body)
            if sig is not None:
                if diagnostics is not None:
                    diagnostics.record_bot_block(sig)
                fallback_reason = sig

        if fallback_reason is None:
            self._report_proxy_outcome(proxy_url, success=True)
            return body

        browser = _get_js_browser()
        if browser is None:
            self._report_proxy_outcome(proxy_url, success=False)
            return None
        if diagnostics is not None:
            diagnostics.record_playwright_fallback()
        Logger.info(
            f"[TixrClient] Triggering Playwright fallback for {normalized_url} "
            f"(reason: {fallback_reason!r})",
            logger_context,
        )
        try:
            fallback_html = await browser.fetch_html(normalized_url, proxy_url=proxy_url)
        except Exception as exc:
            self.log_warning(
                f"[TixrClient] Playwright fallback failed for {normalized_url}: {exc}"
            )
            fallback_html = None

        self._report_proxy_outcome(proxy_url, success=fallback_html is not None)
        return fallback_html

    @staticmethod
    def _response_headers_dict(response: Any) -> Dict[str, str]:
        try:
            headers = response.headers
            if headers is None:
                return {}
            return {str(k): str(v) for k, v in dict(headers).items()}
        except Exception:
            return {}

    @staticmethod
    def _classify_datadome(
        response_headers: Dict[str, str], body: str
    ) -> Optional[FailureType]:
        if any(k.lower() == "x-datadome" for k in response_headers):
            return FailureType.DATADOME_COOKIE
        body_lower = body.lower() if body else ""
        if "datadome" in body_lower or "captcha-delivery.com" in body_lower:
            if "captcha" in body_lower:
                return FailureType.DATADOME_CAPTCHA
            return FailureType.DATADOME_COOKIE
        return None

    def _record_group_page_datadome(
        self,
        url: str,
        status_code: int,
        response_headers: Dict[str, str],
        response_body: str,
    ) -> None:
        monitor = self._failure_monitor
        if monitor is None:
            return
        try:
            monitor.record_request_result(
                event_id=url,
                status_code=status_code,
                response_headers=response_headers,
                response_body=response_body,
                club=self.club,
            )
        except Exception as exc:
            self.log_warning(f"Failed to record Tixr group-page failure: {exc}")

    def _extract_jsonld_event(self, html: str) -> Optional[Dict[str, Any]]:
        """
        Extract the first @type=Event JSON-LD block from an HTML page.

        Args:
            html: Full HTML content of a Tixr event page

        Returns:
            Parsed JSON-LD dict for the Event, or None if not found
        """
        _EVENT_TYPES = {"Event", "MusicEvent", "TheaterEvent", "ComedyEvent", "SocialEvent"}

        blocks = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        for item in JSONUtils.parse_json_ld_contents(blocks):
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            # @type may be a string or a list of type strings
            types = item_type if isinstance(item_type, list) else [item_type]
            if any(t in _EVENT_TYPES for t in types):
                return item
        return None

    def _create_show_from_jsonld(self, data: Dict[str, Any], page_url: str) -> Optional[Show]:
        """
        Create a Show object from a JSON-LD Event schema dict.

        Args:
            data: JSON-LD Event dict (from _extract_jsonld_event)
            page_url: The event page URL (used as fallback show_page_url)

        Returns:
            Show object if successful, None otherwise
        """
        try:
            name = html.unescape(data.get("name", ""))
            start_date = data.get("startDate")
            if not start_date:
                self.log_warning(f"JSON-LD Event has no startDate for {page_url}")
                return None

            try:
                date = DateTimeUtils.parse_datetime_with_timezone(start_date, None)
            except Exception as e:
                self.log_warning(f"Could not parse startDate {start_date!r} for {page_url}: {e}")
                return None

            show_page_url = data.get("url") or page_url
            raw_description = data.get("description")
            description = html.unescape(raw_description) if raw_description else raw_description

            # Extract lineup from performer array
            lineup: List[Comedian] = []
            for performer in data.get("performer", []):
                if isinstance(performer, dict):
                    performer_name = html.unescape(performer.get("name", "").strip())
                elif isinstance(performer, str):
                    performer_name = html.unescape(performer.strip())
                else:
                    continue
                if performer_name:
                    lineup.append(Comedian(name=performer_name))

            # Extract tickets from offers array
            tickets: List[Ticket] = []
            for offer in data.get("offers", []):
                if not isinstance(offer, dict):
                    continue
                try:
                    price = float(offer.get("price", 0))
                except (ValueError, TypeError):
                    price = 0.0
                availability = offer.get("availability", "")
                sold_out = "SoldOut" in availability
                ticket_type = html.unescape(offer.get("name", "General Admission"))
                tickets.append(
                    Ticket(
                        price=price,
                        purchase_url=offer.get("url", show_page_url),
                        sold_out=sold_out,
                        type=ticket_type,
                    )
                )

            if not tickets:
                self.log_warning(f"No offers found in JSON-LD for {page_url}; inserting placeholder ticket")
                # No offers means no availability signal; default to not sold out
                tickets.append(Ticket(price=0, purchase_url=show_page_url, sold_out=False, type="General Admission"))

            return Show(
                name=name,
                club_id=self.club.id,
                date=date,
                show_page_url=show_page_url,
                lineup=lineup,
                tickets=tickets,
                supplied_tags=["event"],
                description=description,
                timezone=None,
                room="",
            )

        except Exception as e:
            self.log_error(f"Failed to create show from JSON-LD: {e}")
            return None

    def _create_show_from_data(self, data: JSONDict) -> Optional[Show]:
        """
        Create a Show object from parsed Tixr API data.

        Args:
            data: Parsed JSON data from Tixr API

        Returns:
            Show object if successful, None otherwise
        """
        try:
            # Validate response structure
            if not isinstance(data, dict):
                self.log_warning("Invalid response format: expected dict")
                return None

            # Extract basic event information
            name = data.get("name", "")
            event_id = data.get("id", "")

            # Extract venue timezone if available
            timezone = None
            venue_data = data.get("venue", {})
            if isinstance(venue_data, dict):
                timezone = venue_data.get("timezone")

            # Parse event date
            date = None
            formatted_iso = data.get("formattedISOStartDate")
            if formatted_iso:
                date = DateTimeUtils.parse_datetime_with_timezone(formatted_iso, timezone)

            # Skip events without valid date
            if not date:
                self.log_warning(f"Event {event_id} has no valid date, skipping")
                return None

            # Build show page URL
            show_page_url = self._build_show_page_url(data, event_id)

            # Extract description
            description = data.get("description")

            # Extract lineup/comedians
            lineup = self._extract_lineup(data)

            # Extract ticket information
            tickets = self._extract_ticket_info(data, show_page_url)

            # Default values for fields not available in Tixr API
            supplied_tags = ["event"]  # Default tag as per project pattern
            room = ""  # Default empty room as per project pattern

            return Show(
                name=name,
                club_id=self.club.id,
                date=date,
                show_page_url=show_page_url,
                lineup=lineup,
                tickets=tickets,
                supplied_tags=supplied_tags,
                description=description,
                timezone=timezone,
                room=room,
            )

        except Exception as e:
            self.log_error(f"Failed to create show from Tixr data: {e}")
            return None

    def _build_show_page_url(self, data: dict, event_id: str) -> str:
        """
        Build the public show page URL from event data.

        Args:
            data: Event data from API
            event_id: Event ID

        Returns:
            Public URL for the event page
        """
        # Try to get URL from response data first
        if data.get("url"):
            return data["url"]

        # Build URL from group subdomain and event info
        group_data = data.get("group", {})
        subdomain = group_data.get("subdomain", "")

        if subdomain:
            # Use short name if available, otherwise use event name
            short_name = data.get("shortName", "")
            if not short_name:
                short_name = data.get("name", "").replace(" ", "-").lower()

            return f"https://www.tixr.com/groups/{subdomain}/events/{short_name}-{event_id}"

        # Fallback URL format
        return f"https://www.tixr.com/groups/events/{event_id}"

    def _extract_lineup(self, data: dict) -> List[Comedian]:
        """
        Extract comedian lineup from event data.

        Args:
            data: Event data from API

        Returns:
            List of Comedian objects
        """
        lineup = []

        # Check for lineups in the response
        lineups_data = data.get("lineups", [])
        if isinstance(lineups_data, list):
            for lineup_entry in lineups_data:
                if not isinstance(lineup_entry, dict):
                    continue

                acts = lineup_entry.get("acts", [])
                if isinstance(acts, list):
                    for act in acts:
                        if isinstance(act, dict):
                            # Tixr structure: act.artist.name
                            artist = act.get("artist", {})
                            if isinstance(artist, dict):
                                artist_name = artist.get("name", "").strip()
                                if artist_name:
                                    lineup.append(Comedian(name=artist_name))
                        elif isinstance(act, str) and act.strip():
                            # Fallback for direct string names
                            lineup.append(Comedian(name=act.strip()))

        # Also check for artists field (alternative structure)
        artists_data = data.get("artists", [])
        if isinstance(artists_data, list):
            for artist in artists_data:
                if isinstance(artist, dict):
                    artist_name = artist.get("name", "").strip()
                    if artist_name:
                        lineup.append(Comedian(name=artist_name))
                elif isinstance(artist, str) and artist.strip():
                    lineup.append(Comedian(name=artist.strip()))

        return lineup

    def _extract_ticket_info(self, data: dict, show_page_url: str) -> List[Ticket]:
        """
        Extract ticket information from event data.

        Args:
            data: Event data from API
            show_page_url: URL for purchasing tickets

        Returns:
            List of Ticket objects
        """
        tickets = []

        # Extract from sales data
        sales_data = data.get("sales", [])
        if isinstance(sales_data, list):
            for sale in sales_data:
                if not isinstance(sale, dict):
                    continue

                tiers = sale.get("tiers", [])
                if isinstance(tiers, list):
                    for tier in tiers:
                        if not isinstance(tier, dict):
                            continue

                        # Extract ticket information
                        price = tier.get("price")
                        sold_out = not tier.get("active", True)
                        ticket_type = tier.get("name", "General Admission")

                        # Validate price (should be numeric)
                        if price is not None:
                            try:
                                price = float(price)
                            except (ValueError, TypeError):
                                price = None

                        ticket = Ticket(
                            price=price or 0, purchase_url=show_page_url, sold_out=sold_out, type=ticket_type
                        )
                        tickets.append(ticket)

        # If no tickets found from sales, check for direct ticket info
        if not tickets:
            # Check for ticket URL or pricing in main event data
            ticket_url = data.get("ticketUrl", show_page_url)

            # Create a default ticket entry if event has ticket info
            if data.get("hasTickets", True):  # Assume tickets available unless specified
                ticket = Ticket(
                    price=0,  # Price not available
                    purchase_url=ticket_url,
                    sold_out=data.get("soldOut", False),
                    type="General Admission",
                )
                tickets.append(ticket)

        return tickets
