"""
Identifies ticketing platforms from ticket purchase URLs.

Maps domains to known ticketing platform names for venue discovery reporting.
"""

import re
from typing import Optional
from urllib.parse import urlparse


# Domain-to-platform mapping. Order doesn't matter — lookup is dict-based.
_PLATFORM_DOMAINS: dict[str, str] = {
    "eventbrite.com": "eventbrite",
    "www.eventbrite.com": "eventbrite",
    "ticketmaster.com": "ticketmaster",
    "www.ticketmaster.com": "ticketmaster",
    "dice.fm": "dice",
    "link.dice.fm": "dice",
    "seated.com": "seated",
    "www.seated.com": "seated",
    "seatengine.com": "seatengine",
    "www.seatengine.com": "seatengine",
    "showclix.com": "showclix",
    "www.showclix.com": "showclix",
    "tixr.com": "tixr",
    "www.tixr.com": "tixr",
    "prekindle.com": "prekindle",
    "www.prekindle.com": "prekindle",
    "humanitix.com": "humanitix",
    "events.humanitix.com": "humanitix",
    "ticketsource.us": "ticketsource",
    "www.ticketsource.us": "ticketsource",
    "ticketsource.co.uk": "ticketsource",
    "www.ticketsource.co.uk": "ticketsource",
    "axs.com": "axs",
    "www.axs.com": "axs",
    "seetickets.us": "seetickets",
    "www.seetickets.us": "seetickets",
    "ticketweb.com": "ticketweb",
    "www.ticketweb.com": "ticketweb",
    "etix.com": "etix",
    "www.etix.com": "etix",
    "universe.com": "universe",
    "www.universe.com": "universe",
    "simpletix.com": "simpletix",
    "www.simpletix.com": "simpletix",
    "headliner.io": "headliner",
    "www.headliner.io": "headliner",
    "ticketplate.com": "ticketplate",
    "www.ticketplate.com": "ticketplate",
    "venuepilot.co": "venuepilot",
    "www.venuepilot.co": "venuepilot",
    "ovationtix.com": "ovationtix",
    "web.ovationtix.com": "ovationtix",
    "ci.ovationtix.com": "ovationtix",
    "freshtix.com": "freshtix",
    "www.freshtix.com": "freshtix",
    "crowdwork.com": "crowdwork",
    "www.crowdwork.com": "crowdwork",
    "opendate.io": "opendate",
    "www.opendate.io": "opendate",
}

# Patterns that match subdomains (e.g., venue.seatengine.com)
_SUBDOMAIN_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\.seatengine\.com$", re.IGNORECASE), "seatengine"),
    (re.compile(r"\.ovationtix\.com$", re.IGNORECASE), "ovationtix"),
    (re.compile(r"\.eventbrite\.com$", re.IGNORECASE), "eventbrite"),
]


def detect_platform(url: str) -> Optional[str]:
    """Return the ticketing platform name for a URL, or None if unknown."""
    if not url:
        return None

    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
    except Exception:
        return None

    # Direct domain lookup
    platform = _PLATFORM_DOMAINS.get(netloc)
    if platform:
        return platform

    # Subdomain pattern matching
    for pattern, name in _SUBDOMAIN_PATTERNS:
        if pattern.search(netloc):
            return name

    return None
