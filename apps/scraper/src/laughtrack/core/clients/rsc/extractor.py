"""Shared extraction primitives for Next.js RSC flight payloads."""

import json
import re

from typing import List, Optional


_PUSH_PATTERN = re.compile(
    r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)',
    re.DOTALL,
)
_RSC_REFERENCE_PATTERN = re.compile(r'"\$[^"]+"')


def extract_push_payloads(html: str) -> List[str]:
    """Return decoded payload strings from self.__next_f.push([1, "..."]) calls."""
    if not html:
        return []

    payloads: List[str] = []
    for match in _PUSH_PATTERN.finditer(html):
        try:
            payloads.append(json.loads(f'"{match.group(1)}"'))
        except (json.JSONDecodeError, ValueError):
            continue
    return payloads


def find_json_array(text: str, key: str) -> Optional[list]:
    """Find and parse a balanced JSON array following a property key."""
    if not text or not key:
        return None

    key_pattern = f'"{key}":'
    key_idx = text.find(key_pattern)
    if key_idx < 0:
        return None

    arr_start = text.find("[", key_idx + len(key_pattern))
    if arr_start < 0:
        return None

    array_json = _extract_balanced(text, arr_start, "[", "]")
    if not array_json:
        return None

    try:
        value = json.loads(array_json)
    except (json.JSONDecodeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def resolve_references(payload: str) -> str:
    """Replace quoted RSC references like "$L5" or "$Sreact.suspense" with null."""
    if not payload:
        return payload
    return _RSC_REFERENCE_PATTERN.sub("null", payload)


def _extract_balanced(
    text: str,
    start: int,
    open_ch: str,
    close_ch: str,
) -> Optional[str]:
    """Extract a balanced bracket/brace block, ignoring delimiters in strings."""
    if start < 0 or start >= len(text) or text[start] != open_ch:
        return None

    depth = 0
    in_string = False
    i = start
    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        i += 1

    return None
