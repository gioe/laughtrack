from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from psycopg2.extras import DictRow

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.protocols.database_entity import DatabaseEntity


@dataclass
class Club(DatabaseEntity):
    """
    Data model for a comedy club.
    Also serves as configuration for scrapers, containing all necessary metadata.
    """

    id: int
    name: str
    address: str
    website: str
    scraping_url: str
    popularity: int
    zip_code: str
    phone_number: str
    visible: bool
    timezone: str = "America/New_York"
    city: Optional[str] = None
    state: Optional[str] = None
    scraper: Optional[str] = None
    eventbrite_id: Optional[str] = None
    ticketmaster_id: Optional[str] = None
    seatengine_id: Optional[str] = None
    rate_limit: float = 1.0
    max_retries: int = 3
    timeout: int = 30

    @property
    def schema_dir(self) -> str:
        """Derive the schema directory name from the scraping_url.

        The schema directory is derived from the hostname of the scraping_url.
        The full hostname (minus www. prefix) is used to ensure consistency
        and match the actual schema directory structure.

        This handles URLs both with and without schemes:
        - comedycellar.com -> comedycellar.com
        - www.comedycellar.com -> comedycellar.com
        - comedycellar.com/events -> comedycellar.com
        - tickets.venue.com -> tickets.venue.com
        - atlanticcitycomedyclub.com/calendar -> atlanticcitycomedyclub.com

        Returns:
            str: The directory name to use in schema (hostname without www)
        """
        if not self.scraping_url:
            return ""

        # Handle URLs without scheme by adding one temporarily
        url_to_parse = self.scraping_url
        if not url_to_parse.startswith(("http://", "https://")):
            url_to_parse = "https://" + url_to_parse

        parsed = urlparse(url_to_parse)
        hostname = parsed.netloc

        # Handle empty netloc (invalid URLs)
        if not hostname:
            return ""

        # Check if hostname is valid:
        # - Contains at least one dot (domain.com)
        # - Is localhost (special case)
        # - Is an IP address (contains only digits, dots, colons for IPv6)
        import re

        is_ip_pattern = re.match(r"^[\d\.:]+(\:\d+)?$", hostname)  # IPv4 or IPv6 with optional port
        is_localhost = hostname.startswith("localhost")
        has_domain_dot = "." in hostname

        if not (has_domain_dot or is_localhost or is_ip_pattern):
            return ""

        # Remove www. prefix if present
        if hostname.startswith("www."):
            hostname = hostname[4:]

        return hostname

    @classmethod
    def from_db_row(cls, row: DictRow) -> "Club":
        """Create Club entity from database row."""
        return cls(
            id=row["id"],  # Required field, use direct access
            name=row.get("name", ""),
            address=row.get("address", ""),
            website=row.get("website", ""),
            scraping_url=row.get("scraping_url", ""),
            popularity=row.get("popularity", 0),
            zip_code=row.get("zip_code", ""),
            phone_number=row.get("phone_number", ""),
            timezone=row.get("timezone", "America/New_York"),
            city=row.get("city"),
            state=row.get("state"),
            visible=row.get("visible", True),
            scraper=row.get("scraper"),
            eventbrite_id=row.get("eventbrite_id"),
            ticketmaster_id=row.get("ticketmaster_id"),
            seatengine_id=row.get("seatengine_id"),
            rate_limit=row.get("rate_limit", 1.0),
            max_retries=row.get("max_retries", 3),
            timeout=row.get("timeout", 30),
        )

    @property
    def scraping_domain(self) -> str:
        url = self.scraping_url
        if "://" in url:
            url = url.split("://", 1)[1]
        return url.split("/")[0].lower()

    def as_context(self) -> JSONDict:
        """Return a context dictionary for logging or other purposes."""
        return {
            "club_id": self.id,
            "club_name": self.name,
            "scraping_url": self.scraping_url,
            "timezone": self.timezone,
            "popularity": self.popularity,
        }

    @classmethod
    def key_from_db_row(cls, row: DictRow) -> tuple:
        """Create a unique key from a database row."""
        return (row.get("name"), row.get("scraping_url"))

    def to_tuple(self) -> tuple:
        """Transform Club entity to database tuple."""
        return (
            self.name,
            self.address,
            self.website,
            self.scraping_url,
            self.popularity,
            self.zip_code,
            self.phone_number,
            self.timezone,
            self.visible,
            self.scraper,
            self.eventbrite_id,
            self.max_retries,
            self.rate_limit,
            self.seatengine_id,
            self.ticketmaster_id,
            self.timeout,
            self.city,
            self.state,
        )

    def to_unique_key(self) -> tuple:
        """Generate a unique key for the Club entity."""
        return (self.name, self.scraping_url)
