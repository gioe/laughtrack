"""
Protocol for domain event models that can convert themselves into Show objects.

This is intentionally minimal to support lightweight conversions in contexts
where a full transformer may not be required.
"""

from typing import Optional, Protocol, runtime_checkable
from laughtrack.core.entities.club.model import Club

@runtime_checkable
class ShowConvertible(Protocol):
    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):  # -> Optional[Show]
        """Convert the object to a Show or return None if not possible."""
        ...
