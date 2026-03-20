from typing import Any, Callable, Dict, List, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.scraper import BatchScraper
from laughtrack.foundation.utilities.url import URLUtils
from laughtrack.scrapers.utils.ticket_enrichment import (
    BaseTicketBatchEnricher,
    ShowPageUrlTicketAdapter,
)


class TesseraTicketBatchEnricher(BaseTicketBatchEnricher):
    """Batch-enrich events with Tessera ticket data, applying a URL override policy."""

    def __init__(self, tessera_client: Any, logger_context: Optional[dict] = None, base_url: Optional[str] = None):
        super().__init__(logger_context)
        self._client = tessera_client
        self._batch = BatchScraper(logger_context={**self._logger_context, "client": "tessera"})
        self._base_url = URLUtils.get_base_domain_with_protocol(URLUtils.normalize_url(base_url)) if base_url else None

    async def enrich(
        self,
        events: List[Any],
        is_candidate: Callable[[Any], bool],
        event_id: Callable[[Any], Optional[str]],
        show_url: Callable[[Any], str],
        label: str = "Tessera ticket enrichment",
    ) -> List[Any]:
        """Enrich events and drop any Tessera candidates that received no ticket data.

        Filtering is performed here — in the enricher — so that every Tessera-backed
        scraper automatically inherits the protection without per-scraper boilerplate.
        """
        enriched = await super().enrich(events, is_candidate, event_id, show_url, label)

        output: List[Any] = []
        for e in enriched:
            if is_candidate(e) and not getattr(e, "_ticket_data", None):
                Logger.warning(
                    f"Skipping Tessera event {event_id(e)!r} — no ticket data returned; "
                    "event may be stale or unavailable",
                    self._logger_context,
                )
            else:
                output.append(e)
        return output

    async def _fetch_tickets(self, event_ids: List[str]) -> Dict[str, List]:
        Logger.info(f"Fetching tickets for {len(event_ids)} Tessera events", self._logger_context)

        async def fetch_one(eid: str):
            tickets = await self._client.get_ticket(eid)
            for t in tickets:
                if hasattr(t, "event_id"):
                    setattr(t, "event_id", eid)
            return eid, tickets

        results = await self._batch.process_batch(event_ids, fetch_one, "tessera ticket fetching")

        tickets_map: Dict[str, List] = {}
        success_count = 0
        error_count = 0
        for pair in results:
            if not pair:
                error_count += 1
                continue
            eid, tickets = pair
            tickets_map.setdefault(eid, []).extend(tickets or [])
            success_count += 1

        Logger.info(
            f"TesseraTicket batch complete: {success_count} successful, {error_count} errors",
            self._logger_context,
        )
        return tickets_map

    def _normalize_show_url(self, url: str) -> str:
        if not url:
            return ""
        if URLUtils.is_valid_url(url):
            return URLUtils.normalize_url(url)
        if self._base_url:
            return URLUtils.build_url(self._base_url, url)
        return url

    def _attach(self, events: List[Any], tickets_map: Dict[str, List], show_url):  # type: ignore[override]
        """Attach tickets and warn only when the final ticket URL is invalid."""
        enriched: List[Any] = []
        for e in events:
            eid = getattr(e, "id", None)

            if eid and eid in tickets_map:
                underlying_list = tickets_map[eid] or []
                underlying = underlying_list[0] if underlying_list else None
                candidate = (show_url(e) or "").strip()
                effective_url = self._normalize_show_url(candidate)

                if underlying is not None and effective_url:
                    e._ticket_data = ShowPageUrlTicketAdapter(underlying, effective_url)
                else:
                    e._ticket_data = underlying_list

                # Validate the final URL that would be used by the ticket
                final_url = ""
                if underlying is not None and effective_url:
                    # Override applies; final URL is the effective show URL
                    final_url = effective_url
                elif underlying is not None:
                    # No override; final URL is the provider/raw purchase_url
                    final_url = getattr(underlying, "purchase_url", "") or ""

                if final_url and not URLUtils.is_valid_url(final_url):
                    Logger.warning(
                        f"Invalid ticket URL for event {eid}: '{final_url}'",
                        self._logger_context,
                    )
                elif not final_url and underlying is not None:
                    # Underlying tickets exist but no usable URL resolved
                    Logger.warning(
                        f"Missing ticket URL for event {eid} (no effective or raw URL)",
                        self._logger_context,
                    )
            enriched.append(e)
        return enriched
