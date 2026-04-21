import json
from dataclasses import dataclass, field, replace
from typing import Any, Optional
from urllib.parse import urlparse

from psycopg2.extras import DictRow

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.protocols.database_entity import DatabaseEntity


@dataclass
class ScrapingSource:
    """Per-club scraping configuration loaded from scraping_sources."""

    platform: str
    scraper_key: str
    source_url: Optional[str] = None
    external_id: Optional[str] = None
    priority: int = 0
    enabled: bool = True
    metadata: JSONDict = field(default_factory=dict)
    id: Optional[int] = None
    club_id: Optional[int] = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ScrapingSource":
        metadata = raw.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}

        return cls(
            id=raw.get("id"),
            club_id=raw.get("club_id"),
            platform=(raw.get("platform") or "custom"),
            scraper_key=(raw.get("scraper_key") or ""),
            source_url=raw.get("source_url"),
            external_id=raw.get("external_id"),
            priority=int(raw.get("priority") or 0),
            enabled=bool(raw.get("enabled", True)),
            metadata=metadata,
        )


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
    popularity: int
    zip_code: str
    phone_number: str
    visible: bool
    timezone: str = "America/New_York"
    city: Optional[str] = None
    state: Optional[str] = None
    status: str = "active"
    club_type: str = "club"
    rate_limit: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    scraping_sources: list[ScrapingSource] = field(default_factory=list)
    active_scraping_source: Optional[ScrapingSource] = None

    @property
    def primary_scraping_source(self) -> Optional[ScrapingSource]:
        enabled_sources = [source for source in self.scraping_sources if source.enabled]
        if not enabled_sources:
            return None
        return sorted(enabled_sources, key=lambda source: (source.priority, source.id or 0))[0]

    @property
    def scraping_source(self) -> Optional[ScrapingSource]:
        return self.active_scraping_source or self.primary_scraping_source

    def activate_scraping_source(self, source: ScrapingSource) -> None:
        self.active_scraping_source = source

    @property
    def scraper(self) -> Optional[str]:
        source = self.scraping_source
        return source.scraper_key if source else None

    @scraper.setter
    def scraper(self, value: Optional[str]) -> None:
        current = self.scraping_source or ScrapingSource(platform="custom", scraper_key=value or "")
        self.active_scraping_source = replace(
            current,
            scraper_key=value or "",
            platform=current.platform or "custom",
        )

    @property
    def scraping_url(self) -> str:
        source = self.scraping_source
        return source.source_url or "" if source else ""

    @scraping_url.setter
    def scraping_url(self, value: str) -> None:
        current = self.scraping_source or ScrapingSource(platform="custom", scraper_key=self.scraper or "")
        self.active_scraping_source = replace(current, source_url=value)

    @property
    def source_metadata(self) -> JSONDict:
        source = self.scraping_source
        return source.metadata if source else {}

    def metadata_value(self, key: str) -> Optional[str]:
        value = self.source_metadata.get(key)
        return str(value) if value is not None else None

    def external_id_for_platform(self, *platforms: str) -> Optional[str]:
        source = self.scraping_source
        if source and source.platform in platforms:
            return source.external_id
        return None

    @property
    def eventbrite_id(self) -> Optional[str]:
        return self.external_id_for_platform("eventbrite")

    @property
    def ticketmaster_id(self) -> Optional[str]:
        return self.external_id_for_platform("ticketmaster")

    @property
    def seatengine_id(self) -> Optional[str]:
        return self.external_id_for_platform("seatengine", "seatengine_v3")

    @property
    def ovationtix_client_id(self) -> Optional[str]:
        return self.external_id_for_platform("ovationtix")

    @property
    def wix_comp_id(self) -> Optional[str]:
        return self.external_id_for_platform("wix_events")

    @property
    def wix_category_id(self) -> Optional[str]:
        return self.metadata_value("category_id")

    @property
    def squadup_user_id(self) -> Optional[str]:
        return self.external_id_for_platform("squadup")

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
        raw_sources = row.get("scraping_sources") or []
        if isinstance(raw_sources, str):
            try:
                raw_sources = json.loads(raw_sources)
            except json.JSONDecodeError:
                raw_sources = []

        scraping_sources = [
            ScrapingSource.from_dict(source)
            for source in raw_sources
            if isinstance(source, dict)
        ]

        return cls(
            id=row["id"],  # Required field, use direct access
            name=row.get("name", ""),
            address=row.get("address", ""),
            website=row.get("website", ""),
            popularity=row.get("popularity", 0),
            zip_code=row.get("zip_code", ""),
            phone_number=row.get("phone_number", ""),
            timezone=row.get("timezone", "America/New_York"),
            city=row.get("city"),
            state=row.get("state"),
            visible=row.get("visible", True),
            status=row.get("status", "active"),
            club_type=row.get("club_type", "club"),
            rate_limit=row.get("rate_limit", 1.0),
            max_retries=row.get("max_retries", 3),
            timeout=row.get("timeout", 30),
            scraping_sources=scraping_sources,
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
            self.max_retries,
            self.rate_limit,
            self.timeout,
            self.city,
            self.state,
        )

    def to_unique_key(self) -> tuple:
        """Generate a unique key for the Club entity."""
        return (self.name, self.scraping_url)
