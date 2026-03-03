"""Domain facade for Show services.

Re-export core service to make domain the canonical import path.
"""

from laughtrack.core.entities.show.service import ShowService  # noqa: F401

__all__ = ["ShowService"]
