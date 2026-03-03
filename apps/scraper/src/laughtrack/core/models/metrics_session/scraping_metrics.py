from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from laughtrack.foundation.infrastructure.logger.logger import Logger

from ..metrics_parts import PerClubStat, ErrorDetail, DuplicateShowDetail


@dataclass
class ScrapingMetrics:
    export_path: Optional[str] = None
    shows_scraped: int = 0
    shows_saved: int = 0
    shows_inserted: int = 0
    shows_updated: int = 0
    shows_failed_save: int = 0
    shows_skipped_dedup: int = 0
    shows_validation_failed: int = 0
    shows_db_errors: int = 0
    clubs_processed: int = 0
    clubs_successful: int = 0
    clubs_failed: int = 0
    errors_total: int = 0
    success_rate: float = 0.0
    session_duration_seconds: float = 0.0
    club_execution_times: List[float] = field(default_factory=list)
    per_club_stats: List[PerClubStat] = field(default_factory=list)
    error_details: List[ErrorDetail] = field(default_factory=list)
    duplicate_show_details: List[DuplicateShowDetail] = field(default_factory=list)

    def _ensure_export_dir(self) -> None:
        if self.export_path:
            os.makedirs(self.export_path, exist_ok=True)

    def inc_shows_scraped(self, n: int = 1) -> None: self.shows_scraped += int(n)
    def inc_shows_saved(self, n: int = 1) -> None: self.shows_saved += int(n)
    def inc_shows_inserted(self, n: int = 1) -> None: self.shows_inserted += int(n)
    def inc_shows_updated(self, n: int = 1) -> None: self.shows_updated += int(n)
    def inc_shows_failed_save(self, n: int = 1) -> None: self.shows_failed_save += int(n)
    def inc_shows_skipped_dedup(self, n: int = 1) -> None: self.shows_skipped_dedup += int(n)
    def inc_shows_validation_failed(self, n: int = 1) -> None: self.shows_validation_failed += int(n)
    def inc_shows_db_errors(self, n: int = 1) -> None: self.shows_db_errors += int(n)
    def inc_clubs_processed(self, n: int = 1) -> None: self.clubs_processed += int(n)
    def inc_clubs_successful(self, n: int = 1) -> None: self.clubs_successful += int(n)
    def inc_clubs_failed(self, n: int = 1) -> None: self.clubs_failed += int(n)
    def inc_errors_total(self, n: int = 1) -> None: self.errors_total += int(n)
    def add_execution_time(self, seconds: float) -> None:
        try: self.club_execution_times.append(float(seconds))
        except Exception: pass
    def set_per_club_stats(self, stats: List[PerClubStat]) -> None: self.per_club_stats = list(stats or [])
    def set_error_details(self, details: List[ErrorDetail]) -> None: self.error_details = list(details or [])
    def append_duplicate_details(self, details: List[DuplicateShowDetail]) -> None:
        if details: self.duplicate_show_details.extend(list(details))
    def compute_success_rate(self) -> float:
        return (self.shows_saved / float(self.shows_scraped)) * 100.0 if self.shows_scraped > 0 else 0.0
    def export_metrics(self) -> None:
        if not self.export_path:
            Logger.warn("Export path not configured"); return
        self._ensure_export_dir()
        try:
            payload = {
                "session": {"duration_seconds": self.session_duration_seconds, "exported_at": datetime.now().isoformat()},
                "shows": {"scraped": self.shows_scraped, "saved": self.shows_saved, "inserted": self.shows_inserted, "updated": self.shows_updated, "failed_save": self.shows_failed_save, "skipped_dedup": self.shows_skipped_dedup, "validation_failed": self.shows_validation_failed, "db_errors": self.shows_db_errors},
                "clubs": {"processed": self.clubs_processed, "successful": self.clubs_successful, "failed": self.clubs_failed},
                "errors": {"total": self.errors_total},
                "success_rate": self.success_rate,
                "execution_times": self.club_execution_times,
                "per_club_stats": [asdict(s) for s in self.per_club_stats],
                "error_details": [asdict(e) for e in self.error_details],
                "duplicate_show_details": [asdict(d) for d in self.duplicate_show_details],
            }
            export_file = Path(self.export_path) / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(export_file, "w", encoding="utf-8") as f: json.dump(payload, f, indent=2)
            Logger.info(f"Exported metrics to {export_file}")
        except Exception as e:
            Logger.error(f"Failed to export metrics: {str(e)}")
