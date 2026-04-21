"""Ticket database handler for ticket-specific operations."""

from typing import List, TYPE_CHECKING

from sql.ticket_queries import TicketQueries

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.utilities.domain.ticket.utils import TicketUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger

from .model import Ticket

if TYPE_CHECKING:
    from laughtrack.core.entities.show.model import Show


class TicketHandler(BaseDatabaseHandler[Ticket]):
    """Handler for ticket database operations."""

    @staticmethod
    def _schema_org_ticket_type(ticket_type: str) -> bool:
        return ticket_type.startswith("http://schema.org/") or ticket_type.startswith("https://schema.org/")

    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "ticket"

    def get_entity_class(self) -> type[Ticket]:
        """Return the Ticket class for instantiation."""
        return Ticket

    def insert_tickets(self, shows: List["Show"]) -> None:
        """
        Insert tickets into the database.

        Args:
            conn: Database connection
            shows: List of shows containing tickets to insert
        """

        # Collect all tickets from shows
        all_tickets = []
        for show in shows:
            for ticket in show.tickets:
                ticket.show_id = show.id
                all_tickets.append(ticket)

        if not all_tickets:
            Logger.info("insert_tickets: no tickets to insert (shows have no ticket data)")
            return

        show_ids = sorted({show.id for show in shows if getattr(show, "id", None) is not None})

        # Deduplicate tickets based on unique constraint (show_id, type)
        deduplicated_tickets = TicketUtils.deduplicate_tickets(all_tickets)

        try:
            if show_ids:
                self.execute_with_cursor(
                    TicketQueries.DELETE_INVALID_SCHEMA_ORG_TICKETS_FOR_SHOWS,
                    (show_ids,),
                )

                removed_invalid = sum(
                    1 for ticket in deduplicated_tickets if self._schema_org_ticket_type(ticket.type)
                )
                if removed_invalid:
                    Logger.warning(
                        f"insert_tickets: dropping {removed_invalid} invalid schema.org ticket type(s) before insert"
                    )
                    deduplicated_tickets = [
                        ticket for ticket in deduplicated_tickets if not self._schema_org_ticket_type(ticket.type)
                    ]

            if not deduplicated_tickets:
                Logger.info("insert_tickets: no tickets to insert after invalid schema.org cleanup")
                return

            # Convert tickets to tuples for batch operation
            ticket_tuples = [ticket.to_tuple() for ticket in deduplicated_tickets]
            results = self.execute_batch_operation(TicketQueries.BATCH_ADD_TICKETS, ticket_tuples, return_results=True)
            result_count = len(results) if results else 0
            Logger.info(f"Successfully processed {result_count} ticket operations")

        except Exception as e:
            Logger.error(f"Error inserting tickets: {str(e)}")
            raise
