from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class PerClubStat:
    club: str
    num_shows: int = 0
    execution_time: float = 0.0
    success: bool = False
    error: Optional[str] = None
    club_id: Optional[int] = None
    inserted: Optional[int] = None
    updated: Optional[int] = None
    saved: Optional[int] = None
    failed_saves: Optional[int] = None
    errors: Optional[int] = None
    success_rate: Optional[float] = None
    skipped_dedup: Optional[int] = None
    validation_failed: Optional[int] = None
    db_errors: Optional[int] = None
