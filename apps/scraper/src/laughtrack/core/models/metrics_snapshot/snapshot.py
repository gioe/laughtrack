from __future__ import annotations
import datetime as _dt
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from laughtrack.foundation.utilities.datetime.utils import DateTimeUtils

from ..metrics_parts import PerClubStat, ErrorDetail, DuplicateShow, DuplicateShowDetail
from .blocks import SessionBlock, ShowsBlock, ClubsBlock, ErrorsBlock

if TYPE_CHECKING:
    from laughtrack.core.models.results import ScrapingSessionResult
    from laughtrack.foundation.models.operation_result import DatabaseOperationResult


@dataclass
class ScrapingMetricsSnapshot:
    timestamp: str
    datetime: _dt.datetime
    session: SessionBlock
    shows: ShowsBlock
    clubs: ClubsBlock
    errors: ErrorsBlock
    success_rate: float = 0.0
    execution_times: List[float] = field(default_factory=list)
    per_club_stats: List[PerClubStat] = field(default_factory=list)
    error_details: List[ErrorDetail] = field(default_factory=list)
    duplicate_show_details: List[DuplicateShowDetail] = field(default_factory=list)

    @staticmethod
    def _parse_per_club_stats(data: List[Dict[str, Any]] | None) -> List[PerClubStat]:
        out: List[PerClubStat] = []
        for d in data or []:
            out.append(
                PerClubStat(
                    club=str(d.get("club", "")),
                    num_shows=int(d.get("num_shows", 0) or 0),
                    execution_time=float(d.get("execution_time", 0.0) or 0.0),
                    success=bool(d.get("success", False)),
                    error=d.get("error"),
                    club_id=d.get("club_id"),
                    inserted=d.get("inserted"),
                    updated=d.get("updated"),
                    saved=d.get("saved"),
                    failed_saves=d.get("failed_saves"),
                    errors=d.get("errors"),
                    success_rate=d.get("success_rate"),
                    skipped_dedup=d.get("skipped_dedup"),
                    validation_failed=d.get("validation_failed"),
                    db_errors=d.get("db_errors"),
                )
            )
        return out

    @staticmethod
    def _parse_error_details(data: List[Dict[str, Any]] | None) -> List[ErrorDetail]:
        out: List[ErrorDetail] = []
        for d in data or []:
            out.append(
                ErrorDetail(
                    club=str(d.get("club", "")),
                    error=d.get("error"),
                    execution_time=float(d.get("execution_time", 0.0) or 0.0),
                )
            )
        return out

    @staticmethod
    def _parse_duplicate_details(data: List[Dict[str, Any]] | None) -> List[DuplicateShowDetail]:
        out: List[DuplicateShowDetail] = []
        for d in data or []:
            kept_raw = d.get("kept") or {}
            kept = DuplicateShow(name=str(kept_raw.get("name", "") or ""), show_page_url=kept_raw.get("show_page_url"))
            dropped: List[DuplicateShow] = []
            for x in d.get("dropped", []) or []:
                dropped.append(DuplicateShow(name=str(x.get("name", "") or ""), show_page_url=x.get("show_page_url")))
            out.append(
                DuplicateShowDetail(
                    club_id=d.get("club_id"),
                    club_name=d.get("club_name"),
                    date=str(d.get("date", "") or ""),
                    room=(d.get("room") if isinstance(d.get("room"), str) else None),
                    kept=kept,
                    dropped=dropped,
                )
            )
        return out

    @classmethod
    def from_json(cls, data: Dict[str, Any], timestamp: str, dt: _dt.datetime) -> "ScrapingMetricsSnapshot":
        session_data = data.get("session", {}) or {}
        shows_data = data.get("shows", {}) or {}
        clubs_data = data.get("clubs", {}) or {}
        errors_data = data.get("errors", {}) or {}
        session = SessionBlock(
            duration_seconds=float(session_data.get("duration_seconds", 0.0) or 0.0),
            exported_at=str(session_data.get("exported_at", "")),
        )
        shows = ShowsBlock(
            scraped=int(shows_data.get("scraped", 0) or 0),
            saved=int(shows_data.get("saved", 0) or 0),
            inserted=int(shows_data.get("inserted", 0) or 0),
            updated=int(shows_data.get("updated", 0) or 0),
            failed_save=int(shows_data.get("failed_save", 0) or 0),
            skipped_dedup=int(shows_data.get("skipped_dedup", 0) or 0),
            validation_failed=int(shows_data.get("validation_failed", 0) or 0),
            db_errors=int(shows_data.get("db_errors", 0) or 0),
        )
        clubs = ClubsBlock(
            processed=int(clubs_data.get("processed", 0) or 0),
            successful=int(clubs_data.get("successful", 0) or 0),
            failed=int(clubs_data.get("failed", 0) or 0),
        )
        errors = ErrorsBlock(total=int(errors_data.get("total", 0) or 0))
        per_club_stats = cls._parse_per_club_stats(data.get("per_club_stats"))
        error_details = cls._parse_error_details(data.get("error_details"))
        duplicate_show_details = cls._parse_duplicate_details(data.get("duplicate_show_details"))
        return cls(
            timestamp=timestamp,
            datetime=dt,
            session=session,
            shows=shows,
            clubs=clubs,
            errors=errors,
            success_rate=float(data.get("success_rate", 0.0) or 0.0),
            execution_times=list(data.get("execution_times") or []),
            per_club_stats=per_club_stats,
            error_details=error_details,
            duplicate_show_details=duplicate_show_details,
        )

    def to_json_dict(self) -> Dict[str, Any]:
        formatted_timestamp = DateTimeUtils.format_display_date(self.datetime.isoformat())
        duration_minutes = (self.session.duration_seconds / 60.0) if self.session.duration_seconds else 0.0
        return {
            "timestamp": formatted_timestamp,
            "shows_scraped": self.shows.scraped,
            "shows_saved": self.shows.saved,
            "shows_inserted": self.shows.inserted,
            "shows_updated": self.shows.updated,
            "failed_saves": self.shows.failed_save,
            "clubs_processed": self.clubs.processed,
            "errors": self.errors.total,
            "success_rate": self.success_rate,
            "duration_minutes": duration_minutes,
            "successful_clubs": self.clubs.successful,
            "failed_clubs": self.clubs.failed,
        }

    def to_full_json(self) -> Dict[str, Any]:
        return {
            "session": {
                "duration_seconds": float(self.session.duration_seconds or 0.0),
                "exported_at": str(self.session.exported_at or self.datetime.isoformat()),
            },
            "shows": {
                "scraped": int(self.shows.scraped or 0),
                "saved": int(self.shows.saved or 0),
                "inserted": int(self.shows.inserted or 0),
                "updated": int(self.shows.updated or 0),
                "failed_save": int(self.shows.failed_save or 0),
                "skipped_dedup": int(self.shows.skipped_dedup or 0),
                "validation_failed": int(self.shows.validation_failed or 0),
                "db_errors": int(self.shows.db_errors or 0),
            },
            "clubs": {
                "processed": int(self.clubs.processed or 0),
                "successful": int(self.clubs.successful or 0),
                "failed": int(self.clubs.failed or 0),
            },
            "errors": {"total": int(self.errors.total or 0)},
            "success_rate": float(self.success_rate or 0.0),
            "execution_times": [float(x) for x in (self.execution_times or [])],
            "per_club_stats": [asdict(s) for s in (self.per_club_stats or [])],
            "error_details": [asdict(e) for e in (self.error_details or [])],
            "duplicate_show_details": [asdict(d) for d in (self.duplicate_show_details or [])],
        }

    @classmethod
    def from_session(
        cls,
        session_result: "ScrapingSessionResult",
        db_operation_result: "DatabaseOperationResult",
        dt: _dt.datetime,
    ) -> "ScrapingMetricsSnapshot":
        shows_scraped = len(session_result.shows)
        saved = db_operation_result.total
        inserted = db_operation_result.inserts
        updated = db_operation_result.updates
        failed_save = db_operation_result.errors
        validation_failed = db_operation_result.validation_errors
        db_errors = db_operation_result.db_errors
        duplicate_details = db_operation_result.duplicate_details
        skipped_dedup = 0
        typed_duplicates: List[DuplicateShowDetail] = []
        try:
            for d in duplicate_details:
                dropped_list = d.dropped
                skipped_dedup += len(dropped_list)
                kept_ref = d.kept
                kept = DuplicateShow(name=kept_ref.name, show_page_url=kept_ref.show_page_url)
                dropped = [DuplicateShow(name=str(x.name or ""), show_page_url=x.show_page_url) for x in dropped_list]
                typed_duplicates.append(
                    DuplicateShowDetail(
                        club_id=d.club_id,
                        club_name=None,
                        date=str(d.date or ""),
                        room=d.room,
                        kept=kept,
                        dropped=dropped,
                    )
                )
        except Exception:
            typed_duplicates = []
            skipped_dedup = 0
        total_clubs = session_result.total_clubs
        successful_clubs = session_result.successful_clubs
        failed_clubs = max(0, total_clubs - successful_clubs)
        total_errors = session_result.total_errors
        per_club_stats: List[PerClubStat] = list(session_result.per_club_stats or [])
        exec_times = [float(s.execution_time or 0.0) for s in per_club_stats]
        duration_seconds = float(sum(exec_times)) if exec_times else 0.0
        success_rate = (saved / shows_scraped * 100.0) if shows_scraped > 0 else 0.0
        return cls(
            timestamp=dt.isoformat(),
            datetime=dt,
            session=SessionBlock(duration_seconds=duration_seconds, exported_at=dt.isoformat()),
            shows=ShowsBlock(
                scraped=shows_scraped,
                saved=saved,
                inserted=inserted,
                updated=updated,
                failed_save=failed_save,
                skipped_dedup=skipped_dedup,
                validation_failed=validation_failed,
                db_errors=db_errors,
            ),
            clubs=ClubsBlock(processed=total_clubs, successful=successful_clubs, failed=failed_clubs),
            errors=ErrorsBlock(total=total_errors),
            success_rate=success_rate,
            execution_times=exec_times,
            per_club_stats=per_club_stats,
            error_details=list(getattr(session_result, "errors", []) or []),
            duplicate_show_details=typed_duplicates,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["ScrapingMetricsSnapshot"]:
        from datetime import datetime as _ldt
        try:
            exported_at: Optional[str] = None
            if isinstance(data.get("session"), dict):
                exported_at = (
                    data["session"].get("exported_at")
                    or data["session"].get("ended_at")
                    or data["session"].get("finished_at")
                )
            def _resolve_dt(raw: Dict[str, Any]) -> _ldt:
                for k in ("datetime", "timestamp", "created_at"):
                    v = raw.get(k)
                    if not v: continue
                    try:
                        if isinstance(v, (int, float)): return _ldt.fromtimestamp(float(v))
                        if isinstance(v, str):
                            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                                try: return _ldt.strptime(v[:26], fmt)
                                except Exception: pass
                    except Exception: continue
                sess = raw.get("session")
                if isinstance(sess, dict):
                    exp = sess.get("exported_at") or sess.get("ended_at") or sess.get("finished_at")
                    if isinstance(exp, str):
                        try: return _ldt.fromisoformat(exp.replace("Z", "+00:00"))
                        except Exception: pass
                return _ldt.min
            if isinstance(exported_at, str):
                try: dt = _ldt.fromisoformat(exported_at.replace("Z", "+00:00"))
                except Exception: dt = _resolve_dt(data)
            else:
                dt = _resolve_dt(data); exported_at = dt.isoformat()
            def _metric_value(container: Dict[str, Any], key: str):
                series = container.get(key)
                if isinstance(series, dict):
                    vals = series.get("values")
                    if isinstance(vals, list) and vals:
                        return (vals[-1] or {}).get("value") or 0
                return series if series is not None else 0
            if all(k in data for k in ("session", "shows", "clubs", "errors")):
                if isinstance(data.get("session"), dict) and not data["session"].get("exported_at"):
                    data["session"]["exported_at"] = exported_at  # type: ignore[index]
                return cls.from_json(data, timestamp=dt.isoformat(), dt=dt)
            def _val(primary: Any, *fallbacks: Any) -> Any:
                for v in (primary, *fallbacks):
                    if v not in (None, ""): return v
                return 0
            shows_scraped = _val(data.get("scraped"), _metric_value(data, "shows.scraped"))
            shows_saved = _val(data.get("saved"), _metric_value(data, "shows.saved"))
            shows_inserted = _val(_metric_value(data, "shows.inserted"))
            shows_updated = _val(_metric_value(data, "shows.updated"))
            shows_failed_save = _val(_metric_value(data, "shows.failed_save"))
            shows_skipped_dedup = _val(_metric_value(data, "shows.skipped_dedup"))
            shows_validation_failed = _val(_metric_value(data, "shows.validation_failed"))
            shows_db_errors = _val(_metric_value(data, "shows.db_errors"))
            clubs_processed = _val(_metric_value(data, "clubs.processed"), _metric_value(data, "clubs.total"))
            clubs_successful = _val(_metric_value(data, "clubs.successful"))
            clubs_failed = _val(_metric_value(data, "clubs.failed"))
            errors_total = _val(_metric_value(data, "errors.total"))
            per_club_stats_list = None
            if isinstance(data.get("per_club_stats"), list): per_club_stats_list = data.get("per_club_stats")
            elif isinstance(data.get("club_stats"), list): per_club_stats_list = data.get("club_stats")
            duplicate_details_raw = None
            if isinstance(data.get("duplicate_show_details"), list): duplicate_details_raw = data.get("duplicate_show_details")
            elif isinstance(data.get("duplicates"), list): duplicate_details_raw = data.get("duplicates")
            payload = {
                "session": {
                    "duration_seconds": float((data.get("session") or {}).get("duration_seconds", 0.0)) if isinstance(data.get("session"), dict) else 0.0,
                    "exported_at": exported_at,
                },
                "shows": {
                    "scraped": int(shows_scraped or 0),
                    "saved": int(shows_saved or 0),
                    "inserted": int(shows_inserted or 0),
                    "updated": int(shows_updated or 0),
                    "failed_save": int(shows_failed_save or 0),
                    "skipped_dedup": int(shows_skipped_dedup or 0),
                    "validation_failed": int(shows_validation_failed or 0),
                    "db_errors": int(shows_db_errors or 0),
                },
                "clubs": {"processed": int(clubs_processed or 0), "successful": int(clubs_successful or 0), "failed": int(clubs_failed or 0)},
                "errors": {"total": int(errors_total or 0)},
                "success_rate": float(data.get("success_rate") or 0.0),
                "execution_times": list(data.get("execution_times") or []),
                "per_club_stats": per_club_stats_list or [],
                "error_details": data.get("error_details") if isinstance(data.get("error_details"), list) else [],
                "duplicate_show_details": duplicate_details_raw or [],
            }
            return cls.from_json(payload, timestamp=dt.isoformat(), dt=dt)
        except Exception:
            return None

    @classmethod
    def from_file(cls, path: str | Path) -> Optional["ScrapingMetricsSnapshot"]:
        import json
        from datetime import datetime as _ldt
        try:
            p = Path(path)
            with open(p, "r", encoding="utf-8") as f: data = json.load(f)
            try:
                stem = p.name.replace("metrics_", "").replace(".json", ""); ts_from_file: _ldt = _ldt.strptime(stem, "%Y%m%d_%H%M%S")
            except Exception: ts_from_file = _ldt.now()
            if all(k in (data or {}) for k in ("session", "shows", "clubs", "errors")):
                session_block = data.get("session", {}) or {}
                ts_str = session_block.get("exported_at") or None
                if ts_str:
                    try: parsed_dt = _ldt.fromisoformat(ts_str)
                    except Exception: parsed_dt = ts_from_file
                else: parsed_dt = ts_from_file
                effective_dt: _ldt = parsed_dt or ts_from_file or _ldt.now()
                effective_ts: str = ts_str or effective_dt.isoformat()
                return cls.from_json(data, timestamp=effective_ts, dt=effective_dt)
            def latest_value(key: str) -> float:
                block = (data or {}).get(key) or {}; values = block.get("values") or []
                if not values: return 0.0
                try: return float((values[-1] or {}).get("value", 0.0) or 0.0)
                except Exception: return 0.0
            def latest_timestamp(key: str):
                block = (data or {}).get(key) or {}; values = block.get("values") or []
                if not values: return None
                return (values[-1] or {}).get("timestamp")
            ts_str = (latest_timestamp("session.duration") or latest_timestamp("shows.saved") or latest_timestamp("shows.scraped"))
            if ts_str:
                try: parsed_dt = _ldt.fromisoformat(ts_str)
                except Exception: parsed_dt = ts_from_file
            else: parsed_dt = ts_from_file
            typed_payload = {
                "session": {"duration_seconds": latest_value("session.duration"), "exported_at": ts_str or ts_from_file.isoformat()},
                "shows": {
                    "scraped": int(latest_value("shows.scraped")),
                    "saved": int(latest_value("shows.saved")),
                    "inserted": int(latest_value("shows.inserted")),
                    "updated": int(latest_value("shows.updated")),
                    "failed_save": int(latest_value("shows.failed_save")),
                    "skipped_dedup": int(latest_value("shows.skipped_dedup")),
                    "validation_failed": int(latest_value("shows.validation_failed")),
                    "db_errors": int(latest_value("shows.db_errors")),
                },
                "clubs": {"processed": int(latest_value("clubs.processed")), "successful": int(latest_value("clubs.successful")), "failed": int(latest_value("clubs.failed"))},
                "errors": {"total": int(latest_value("errors.total"))},
                "success_rate": float(latest_value("success_rate")),
                "execution_times": [],
                "per_club_stats": ((data.get("metadata", {}) or {}).get("per_club_stats", []) or []),
                "error_details": ((data.get("metadata", {}) or {}).get("error_details", []) or []),
                "duplicate_show_details": ((data.get("metadata", {}) or {}).get("duplicate_show_details", []) or []),
            }
            effective_dt = parsed_dt or ts_from_file or _ldt.now(); effective_ts = ts_str or effective_dt.isoformat()
            return cls.from_json(typed_payload, timestamp=effective_ts, dt=effective_dt)
        except Exception: return None
