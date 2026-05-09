"""
Foundation utilities with no domain dependencies.

These utilities contain pure functions for basic data manipulation using
only standard library and common third-party dependencies.
"""

from .datetime import DateTimeUtils
from .html import HtmlUtils
from .string import StringUtils
from .url import URLUtils

__all__ = [
    "DateTimeUtils",
    "HtmlUtils",
    "StringUtils",
    "URLUtils",
]
