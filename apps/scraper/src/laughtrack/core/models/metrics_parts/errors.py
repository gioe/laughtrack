from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class ErrorDetail:
    club: str
    error: Optional[str] = None
    execution_time: float = 0.0
