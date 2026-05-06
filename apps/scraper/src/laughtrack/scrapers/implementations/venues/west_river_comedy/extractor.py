"""Extract TicketTailor detail links for West River Comedy Club."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


_TICKETTAILOR_HOST = "www.tickettailor.com"
_EVENT_PATH_PREFIX = "/events/westrivercomedyclub/"


def extract_event_urls(html: str, base_url: str = "https://www.tickettailor.com") -> list[str]:
    """Return unique TicketTailor event detail URLs from a listing page."""
    soup = BeautifulSoup(html or "", "html.parser")
    urls: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(base_url, anchor["href"])
        parsed = urlparse(absolute)
        if parsed.netloc != _TICKETTAILOR_HOST:
            continue
        if not parsed.path.startswith(_EVENT_PATH_PREFIX):
            continue
        if parsed.path.endswith("/select-date"):
            continue

        normalized = f"https://{_TICKETTAILOR_HOST}{parsed.path}"
        if normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)

    return urls


def extract_pagination_urls(html: str, base_url: str) -> list[str]:
    """Return TicketTailor listing pagination URLs from a listing page."""
    soup = BeautifulSoup(html or "", "html.parser")
    urls: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        if not _is_pagination_link(anchor):
            continue

        absolute = urljoin(base_url, anchor["href"])
        parsed = urlparse(absolute)
        if parsed.netloc != _TICKETTAILOR_HOST:
            continue
        if not parsed.path.rstrip("/").endswith("/events/westrivercomedyclub"):
            continue

        normalized = f"https://{_TICKETTAILOR_HOST}{parsed.path}"
        if parsed.query:
            normalized = f"{normalized}?{parsed.query}"
        if normalized in seen:
            continue
        seen.add(normalized)
        urls.append(normalized)

    return urls


def _is_pagination_link(anchor) -> bool:
    rel = anchor.get("rel") or []
    if isinstance(rel, str):
        rel = [rel]
    rel_values = {str(value).lower() for value in rel}
    if "next" in rel_values:
        return True

    label = " ".join(
        part.strip().lower()
        for part in [
            anchor.get("aria-label", ""),
            anchor.get_text(" ", strip=True),
            " ".join(anchor.get("class", [])),
        ]
        if part
    )
    return "pagination" in label and ("next" in label or "page" in label)
