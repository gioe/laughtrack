"""Ticket entity package.

Keep imports minimal to avoid circular dependencies. Use lazy imports.
"""

from typing import Any

__all__ = []


def __getattr__(name: str) -> Any:
	if name == "Ticket":
		from .model import Ticket as _Ticket

		return _Ticket
	raise AttributeError(name)
