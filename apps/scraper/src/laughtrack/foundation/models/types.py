"""
Centralized type definitions for the Laughtrack application.

This module contains all common type aliases, TypeVars, and custom type definitions
used throughout the codebase to ensure consistency and avoid duplication.
"""

from typing import Any, Dict, List, TypeVar, Union, Tuple
from dataclasses import dataclass

# =============================================================================
# Common TypeVars
# =============================================================================

# Generic type variable for any type
T = TypeVar("T")

# Generic type variable for return types
R = TypeVar("R")

# Generic type variable for input types
Input = TypeVar("Input")

# Generic type variable for output types
Output = TypeVar("Output")


# =============================================================================
# JSON Type Aliases
# =============================================================================

# Represents any valid JSON value
JSONValue = Any

# Represents a JSON object (dictionary with string keys)
JSONDict = Dict[str, Any]

# Represents a JSON array
JSONArray = List[Dict[str, Any]]

# Represents raw JSON data (either object or array)
JSONData = Union[Dict[str, Any], List[Dict[str, Any]]]


# =============================================================================
# Database Type Aliases
# =============================================================================

# Database row representation
DatabaseRow = Dict[str, Any]

# Database query parameters
QueryParams = Dict[str, Any]

# Database connection string
ConnectionString = str


# =============================================================================
# HTTP Type Aliases
# =============================================================================

# HTTP headers dictionary
HTTPHeaders = Dict[str, str]

# HTTP parameters dictionary
HTTPParams = Dict[str, Union[str, int, float, bool]]

# URL string
URL = str


# =============================================================================
# Scraping Type Aliases
# =============================================================================

# HTML content string
HTMLContent = str

# Raw scraped data (before validation)
RawScrapedData = Dict[str, Any]

# Validated scraped data (after schema validation)
ValidatedData = Dict[str, Any]

# Type alias to clarify that discover_urls can return URLs or identifiers
ScrapingTarget = str  # Can be a URL or an identifier (like date string) used by extract_data


# =============================================================================
# Deduplication Detail Types
# =============================================================================

@dataclass
class DuplicateShowRef:
	"""Reference to a show variant used in deduplication logs."""

	name: str
	show_page_url: str | None = None


@dataclass
class DuplicateKeyDetails:
	"""Details describing duplicates for a unique (club_id, date, room) key."""

	# Use ISO string for date to ensure JSON-serializable metadata
	key: Tuple[int, str, str]
	club_id: int
	# ISO 8601 string representation for consistent logging/serialization
	date: str
	room: str
	kept: DuplicateShowRef
	dropped: List[DuplicateShowRef]
