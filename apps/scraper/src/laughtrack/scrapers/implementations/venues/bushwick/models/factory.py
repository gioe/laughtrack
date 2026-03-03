"""
Factory utilities for creating Wix response dataclasses from JSON API responses.

This module provides functions to parse the complex nested JSON structure returned
by Bushwick Comedy Club's Wix Events API into typed dataclasses.
"""

from typing import Any, Dict

from .wix_response import (
    CalendarLinks,
    ConfirmationMessage,
    ConfirmationMessages,
    Coordinates,
    EventDateInfo,
    EventDates,
    EventDisplaySettings,
    FullAddress,
    Geocode,
    GuestListConfig,
    LabellingSettings,
    Location,
    MainImage,
    NegativeMessage,
    OnlineConferencing,
    Recurrences,
    Registration,
    RsvpCollection,
    RsvpConfig,
    Scheduling,
    SchedulingConfig,
    StreetAddress,
    Subdivision,
    TaxConfig,
    TicketConfirmationMessages,
    Ticketing,
    TicketingConfig,
    TicketPrice,
    WaitlistMessage,
    WixEvent,
    WixEventsResponse,
)


class WixResponseFactory:
    """Factory for creating Wix dataclass objects from JSON API responses."""

    @staticmethod
    def create_street_address(data: Dict[str, Any]) -> StreetAddress:
        """Create StreetAddress from JSON data."""
        return StreetAddress(number=data.get("number", ""), name=data.get("name", ""), apt=data.get("apt", ""))

    @staticmethod
    def create_geocode(data: Dict[str, Any]) -> Geocode:
        """Create Geocode from JSON data."""
        return Geocode(latitude=data.get("latitude", 0.0), longitude=data.get("longitude", 0.0))

    @staticmethod
    def create_subdivision(data: Dict[str, Any]) -> Subdivision:
        """Create Subdivision from JSON data."""
        return Subdivision(code=data.get("code", ""), name=data.get("name", ""), type=data.get("type", 0))

    @staticmethod
    def create_full_address(data: Dict[str, Any]) -> FullAddress:
        """Create FullAddress from JSON data."""
        return FullAddress(
            country=data.get("country", ""),
            subdivision=data.get("subdivision", ""),
            city=data.get("city", ""),
            postalCode=data.get("postalCode", ""),
            streetAddress=WixResponseFactory.create_street_address(data.get("streetAddress", {})),
            formattedAddress=data.get("formattedAddress", ""),
            geocode=WixResponseFactory.create_geocode(data.get("geocode", {})),
            countryFullname=data.get("countryFullname", ""),
            subdivisions=[WixResponseFactory.create_subdivision(sub) for sub in data.get("subdivisions", [])],
        )

    @staticmethod
    def create_coordinates(data: Dict[str, Any]) -> Coordinates:
        """Create Coordinates from JSON data."""
        return Coordinates(lat=data.get("lat", 0.0), lng=data.get("lng", 0.0))

    @staticmethod
    def create_location(data: Dict[str, Any]) -> Location:
        """Create Location from JSON data."""
        return Location(
            name=data.get("name", ""),
            coordinates=WixResponseFactory.create_coordinates(data.get("coordinates", {})),
            address=data.get("address", ""),
            type=data.get("type", 0),
            fullAddress=WixResponseFactory.create_full_address(data.get("fullAddress", {})),
            tbd=data.get("tbd", False),
        )

    @staticmethod
    def create_recurrences(data: Dict[str, Any]) -> Recurrences:
        """Create Recurrences from JSON data."""
        return Recurrences(
            occurrences=data.get("occurrences", []), categoryId=data.get("categoryId", ""), status=data.get("status", 0)
        )

    @staticmethod
    def create_scheduling_config(data: Dict[str, Any]) -> SchedulingConfig:
        """Create SchedulingConfig from JSON data."""
        return SchedulingConfig(
            scheduleTbd=data.get("scheduleTbd", False),
            startDate=data.get("startDate", ""),
            endDate=data.get("endDate", ""),
            timeZoneId=data.get("timeZoneId", ""),
            endDateHidden=data.get("endDateHidden", False),
            showTimeZone=data.get("showTimeZone", False),
            recurrences=WixResponseFactory.create_recurrences(data.get("recurrences", {})),
        )

    @staticmethod
    def create_scheduling(data: Dict[str, Any]) -> Scheduling:
        """Create Scheduling from JSON data."""
        return Scheduling(
            config=WixResponseFactory.create_scheduling_config(data.get("config", {})),
            formatted=data.get("formatted", ""),
            startDateFormatted=data.get("startDateFormatted", ""),
            startTimeFormatted=data.get("startTimeFormatted", ""),
            endDateFormatted=data.get("endDateFormatted", ""),
            endTimeFormatted=data.get("endTimeFormatted", ""),
        )

    @staticmethod
    def create_main_image(data: Dict[str, Any]) -> MainImage:
        """Create MainImage from JSON data."""
        return MainImage(
            id=data.get("id", ""), url=data.get("url", ""), height=data.get("height", 0), width=data.get("width", 0)
        )

    @staticmethod
    def create_confirmation_message(data: Dict[str, Any]) -> ConfirmationMessage:
        """Create ConfirmationMessage from JSON data."""
        return ConfirmationMessage(
            title=data.get("title", ""),
            message=data.get("message", ""),
            addToCalendarActionLabel=data.get("addToCalendarActionLabel", ""),
            shareActionLabel=data.get("shareActionLabel", ""),
        )

    @staticmethod
    def create_waitlist_message(data: Dict[str, Any]) -> WaitlistMessage:
        """Create WaitlistMessage from JSON data."""
        return WaitlistMessage(
            title=data.get("title", ""),
            message=data.get("message", ""),
            addToCalendarActionLabel=data.get("addToCalendarActionLabel", ""),
            shareActionLabel=data.get("shareActionLabel", ""),
        )

    @staticmethod
    def create_negative_message(data: Dict[str, Any]) -> NegativeMessage:
        """Create NegativeMessage from JSON data."""
        return NegativeMessage(title=data.get("title", ""), shareActionLabel=data.get("shareActionLabel", ""))

    @staticmethod
    def create_confirmation_messages(data: Dict[str, Any]) -> ConfirmationMessages:
        """Create ConfirmationMessages from JSON data."""
        return ConfirmationMessages(
            positiveConfirmation=WixResponseFactory.create_confirmation_message(data.get("positiveConfirmation", {})),
            waitlistMessages=WixResponseFactory.create_waitlist_message(data.get("waitlistMessages", {})),
            negativeMessages=WixResponseFactory.create_negative_message(data.get("negativeMessages", {})),
        )

    @staticmethod
    def create_rsvp_config(data: Dict[str, Any]) -> RsvpConfig:
        """Create RsvpConfig from JSON data."""
        return RsvpConfig(
            rsvpStatusOptions=data.get("rsvpStatusOptions", 0),
            waitlist=data.get("waitlist", False),
            confirmationMessages=WixResponseFactory.create_confirmation_messages(data.get("confirmationMessages", {})),
        )

    @staticmethod
    def create_rsvp_collection(data: Dict[str, Any]) -> RsvpCollection:
        """Create RsvpCollection from JSON data."""
        return RsvpCollection(config=WixResponseFactory.create_rsvp_config(data.get("config", {})))

    @staticmethod
    def create_tax_config(data: Dict[str, Any]) -> TaxConfig:
        """Create TaxConfig from JSON data."""
        return TaxConfig(
            type=data.get("type", 0),
            name=data.get("name", ""),
            rate=data.get("rate", ""),
            appliesToDonations=data.get("appliesToDonations", False),
        )

    @staticmethod
    def create_ticket_confirmation_messages(data: Dict[str, Any]) -> TicketConfirmationMessages:
        """Create TicketConfirmationMessages from JSON data."""
        return TicketConfirmationMessages(
            title=data.get("title", ""),
            message=data.get("message", ""),
            downloadTicketsLabel=data.get("downloadTicketsLabel", ""),
            addToCalendarActionLabel=data.get("addToCalendarActionLabel", ""),
            shareActionLabel=data.get("shareActionLabel", ""),
        )

    @staticmethod
    def create_ticketing_config(data: Dict[str, Any]) -> TicketingConfig:
        """Create TicketingConfig from JSON data."""
        return TicketingConfig(
            guestAssignedTickets=data.get("guestAssignedTickets", False),
            taxConfig=WixResponseFactory.create_tax_config(data.get("taxConfig", {})),
            ticketLimitPerOrder=data.get("ticketLimitPerOrder", 0),
            reservationDurationInMinutes=data.get("reservationDurationInMinutes", 0),
            gracePeriodInMinutes=data.get("gracePeriodInMinutes", 0),
            confirmationMessages=WixResponseFactory.create_ticket_confirmation_messages(
                data.get("confirmationMessages", {})
            ),
        )

    @staticmethod
    def create_ticket_price(data: Dict[str, Any]) -> TicketPrice:
        """Create TicketPrice from JSON data."""
        return TicketPrice(
            amount=data.get("amount", ""), currency=data.get("currency", ""), value=data.get("value", "")
        )

    @staticmethod
    def create_ticketing(data: Dict[str, Any]) -> Ticketing:
        """Create Ticketing from JSON data."""
        return Ticketing(
            lowestPrice=data.get("lowestPrice", ""),
            highestPrice=data.get("highestPrice", ""),
            currency=data.get("currency", ""),
            config=WixResponseFactory.create_ticketing_config(data.get("config", {})),
            lowestTicketPrice=WixResponseFactory.create_ticket_price(data.get("lowestTicketPrice", {})),
            highestTicketPrice=WixResponseFactory.create_ticket_price(data.get("highestTicketPrice", {})),
            lowestTicketPriceFormatted=data.get("lowestTicketPriceFormatted", ""),
            highestTicketPriceFormatted=data.get("highestTicketPriceFormatted", ""),
            soldOut=data.get("soldOut", False),
        )

    @staticmethod
    def create_registration(data: Dict[str, Any]) -> Registration:
        """Create Registration from JSON data."""
        return Registration(
            type=data.get("type", 0),
            status=data.get("status", 0),
            rsvpCollection=WixResponseFactory.create_rsvp_collection(data.get("rsvpCollection", {})),
            ticketing=WixResponseFactory.create_ticketing(data.get("ticketing", {})),
            restrictedTo=data.get("restrictedTo", 0),
            initialType=data.get("initialType", 0),
        )

    @staticmethod
    def create_calendar_links(data: Dict[str, Any]) -> CalendarLinks:
        """Create CalendarLinks from JSON data."""
        return CalendarLinks(google=data.get("google", ""), ics=data.get("ics", ""))

    @staticmethod
    def create_guest_list_config(data: Dict[str, Any]) -> GuestListConfig:
        """Create GuestListConfig from JSON data."""
        return GuestListConfig(publicGuestList=data.get("publicGuestList", False))

    @staticmethod
    def create_online_conferencing(data: Dict[str, Any]) -> OnlineConferencing:
        """Create OnlineConferencing from JSON data."""
        return OnlineConferencing(providerName=data.get("providerName", ""))

    @staticmethod
    def create_event_display_settings(data: Dict[str, Any]) -> EventDisplaySettings:
        """Create EventDisplaySettings from JSON data."""
        return EventDisplaySettings()

    @staticmethod
    def create_labelling_settings(data: Dict[str, Any]) -> LabellingSettings:
        """Create LabellingSettings from JSON data."""
        return LabellingSettings(assignedContactsLabelDeleted=data.get("assignedContactsLabelDeleted", False))

    @staticmethod
    def create_wix_event(data: Dict[str, Any]) -> WixEvent:
        """Create WixEvent from JSON data."""
        return WixEvent(
            id=data.get("id", ""),
            location=WixResponseFactory.create_location(data.get("location", {})),
            scheduling=WixResponseFactory.create_scheduling(data.get("scheduling", {})),
            title=data.get("title", ""),
            description=data.get("description", ""),
            about=data.get("about", ""),
            mainImage=WixResponseFactory.create_main_image(data.get("mainImage", {})),
            slug=data.get("slug", ""),
            language=data.get("language", ""),
            created=data.get("created", ""),
            modified=data.get("modified", ""),
            status=data.get("status", 0),
            registration=WixResponseFactory.create_registration(data.get("registration", {})),
            calendarLinks=WixResponseFactory.create_calendar_links(data.get("calendarLinks", {})),
            instanceId=data.get("instanceId", ""),
            guestListConfig=WixResponseFactory.create_guest_list_config(data.get("guestListConfig", {})),
            userId=data.get("userId", ""),
            onlineConferencing=WixResponseFactory.create_online_conferencing(data.get("onlineConferencing", {})),
            categories=data.get("categories", []),
            eventDisplaySettings=WixResponseFactory.create_event_display_settings(data.get("eventDisplaySettings", {})),
            labellingSettings=WixResponseFactory.create_labelling_settings(data.get("labellingSettings", {})),
            publishedDate=data.get("publishedDate", ""),
            badges=data.get("badges", []),
            members=data.get("members", []),
        )

    @staticmethod
    def create_event_date_info(data: Dict[str, Any]) -> EventDateInfo:
        """Create EventDateInfo from JSON data."""
        return EventDateInfo(
            utcOffset=data.get("utcOffset", 0),
            startDateISOFormatNotUTC=data.get("startDateISOFormatNotUTC", ""),
            endDateISOFormatNotUTC=data.get("endDateISOFormatNotUTC", ""),
            monthDay=data.get("monthDay", ""),
            weekDay=data.get("weekDay", ""),
            month=data.get("month", ""),
            fullDate=data.get("fullDate", ""),
            shortStartDate=data.get("shortStartDate", ""),
            startDate=data.get("startDate", ""),
            startTime=data.get("startTime", ""),
            daysLeft=data.get("daysLeft", 0),
            day=data.get("day", ""),
            year=data.get("year", ""),
            yearMonth=data.get("yearMonth", ""),
        )

    @staticmethod
    def create_event_dates(data: Dict[str, Any]) -> EventDates:
        """Create EventDates from JSON data."""
        events_data = data.get("events", {})
        events = {
            event_id: WixResponseFactory.create_event_date_info(event_info)
            for event_id, event_info in events_data.items()
        }
        return EventDates(events=events)

    @staticmethod
    def create_wix_events_response(data: Dict[str, Any]) -> WixEventsResponse:
        """Create WixEventsResponse from JSON data."""
        events = [WixResponseFactory.create_wix_event(event_data) for event_data in data.get("events", [])]
        return WixEventsResponse(
            events=events,
            dates=WixResponseFactory.create_event_dates(data.get("dates", {})),
            hasMore=data.get("hasMore", False),
            total=data.get("total", 0),
        )
