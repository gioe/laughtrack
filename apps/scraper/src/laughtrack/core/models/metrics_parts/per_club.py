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
    # Fetch-layer diagnostics — let 0-show results self-triage without a rerun.
    # http_status is the most-diagnostic response code seen (non-200 wins over 200);
    # items_before_filter counts raw events parsed before dedup/date/validation filters.
    http_status: Optional[int] = None
    bot_block_detected: bool = False
    bot_block_signature: Optional[str] = None
    bot_block_provider: Optional[str] = None
    bot_block_type: Optional[str] = None
    bot_block_source: Optional[str] = None
    bot_block_stage: Optional[str] = None
    playwright_fallback_used: bool = False
    items_before_filter: Optional[int] = None
