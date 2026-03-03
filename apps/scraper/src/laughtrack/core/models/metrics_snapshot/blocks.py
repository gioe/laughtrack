from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SessionBlock:
    duration_seconds: float = 0.0
    exported_at: str = ""


@dataclass
class ShowsBlock:
    scraped: int = 0
    saved: int = 0
    inserted: int = 0
    updated: int = 0
    failed_save: int = 0
    skipped_dedup: int = 0
    validation_failed: int = 0
    db_errors: int = 0


@dataclass
class ClubsBlock:
    processed: int = 0
    successful: int = 0
    failed: int = 0


@dataclass
class ErrorsBlock:
    total: int = 0
