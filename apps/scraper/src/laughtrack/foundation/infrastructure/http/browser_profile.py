"""Coherent browser fingerprint profiles for anti-detection scraping.

Each BrowserProfile bundles a browser version with its matching User-Agent,
sec-ch-ua header, Accept-Language, platform, and curl-cffi impersonation
target so that TLS fingerprint (set by curl-cffi) and HTTP headers always
describe the same browser version.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class BrowserProfile:
    """
    A coherent browser fingerprint profile.

    All fields must describe the same browser version so that the TLS
    fingerprint (selected via ``impersonation_target`` in curl-cffi) and
    HTTP headers are never contradictory.

    Fields:
        browser_version:      curl-cffi impersonation identifier, e.g. ``"chrome124"``.
                              Doubles as the canonical version label for the profile.
        user_agent:           Full User-Agent header value.
        sec_ch_ua:            ``sec-ch-ua`` header value (brand list).
        accept_language:      ``Accept-Language`` header value.
        platform:             OS platform label used for ``sec-ch-ua-platform``
                              (e.g. ``"macOS"``, ``"Windows"``, ``"Android"``).
        impersonation_target: curl-cffi target string passed to ``AsyncSession``.
                              Must match ``browser_version``.
    """

    browser_version: str
    user_agent: str
    sec_ch_ua: str
    accept_language: str
    platform: str
    impersonation_target: str

    @property
    def is_mobile(self) -> bool:
        return self.platform == "Android"

    def to_headers(self) -> dict:
        """Return the browser-identity headers derived from this profile."""
        return {
            "User-Agent": self.user_agent,
            "Accept-Language": self.accept_language,
            "sec-ch-ua": self.sec_ch_ua,
            "sec-ch-ua-mobile": "?1" if self.is_mobile else "?0",
            "sec-ch-ua-platform": f'"{self.platform}"',
        }


# ---------------------------------------------------------------------------
# Built-in profiles
# ---------------------------------------------------------------------------
# Only versions whose impersonation_target is confirmed valid in the
# installed curl-cffi are included.  Using an unsupported target silently
# falls back to plain HTTP/2 without a real browser TLS fingerprint,
# making the TLS fingerprint inconsistent with the HTTP headers.
#
# Confirmed targets in curl-cffi ≤0.7.x:
#   chrome99, chrome100, chrome101, chrome104, chrome107, chrome110,
#   chrome116, chrome119, chrome120, chrome123, chrome124,
#   chrome99_android, safari15_3, safari15_5, safari17_0, safari17_2_ios

BUILTIN_PROFILES: List[BrowserProfile] = [
    BrowserProfile(
        browser_version="chrome124",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
        accept_language="en-US,en;q=0.9",
        platform="macOS",
        impersonation_target="chrome124",
    ),
    BrowserProfile(
        browser_version="chrome124",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
        accept_language="en-US,en;q=0.9",
        platform="Windows",
        impersonation_target="chrome124",
    ),
    BrowserProfile(
        browser_version="chrome120",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        accept_language="en-US,en;q=0.9",
        platform="macOS",
        impersonation_target="chrome120",
    ),
    BrowserProfile(
        browser_version="chrome120",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        accept_language="en-US,en;q=0.9",
        platform="Windows",
        impersonation_target="chrome120",
    ),
    BrowserProfile(
        browser_version="chrome116",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Not)A;Brand";v="24", "Chromium";v="116", "Google Chrome";v="116"',
        accept_language="en-US,en;q=0.9",
        platform="macOS",
        impersonation_target="chrome116",
    ),
    BrowserProfile(
        browser_version="chrome116",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Not)A;Brand";v="24", "Chromium";v="116", "Google Chrome";v="116"',
        accept_language="en-US,en;q=0.9",
        platform="Windows",
        impersonation_target="chrome116",
    ),
]
