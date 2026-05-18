"""HTML extraction for SellingTicket event list pages."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.sellingticket import SellingTicketEvent


class SellingTicketExtractor:
    """Extract event rows from SellingTicket's server-rendered table."""

    @staticmethod
    def extract_events(html: str, source_url: str) -> list[SellingTicketEvent]:
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: list[SellingTicketEvent] = []
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            title = SellingTicketExtractor._clean(cells[0].get_text(" ", strip=True))
            if not title or title.lower() == "title event":
                continue

            address = SellingTicketExtractor._clean(cells[1].get_text(" ", strip=True))
            weekday = SellingTicketExtractor._clean(cells[2].get_text(" ", strip=True))
            date_time = SellingTicketExtractor._clean(cells[3].get_text(" ", strip=True))
            ticket_link = cells[4].find("a", href=True)
            if not date_time or not ticket_link:
                continue

            events.append(
                SellingTicketEvent(
                    title=title,
                    address=address,
                    weekday=weekday,
                    date_time=date_time,
                    ticket_url=urljoin(source_url, ticket_link["href"]),
                    source_url=source_url,
                )
            )

        return events

    @staticmethod
    def _clean(value: str) -> str:
        return " ".join((value or "").split())
