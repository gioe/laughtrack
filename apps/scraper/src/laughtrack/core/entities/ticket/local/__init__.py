"""
Local ticket models package.

Use lazy imports to avoid pulling in unrelated dependencies during import-time
of the package. This helps tests that only need a specific ticket adapter.
"""

from typing import Any


def __getattr__(name: str) -> Any:
    if name == "EventbriteTicket":
        from .eventbrite import EventbriteTicket as _T

        return _T
    if name == "BroadwayTicket":
        from .broadway import BroadwayTicket as _T

        return _T
    if name == "Grove34Ticket":
        from .grove34 import Grove34Ticket as _T

        return _T
    if name == "ComedyCellarTicket":
        from .comedy_cellar import ComedyCellarTicket as _T

        return _T
    raise AttributeError(name)
