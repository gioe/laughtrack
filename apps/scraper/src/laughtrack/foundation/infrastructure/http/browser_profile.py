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
# Only versions that have a matching curl-cffi impersonation target are
# included here.  Using an unsupported target would silently fall back to
# plain HTTP/2 without a real browser TLS fingerprint.

BUILTIN_PROFILES: List[BrowserProfile] = [
    BrowserProfile(
        browser_version="chrome124",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
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
        sec_ch_ua='"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        accept_language="en-US,en;q=0.9",
        platform="Windows",
        impersonation_target="chrome124",
    ),
    BrowserProfile(
        browser_version="chrome131",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="131", "Chromium";v="131", "Not-A.Brand";v="24"',
        accept_language="en-US,en;q=0.9",
        platform="macOS",
        impersonation_target="chrome131",
    ),
    BrowserProfile(
        browser_version="chrome131",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="131", "Chromium";v="131", "Not-A.Brand";v="24"',
        accept_language="en-US,en;q=0.9",
        platform="Windows",
        impersonation_target="chrome131",
    ),
    BrowserProfile(
        browser_version="chrome136",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="136", "Chromium";v="136", "Not/A)Brand";v="24"',
        accept_language="en-US,en;q=0.9",
        platform="macOS",
        impersonation_target="chrome136",
    ),
    BrowserProfile(
        browser_version="chrome136",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="136", "Chromium";v="136", "Not/A)Brand";v="24"',
        accept_language="en-US,en;q=0.9",
        platform="Windows",
        impersonation_target="chrome136",
    ),
    BrowserProfile(
        browser_version="chrome_android135",
        user_agent=(
            "Mozilla/5.0 (Linux; Android 10; K) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36"
        ),
        sec_ch_ua='"Google Chrome";v="135", "Chromium";v="135", "Not-A.Brand";v="8"',
        accept_language="en-US,en;q=0.9",
        platform="Android",
        impersonation_target="chrome_android135",
    ),
]
