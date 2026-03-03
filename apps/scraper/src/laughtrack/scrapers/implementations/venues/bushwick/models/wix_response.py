"""
Comprehensive dataclasses representing the Wix Events API JSON response structure.

These models represent the complete structure returned by Bushwick Comedy Club's
Wix Events API endpoint, including all nested objects and configuration data.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Coordinates:
    """Geographic coordinates."""

    lat: float
    lng: float


@dataclass
class StreetAddress:
    """Street address components."""

    number: str
    name: str
    apt: str


@dataclass
class Geocode:
    """Geocode data."""

    latitude: float
    longitude: float


@dataclass
class Subdivision:
    """Administrative subdivision data."""

    code: str
    name: str
    type: int


@dataclass
class FullAddress:
    """Complete address information."""

    country: str
    subdivision: str
    city: str
    postalCode: str
    streetAddress: StreetAddress
    formattedAddress: str
    geocode: Geocode
    countryFullname: str
    subdivisions: List[Subdivision]


@dataclass
class Location:
    """Event location data."""

    name: str
    coordinates: Coordinates
    address: str
    type: int
    fullAddress: FullAddress
    tbd: bool


@dataclass
class Recurrences:
    """Event recurrence configuration."""

    occurrences: List[Any]  # Could be more specific if structure known
    categoryId: str
    status: int


@dataclass
class SchedulingConfig:
    """Scheduling configuration data."""

    scheduleTbd: bool
    startDate: str
    endDate: str
    timeZoneId: str
    endDateHidden: bool
    showTimeZone: bool
    recurrences: Recurrences


@dataclass
class Scheduling:
    """Event scheduling information."""

    config: SchedulingConfig
    formatted: str
    startDateFormatted: str
    startTimeFormatted: str
    endDateFormatted: str
    endTimeFormatted: str


@dataclass
class MainImage:
    """Event main image data."""

    id: str
    url: str
    height: int
    width: int


@dataclass
class ConfirmationMessage:
    """Confirmation message configuration."""

    title: str
    message: str
    addToCalendarActionLabel: str
    shareActionLabel: str


@dataclass
class WaitlistMessage:
    """Waitlist message configuration."""

    title: str
    message: str
    addToCalendarActionLabel: str
    shareActionLabel: str


@dataclass
class NegativeMessage:
    """Negative response message configuration."""

    title: str
    shareActionLabel: str


@dataclass
class ConfirmationMessages:
    """All confirmation message types."""

    positiveConfirmation: ConfirmationMessage
    waitlistMessages: WaitlistMessage
    negativeMessages: NegativeMessage


@dataclass
class RsvpConfig:
    """RSVP collection configuration."""

    rsvpStatusOptions: int
    waitlist: bool
    confirmationMessages: ConfirmationMessages


@dataclass
class RsvpCollection:
    """RSVP collection settings."""

    config: RsvpConfig


@dataclass
class TaxConfig:
    """Tax configuration for ticketing."""

    type: int
    name: str
    rate: str
    appliesToDonations: bool


@dataclass
class TicketConfirmationMessages:
    """Ticket confirmation message configuration."""

    title: str
    message: str
    downloadTicketsLabel: str
    addToCalendarActionLabel: str
    shareActionLabel: str


@dataclass
class TicketingConfig:
    """Ticketing system configuration."""

    guestAssignedTickets: bool
    taxConfig: TaxConfig
    ticketLimitPerOrder: int
    reservationDurationInMinutes: int
    gracePeriodInMinutes: int
    confirmationMessages: TicketConfirmationMessages


@dataclass
class TicketPrice:
    """Individual ticket price data."""

    amount: str
    currency: str
    value: str


@dataclass
class Ticketing:
    """Event ticketing information."""

    lowestPrice: str
    highestPrice: str
    currency: str
    config: TicketingConfig
    lowestTicketPrice: TicketPrice
    highestTicketPrice: TicketPrice
    lowestTicketPriceFormatted: str
    highestTicketPriceFormatted: str
    soldOut: bool


@dataclass
class Registration:
    """Event registration information."""

    type: int
    status: int
    rsvpCollection: RsvpCollection
    ticketing: Ticketing
    restrictedTo: int
    initialType: int


@dataclass
class CalendarLinks:
    """Calendar integration links."""

    google: str
    ics: str


@dataclass
class GuestListConfig:
    """Guest list configuration."""

    publicGuestList: bool


@dataclass
class OnlineConferencing:
    """Online conferencing settings."""

    providerName: str


@dataclass
class EventDisplaySettings:
    """Event display configuration (empty in this example)."""

    pass


@dataclass
class LabellingSettings:
    """Event labelling configuration."""

    assignedContactsLabelDeleted: bool


@dataclass
class WixEvent:
    """Complete Wix event data structure."""

    id: str
    location: Location
    scheduling: Scheduling
    title: str
    description: str
    about: str
    mainImage: MainImage
    slug: str
    language: str
    created: str
    modified: str
    status: int
    registration: Registration
    calendarLinks: CalendarLinks
    instanceId: str
    guestListConfig: GuestListConfig
    userId: str
    onlineConferencing: OnlineConferencing
    categories: List[Any]  # Could be more specific if structure known
    eventDisplaySettings: EventDisplaySettings
    labellingSettings: LabellingSettings
    publishedDate: str
    badges: List[Any]  # Could be more specific if structure known
    members: List[Any]  # Could be more specific if structure known


@dataclass
class EventDateInfo:
    """Event date and time formatting information."""

    utcOffset: int
    startDateISOFormatNotUTC: str
    endDateISOFormatNotUTC: str
    monthDay: str
    weekDay: str
    month: str
    fullDate: str
    shortStartDate: str
    startDate: str
    startTime: str
    daysLeft: int
    day: str
    year: str
    yearMonth: str


@dataclass
class EventDates:
    """Collection of event date information."""

    events: Dict[str, EventDateInfo]


@dataclass
class WixEventsResponse:
    """Complete Wix Events API response structure."""

    events: List[WixEvent]
    dates: EventDates
    hasMore: bool
    total: int
