"""Data model for a single event from Empire Comedy Club."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EmpireEvent:
    """Data model representing a single event from Empire Comedy Club."""

    name: str
    date_time: datetime
    show_page_url: str
    status: Optional[str] = None
