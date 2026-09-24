"""Timezone lookup utilities for US venue addresses."""

import re

from pytz import country_names
from typing import Optional

# US state abbreviation → IANA timezone.
# For states spanning multiple time zones, the most-populated zone is used.
_STATE_TO_TIMEZONE: dict[str, str] = {
    "AL": "America/Chicago",
    "AK": "America/Anchorage",
    "AZ": "America/Phoenix",
    "AR": "America/Chicago",
    "CA": "America/Los_Angeles",
    "CO": "America/Denver",
    "CT": "America/New_York",
    "DC": "America/New_York",
    "DE": "America/New_York",
    "FL": "America/New_York",
    "GA": "America/New_York",
    "HI": "Pacific/Honolulu",
    "ID": "America/Boise",
    "IL": "America/Chicago",
    "IN": "America/Indiana/Indianapolis",
    "IA": "America/Chicago",
    "KS": "America/Chicago",
    "KY": "America/New_York",
    "LA": "America/Chicago",
    "ME": "America/New_York",
    "MD": "America/New_York",
    "MA": "America/New_York",
    "MI": "America/Detroit",
    "MN": "America/Chicago",
    "MS": "America/Chicago",
    "MO": "America/Chicago",
    "MT": "America/Denver",
    "NE": "America/Chicago",
    "NV": "America/Los_Angeles",
    "NH": "America/New_York",
    "NJ": "America/New_York",
    "NM": "America/Denver",
    "NY": "America/New_York",
    "NC": "America/New_York",
    "ND": "America/Chicago",
    "OH": "America/New_York",
    "OK": "America/Chicago",
    "OR": "America/Los_Angeles",
    "PA": "America/New_York",
    "RI": "America/New_York",
    "SC": "America/New_York",
    "SD": "America/Chicago",
    "TN": "America/Chicago",
    "TX": "America/Chicago",
    "UT": "America/Denver",
    "VT": "America/New_York",
    "VA": "America/New_York",
    "WA": "America/Los_Angeles",
    "WV": "America/New_York",
    "WI": "America/Chicago",
    "WY": "America/Denver",
    # Territories
    "PR": "America/Puerto_Rico",
    "VI": "America/St_Thomas",
    "GU": "Pacific/Guam",
    "AS": "Pacific/Pago_Pago",
    "MP": "Pacific/Saipan",
}


def timezone_from_state(state_code: str) -> Optional[str]:
    """Return IANA timezone for a US state abbreviation, or None if unknown."""
    if not state_code:
        return None
    return _STATE_TO_TIMEZONE.get(state_code.strip().upper())


def _split_address_parts(address: str) -> list[str]:
    """Split a comma-separated address into stripped, non-empty parts."""
    return [p.strip() for p in address.split(",") if p.strip()]


def _extract_state_code(candidate: str) -> Optional[str]:
    """
    Extract a two-letter US state code from the last address segment.

    Accepts "NY" or "NY 10001" (with optional ZIP). Returns the uppercased
    state abbreviation if it exists in _STATE_TO_TIMEZONE, else None.
    """
    m = re.match(r"^([A-Za-z]{2})(?:\s+\d{5}(?:-\d{4})?)?$", candidate)
    if m:
        code = m.group(1).upper()
        return code if code in _STATE_TO_TIMEZONE else None
    return None


def _looks_like_non_city_segment(candidate: str) -> bool:
    """Return True when an address segment is clearly not a city name."""
    if not candidate:
        return True
    # Tour-list fragments such as "‘26 Chicago" and "May 17 '26 Dallas"
    # are event date remnants, not city names. They should not be persisted
    # as clubs.city just because the following comma segment is a valid state.
    return any(ch.isdigit() for ch in candidate)


