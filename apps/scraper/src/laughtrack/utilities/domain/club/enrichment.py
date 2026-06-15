"""Extract a club's description from its website HTML.

The extractor is intentionally conservative — it only returns a value when
it can be parsed unambiguously from a structured source: schema.org JSON-LD
``description`` on a LocalBusiness-style node, then HTML
``<meta name="description">`` and ``<meta property="og:description">``.
"""

from __future__ import annotations

import html as _html
import json
import re
from typing import Any, Dict, Iterable, List, Optional

_MAX_DESCRIPTION_LENGTH = 1000

_LDJSON_SCRIPT_RE = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def extract_description(html: Optional[str]) -> Optional[str]:
    """Return a cleaned description, or ``None`` when nothing usable is found.

    Tries JSON-LD first (a LocalBusiness node's ``description`` is more
    editorial than an SEO-tuned meta tag), then falls back to the standard
    HTML meta tags.
    """
    if not html:
        return None

    for node in _iter_ldjson_nodes(html):
        desc = node.get("description")
        if isinstance(desc, str) and desc.strip():
            return _clean_text(desc)

    meta_desc = _extract_meta_content(
        html,
        [
            ("name", "description"),
            ("property", "og:description"),
            ("name", "og:description"),
            ("name", "twitter:description"),
        ],
    )
    if meta_desc:
        return _clean_text(meta_desc)

    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iter_ldjson_nodes(html: str) -> Iterable[Dict[str, Any]]:
    """Yield every dict found inside any ``application/ld+json`` block.

    Walks ``@graph`` collections and nested objects so LocalBusiness nodes
    buried inside a WebPage or Organization graph are still discoverable.
    """
    for raw in _LDJSON_SCRIPT_RE.findall(html):
        try:
            data = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        yield from _walk(data)


def _walk(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            if isinstance(value, (dict, list)):
                yield from _walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item)


def _extract_meta_content(html: str, attrs: List[tuple[str, str]]) -> Optional[str]:
    """Regex-based meta tag reader (BeautifulSoup-free to keep this module cheap).

    Tolerates attribute order and quoting variations since the tags we care
    about are standard enough to match with a loose pattern.
    """
    for attr_name, attr_value in attrs:
        pattern = re.compile(
            rf'<meta[^>]*{attr_name}\s*=\s*["\']{re.escape(attr_value)}["\'][^>]*>',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if not match:
            continue
        tag = match.group(0)
        content_match = re.search(r'content\s*=\s*["\']([^"\']*)["\']', tag, re.IGNORECASE)
        if content_match and content_match.group(1).strip():
            return content_match.group(1)
    return None


def _clean_text(text: str) -> str:
    # Decode HTML entities before collapsing whitespace so "&amp;"/"&nbsp;"
    # don't survive to the UI as literal character sequences.
    cleaned = _html.unescape(text).replace("\u00a0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > _MAX_DESCRIPTION_LENGTH:
        cleaned = cleaned[: _MAX_DESCRIPTION_LENGTH - 1].rstrip() + "\u2026"
    return cleaned
