"""Base headers configuration for scrapers and API clients."""

from typing import Optional
from urllib.parse import urlparse


class BaseHeaders:
    """Base headers that are common across scrapers and API clients."""

    # Common headers shared across all clients
    COMMON_HEADERS = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    }

    # Desktop browser headers (macOS Chrome)
    DESKTOP_BROWSER_HEADERS = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    }

    # Mobile browser headers (Android Chrome)
    MOBILE_BROWSER_HEADERS = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    # Specialized header templates for different contexts
    HEADER_TEMPLATES = {
        "json": {"Content-Type": "application/json"},
        "form": {
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
        "graphql": {
            "Content-Type": "application/json; charset=UTF-8",
            "x-amz-user-agent": "aws-amplify/6.13.1 api/1 framework/2",
        },
        "comedy_cellar_lineup": {
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
        "comedy_cellar_shows": {
            "content-type": "application/json",
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        },
        "rodneys": {
            "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "sec-fetch-site": "none",
            "sec-fetch-mode": "navigate",
            "sec-fetch-user": "?1",
            "sec-fetch-dest": "document",
        },
        "wix_api": {
            "x-wix-brand": "wix",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        },
    }

    # Authentication headers for different services
    AUTH_HEADERS = {
        "eventbrite": lambda token: {"Authorization": f"Bearer {token}"},
        "live_nation": lambda token: {"x-api-key": token},
        "seat_engine": lambda token: {"x-auth-token": token},
    }

    # Legacy cookie string for backward compatibility
    LEGACY_COOKIE = "queryParams={}; allow_functional_cookies=1; allow_analytics_cookies=1; allow_marketing_cookies=1; _ga=GA1.1.1829206343.1732242248; tsession=MTI1ZWIwNzktZGE5NS00MDQ2LTkwM2QtYzcwNWY4NmIwYzBm; ULIN=1; _ga_429HYMWZX6=GS1.1.1734656591.5.1.1734658245.19.0.0; _ga_0YPZ42JS0T=GS1.1.1734656592.5.1.1734658245.0.0.0; datadome=1flA_0RXJQKi3OSMf6X6z2bE~op0mWOJIBeMvXzo_jSm_QkDOCltK4gyf7Ot4TBKWMasuq9hOAXFgiTf7Qlv1P3qAJlh1bZ4USP2mwKeJaxow3~ld5M4jV52~qAyOa9C; datadome=99YpGRgAeh5QVmWH19yj~2Ch5nhNjam9bb1G0bkOaTAfxDry3yE5xNXynU9ywc8ZRvXNEtjhfNYhqDtaNGW1w9u9ZDS770lawgqoixJS4qfvOOusNeTinw2ELqPlu26t"

    # Venue type to header type mapping
    VENUE_MAPPINGS = {
        "comedy_cellar_lineup": "comedy_cellar_lineup",
        "comedy_cellar_shows": "comedy_cellar_shows",
        "rodneys": "rodneys",
        "improv": "mobile_browser",
        "grove34": "desktop_browser",
        "standup_ny": "graphql",
        "bushwick": "wix_api",
        "gotham": "common",  # Use common headers for Gotham S3 API calls
    }

    @classmethod
    def get_headers(
        cls,
        base_type: str = "common",
        auth_type: Optional[str] = None,
        auth_token: Optional[str] = None,
        include_cookies: bool = False,
        domain: Optional[str] = None,
        referer: Optional[str] = None,
        host: Optional[str] = None,
        origin: Optional[str] = None,
        cookies: Optional[str] = None,
        **additional_headers,
    ) -> dict:
        """
        Get headers with optional additional headers and authentication.

        Args:
            base_type: Type of base headers to use:
                      'common', 'json', 'form', 'graphql', 'desktop_browser', 'mobile_browser',
                      'comedy_cellar_lineup', 'comedy_cellar_shows', 'rodneys',
                      'browser' (legacy), 'mobile_browser' (legacy)
            auth_type: Type of authentication to use (e.g., 'eventbrite', 'live_nation', 'seat_engine')
            auth_token: Authentication token to use
            include_cookies: Whether to include cookie headers (only for browser headers)
            domain: Domain to use for origin and referer headers (auto-sets both unless overridden)
            referer: Specific referer URL (overrides domain-based referer)
            host: Specific host header value
            origin: Specific origin URL (overrides domain-based origin)
            cookies: Cookie string to include
            additional_headers: Additional headers to add or override

        Returns:
            Dictionary of headers
        """
        # Normalize base_type for legacy compatibility
        if base_type == "browser":
            base_type = "desktop_browser"

        # Get base headers based on type
        base = {}
        if base_type == "common":
            base = cls.COMMON_HEADERS.copy()
        elif base_type == "desktop_browser":
            base = cls.DESKTOP_BROWSER_HEADERS.copy()
        elif base_type == "mobile_browser":
            base = cls.MOBILE_BROWSER_HEADERS.copy()
        elif base_type in cls.HEADER_TEMPLATES:
            # For specialized types like 'json', 'form', etc.
            # Start with common headers and add template-specific ones
            if base_type == "rodneys":
                # These have full header sets
                base = cls.HEADER_TEMPLATES[base_type].copy()
            elif base_type in ["comedy_cellar_lineup", "comedy_cellar_shows"]:
                # Add accept and other basic headers needed for the complex test
                base = {
                    "accept": "*/*",
                    "accept-language": "en-US,en;q=0.9",
                    "cache-control": "no-cache",
                    "pragma": "no-cache",
                    "priority": "u=1, i",
                    **cls.HEADER_TEMPLATES[base_type],
                }
            else:
                # These need to be combined with common headers
                base = {**cls.COMMON_HEADERS, **cls.HEADER_TEMPLATES[base_type]}
        else:
            # Default to common headers if type not found
            base = cls.COMMON_HEADERS.copy()

        # Add authentication headers if specified
        if auth_type and auth_token and auth_type in cls.AUTH_HEADERS:
            base.update(cls.AUTH_HEADERS[auth_type](auth_token))

        # Add legacy cookies if requested (for backward compatibility)
        if base_type in ["desktop_browser", "browser"] and include_cookies:
            base["cookie"] = cls.LEGACY_COOKIE

        # Add domain-specific headers
        if domain:
            parsed = urlparse(domain if domain.startswith(("http://", "https://")) else f"https://{domain}")
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            base["origin"] = origin or base_url
            base["referer"] = referer or base_url

        # Add specific headers
        if host:
            base["host"] = host
        if origin and not domain:  # Don't override domain-based origin
            base["origin"] = origin
        if referer and not domain:  # Don't override domain-based referer
            base["referer"] = referer
        if cookies:
            base["Cookie"] = cookies

        # Merge additional headers
        if additional_headers:
            base.update(additional_headers)

        return base

    @classmethod
    def get_venue_headers(cls, venue_type: str, **kwargs) -> dict:
        """
        Get headers optimized for specific venue types.

        Args:
            venue_type: Type of venue ('comedy_cellar', 'rodneys', 'improv', 'grove34', etc.)
            **kwargs: Additional arguments passed to get_headers()

        Returns:
            Dictionary of headers optimized for the venue
        """
        base_type = cls.VENUE_MAPPINGS.get(venue_type, "desktop_browser")
        return cls.get_headers(base_type=base_type, **kwargs)