def parse_city_state_from_address(address: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Parse city and state from a comma-separated US address string.

    Expects format: "Street, City, State" or "Street, City, State ZIP"
    Returns (city, state) tuple; either may be None if unparseable.

    Supported codes: all 50 US states + DC, and the territories PR, VI, GU,
    AS, and MP. The UM (U.S. Minor Outlying Islands) code is not supported
    because those islands span multiple timezones with no single IANA mapping.
    """
    if not address:
        return None, None
    parts = _split_address_parts(address)
    if len(parts) < 2:
        return None, None
    suffix = parts[-1].upper()
    if suffix in {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"}:
        parts.pop()
    else:
        foreign_names = {name.upper() for code, name in country_names.items() if code != "US"}
        foreign_codes = set(country_names) - set(_STATE_TO_TIMEZONE) - {"US"}
        foreign_names.update({"CANADA", "UK", "UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES"})
        canadian_suffix = suffix == "CA" and _CANADIAN_POSTAL.search(", ".join(parts[:-1]))
        if suffix in foreign_names or suffix in foreign_codes or canadian_suffix:
            return None, None
    if parts and re.fullmatch(r"\d{5}(?:-\d{4})?", parts[-1]):
        parts.pop()
    if len(parts) < 2:
        return None, None

    def region_code(part: str) -> Optional[str]:
        region = re.sub(r"\s+\d{5}(?:-\d{4})?$", "", part).upper()
        return _extract_state_code(_US_STATE_NAMES.get(region, region))

    state = region_code(parts[-1])
    # JSON-LD can repeat a full state + ZIP with its abbreviated region.
    # Do not strip a same-named city such as New York merely for matching NY.
    while state and len(parts) > 2 and region_code(parts[-2]) == state:
        previous = parts[-2]
        if not re.search(r"\d", previous) and previous.upper() != state:
            break
        parts.pop()
    city = parts[-2] or None
    if city and _looks_like_non_city_segment(city):
        city = None
    return city, state


def timezone_from_address(address: Optional[str]) -> Optional[str]:
    """
    Infer IANA timezone from a venue address string.

    Expects the address to end with a US state abbreviation as the last
    comma-separated segment, e.g. "123 Main St, New York, NY".

    Returns:
        IANA timezone string, or None if the state cannot be determined.
    """
    if not address:
        return None
    parts = _split_address_parts(address)
    if not parts:
        return None
    state = _extract_state_code(parts[-1])
    return timezone_from_state(state) if state else None


# Central enrichment must not turn a state's majority zone into venue evidence.
# Keep the legacy helpers above stable for their existing scraper callers.
_SPLIT_ZONE_STATES = frozenset("AK AZ FL ID IN KS KY MI NE NV ND OR SD TN TX".split())
_US_STATE_NAMES = dict(
    zip(
        "Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|District of Columbia|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming".upper().split(
            "|"
        ),
        "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split(),
    )
)
_CANADIAN_PROVINCE_ZONES = {
    "AB": "America/Edmonton",
    "NB": "America/Moncton",
    "NS": "America/Halifax",
    "PE": "America/Halifax",
}
_CANADIAN_POSTAL = re.compile(
    r"(?:^|,)\s*([A-Z]{2})\s+([ABCEGHJKLMNPRSTVXY]\d[A-Z]\s?\d[A-Z]\d)$",
    re.I,
)


def timezone_from_evidence(
    state: Optional[str],
    address: Optional[str],
    country: Optional[str] = None,
) -> tuple[str, Optional[str]]:
    """Resolve only unambiguous region evidence, returning (source, IANA zone).

    Full state names, separate ZIP segments, US country suffixes and trailing
    suite notes occur in aggregate venue payloads. Canadian postal evidence is
    accepted only for single-zone provinces. Unknown countries, split-zone
    regions, and contradictory fields remain unresolved for manual review.
    No city/name search, coordinate guessing, or majority-zone default is used.
    """
    unresolved = ("unresolved", None)
    country_code = (country or "").strip().upper()
    aliases = {"USA": "US", "UNITED STATES": "US", "UNITED STATES OF AMERICA": "US", "CANADA": "CA"}
    country_code = aliases.get(country_code, country_code)
    if country_code and country_code not in {"US", "CA"}:
        return unresolved

    text = (address or "").strip().rstrip(",").strip()
    # Only discard parenthesized notes after a ZIP, never arbitrary location text.
    text = re.sub(r"(\d{5}(?:-\d{4})?)\s*\([^()]*\)$", r"\1", text).strip()
    suffix = re.search(r",\s*(USA|US|United States(?: of America)?|Canada|CA)$", text, re.I)
    if suffix and suffix.group(1).upper() == "CA":
        # JSON-LD emits CA for Canada, but it also denotes California in US
        # addresses. Only Canadian province/postal evidence disambiguates it.
        if not _CANADIAN_POSTAL.search(text[: suffix.start()].rstrip(", ")):
            suffix = None
    if suffix:
        suffix_country = aliases.get(suffix.group(1).upper(), suffix.group(1).upper())
        if country_code and suffix_country != country_code:
            return unresolved
        country_code = suffix_country
        text = text[: suffix.start()].rstrip(", ")

    # An explicit foreign country suffix must not lose to a US state field.
    # Country names come from the existing pytz dependency; codes that overlap
    # US states (e.g. CA) are deliberately not treated as country suffixes.
    foreign_names = {name.upper() for code, name in country_names.items() if code not in {"US", "CA"}}
    foreign_names.update({"UK", "UNITED KINGDOM", "GB", "AU", "NZ", "IE", "ENGLAND", "SCOTLAND", "WALES"})
    if text.rsplit(",", 1)[-1].strip().upper() in foreign_names:
        return unresolved

    normalized_state = (state or "").strip().upper()
    normalized_state = _US_STATE_NAMES.get(normalized_state, normalized_state)
    canadian = _CANADIAN_POSTAL.search(text)
    if canadian:
        province = canadian.group(1).upper()
        if country_code == "US" or (normalized_state and normalized_state != province):
            return unresolved
        prefix = {"AB": "T", "NB": "E", "NS": "B", "PE": "C"}.get(province)
        if prefix is None or not canadian.group(2).upper().startswith(prefix):
            return unresolved
        tz = _CANADIAN_PROVINCE_ZONES.get(province)
        return ("address", tz) if tz else unresolved
    # Canadian region codes alone do not establish the venue's location.
    if country_code == "CA":
        return unresolved

    parts = _split_address_parts(text)
    if parts and re.fullmatch(r"\d{5}(?:-\d{4})?", parts[-1]):
        parts.pop()
    address_state = None
    if parts:
        region = re.sub(r"\s+\d{5}(?:-\d{4})?$", "", parts[-1]).upper()
        region = _US_STATE_NAMES.get(region, region)
        if region in _STATE_TO_TIMEZONE:
            address_state = region
    if normalized_state and address_state and normalized_state != address_state:
        return unresolved
    # Do not fall back from an explicitly supplied unknown region to an address.
    if normalized_state and normalized_state not in _STATE_TO_TIMEZONE:
        return unresolved
    region = normalized_state or address_state
    if not region or region in _SPLIT_ZONE_STATES:
        return unresolved
    tz = timezone_from_state(region)
    return ("state" if normalized_state else "address", tz) if tz else unresolved
