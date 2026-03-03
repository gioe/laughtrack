from typing import Any, Callable, Dict, List, Optional
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.infrastructure.scraper import log_filter_breakdown
from laughtrack.foundation.utilities.url import URLUtils


class ShowPageUrlTicketAdapter:
    """Adapter that ensures Ticket.purchase_url uses an event's show page URL.

    The underlying object may be a provider ticket or a wrapper with a to_ticket method.
    """

    def __init__(self, underlying: object, url: str):
        self._underlying = underlying
        self._url = (url or "").strip()

    def to_ticket(self):
        # Deferred import to avoid circular dependencies
        from laughtrack.core.entities.ticket.model import Ticket

        if hasattr(self._underlying, "to_ticket") and callable(getattr(self._underlying, "to_ticket")):
            t = self._underlying.to_ticket()  # type: ignore[call-arg]
        elif isinstance(self._underlying, Ticket):
            t = self._underlying
        else:
            return Ticket(price=0.0, purchase_url=self._url, type="General Admission")

        if self._url:
            t.purchase_url = self._url
        return t


class BaseTicketBatchEnricher:
    """Generic base for batch-enriching events with provider tickets.

    Subclasses implement _fetch_tickets; base handles filtering, diagnostics, and attach.
    """

    def __init__(self, logger_context: Optional[dict] = None):
        self._logger_context = logger_context or {}

    async def enrich(
        self,
        events: List[Any],
        is_candidate: Callable[[Any], bool],
        event_id: Callable[[Any], Optional[str]],
        show_url: Callable[[Any], str],
        label: str = "Ticket enrichment",
    ) -> List[Any]:
        try:
            ids = log_filter_breakdown(
                events,
                self._logger_context,
                id_getter=event_id,
                accept_predicate=is_candidate,
                label=label,
                name_getter=lambda e: getattr(e, "mainArtist", ["n/a"])[0] if getattr(e, "mainArtist", []) else "n/a",
                date_getter=lambda e: getattr(e, "eventDate", "n/a"),
            )
            if not ids:
                Logger.info("No candidate events found to enrich", self._logger_context)
                return events

            tickets_map = await self._fetch_tickets(ids)
            enriched = self._attach(events, tickets_map, show_url)
            Logger.info(
                f"Successfully enriched {len([e for e in enriched if hasattr(e, '_ticket_data')])} events with ticket data",
                self._logger_context,
            )
            return enriched
        except Exception as e:
            Logger.error(f"Error during ticket enrichment: {e}", self._logger_context)
            return events

    async def _fetch_tickets(self, event_ids: List[str]) -> Dict[str, List]:  # pragma: no cover - abstract
        raise NotImplementedError

    def _attach(self, events: List[Any], tickets_map: Dict[str, List], show_url: Callable[[Any], str]) -> List[Any]:
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
            enriched.append(e)
        return enriched

    def _normalize_show_url(self, url: str) -> str:
        """Default URL normalizer. Subclasses may override for provider-specific rules."""
        if not url:
            return ""
        return URLUtils.normalize_url(url) if URLUtils.is_valid_url(url) else url
