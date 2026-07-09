"""
Core database infrastructure components.

This module contains the foundational database handling classes:
- BaseDatabaseHandler: Unified database operations with entity abstractions

Deliberately imports nothing from laughtrack.adapters or
laughtrack.infrastructure: the concrete DB adapter reaches base_handler
through its ports.database seam, registered by the composition roots
(scripts/__init__.py, laughtrack.app.wiring) — TASK-3701.
"""

from .base_handler import BaseDatabaseHandler

__all__ = [
    "BaseDatabaseHandler",
]
