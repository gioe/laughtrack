"""Data model for UCB WP Grid Builder show cards."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class UCBAdmission:
    """One physical admission; currency and fee evidence survive normalization."""

    name: str
    price: Optional[float]
    currency: str = "USD"
    fee_policy: str = "unspecified"
    sold_out: bool = False


@dataclass
class UCBEvent(ShowConvertible):
    """One dated UCB show card from the WP Grid Builder listing."""

    title: str
    date_text: str
    show_page_url: str
    ticket_url: str
    location_slug: str
    location_name: str
    description: str = ""
    admissions: list[UCBAdmission] = field(default_factory=list)

    def start_datetime(self, club: Club) -> datetime:
        parsed = datetime.strptime(self.date_text.strip(), "%A, %B %d, %Y @ %I:%M %p")
        return ShowFactoryUtils.parse_datetime_with_timezone_fallback(
            parsed.strftime("%Y-%m-%d %H:%M:%S"),
            club.timezone or "America/Los_Angeles",
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            start_date = self.start_datetime(club)
        except Exception:
            return None

        ticket_url = url or self.ticket_url or self.show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]
        if self.admissions:
            fee_labels = {"additional": "plus fees", "included": "fees included", "unspecified": "fees unspecified"}
            tickets = [
                ShowFactoryUtils.create_fallback_ticket(
                    ticket_url,
                    price=admission.price if admission.currency == "USD" else None,
                    ticket_type=f"{admission.name} ({fee_labels[admission.fee_policy]})",
                    sold_out=admission.sold_out,
                )
                for admission in self.admissions
            ]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_date,
            show_page_url=self.show_page_url or ticket_url,
            description=self.description,
            room=self.location_name,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
