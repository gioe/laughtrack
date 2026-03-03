"""Domain facade for Comedian services.

Re-export core service to make domain the canonical import path.
"""

from laughtrack.core.entities.comedian.service import ComedianService  # noqa: F401

__all__ = ["ComedianService"]
