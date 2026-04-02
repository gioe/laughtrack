"""Club quality filter — rejects junk venues before they reach the database."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import yaml

from laughtrack.foundation.infrastructure.logger.logger import Logger

_RULES_PATH = Path(__file__).resolve().parents[3] / "infrastructure" / "config" / "club_quality_rules.yaml"


def _load_rules() -> dict:
    with open(_RULES_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# Rules are loaded once at module import so the file is read a single time per
# process, but can be patched in tests via the module-level _RULES reference.
_RULES: dict = _load_rules()


def _check_name(name: str, rules: dict) -> Optional[str]:
    """Return a rejection reason if *name* matches a prefix deny rule, else None."""
    for prefix in rules.get("name_prefix_deny", []):
        if name.startswith(prefix):
            return f"name starts with denied prefix '{prefix}'"
    return None


def _check_website(website: str, rules: dict) -> Optional[str]:
    """Return a rejection reason if *website* matches a deny rule, else None."""
    # Exact-match check (covers empty string and '#')
    stripped = website.strip()
    for exact in rules.get("website_deny_exact", []):
        if stripped == exact:
            reason = f"website is '{exact}'" if exact else "website is empty"
            return reason

    # Hostname check — only applicable when URL has a scheme
    if not stripped:
        return None
    try:
        hostname = urlparse(stripped).hostname or ""
    except Exception:
        return None

    if not hostname:
        return None

    hostname_rules = rules.get("website_hostname_deny", {})
    for exact_host in hostname_rules.get("exact", []):
        if hostname == exact_host:
            return f"website hostname '{hostname}' is on the deny list"
    for pattern in hostname_rules.get("glob", []):
        if fnmatch.fnmatch(hostname, pattern):
            return f"website hostname '{hostname}' matches denied pattern '{pattern}'"

    return None


def is_junk_venue(name: str, website: str) -> bool:
    """
    Return True if the venue should be rejected before DB ingestion.

    Logs a warning with the club name and matched rule when a venue is rejected.
    """
    rules = _RULES

    reason = _check_name(name, rules)
    if reason is None:
        reason = _check_website(website, rules)

    if reason is not None:
        Logger.warn(f"Club quality filter: rejecting '{name}' — {reason}")
        return True

    return False
