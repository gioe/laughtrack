"""Pure HTML utilities with no domain dependencies."""

import re
from html import unescape
from typing import Optional


_TAG_RE = re.compile(r"<[^>]+>")


class HtmlUtils:
    """Pure HTML manipulation utilities."""

    @staticmethod
    def strip_tags(text: Optional[str], *, normalize_whitespace: bool = False) -> str:
        """Remove HTML tags from *text* and decode HTML entities.

        Args:
            text: HTML string. ``None`` and empty inputs return ``""``.
            normalize_whitespace: When ``True``, tags collapse to a single
                space (preserving word boundaries across markup), non-breaking
                spaces (``\\xa0``) become regular spaces, and runs of
                whitespace collapse to a single space. When ``False`` (default),
                tags are stripped with no replacement and only the surrounding
                whitespace is trimmed.

        Returns:
            The plain-text content with entities decoded.
        """
        if not text:
            return ""
        if normalize_whitespace:
            stripped = _TAG_RE.sub(" ", text)
            return " ".join(unescape(stripped).replace("\xa0", " ").split())
        return unescape(_TAG_RE.sub("", text)).strip()
