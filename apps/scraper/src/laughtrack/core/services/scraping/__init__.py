"""Scraping service package (public path preserved)."""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.base.base_scraper import BaseScraper
from laughtrack.utilities.domain.club.selector import ClubSelector
from laughtrack.utilities.domain.scraper.result import ScrapingResultProcessor
from laughtrack.foundation.infrastructure.http.proxy_pool import ProxyPool
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.app.wiring import build_services  # noqa: F401 (side-effects for wiring if needed)
from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.core.models.domain_metrics import DomainRequestMetrics, ScrapingRunSummary
from laughtrack.foundation.models.operation_result import DatabaseOperationResult

_DEFAULT_SUCCESS_RATE_THRESHOLD = 70.0
_DEFAULT_MAX_CONCURRENT_CLUBS = 5


def _scrape_with_context(scraper: BaseScraper, club: Club) -> ClubScrapingResult:
    """Run scrape_with_result() inside the club's log context (thread-safe)."""
    with Logger.use_context(club.as_context()):
        return scraper.scrape_with_result()


class ScrapingService:
    def __init__(self, success_rate_threshold: float = _DEFAULT_SUCCESS_RATE_THRESHOLD):
        self.club_handler = ClubHandler()
        self.selector = ClubSelector()
        self._result_processor: Optional[ScrapingResultProcessor] = None
        self._scraping_resolver = ScraperResolver()
        self.success_rate_threshold: float = float(
            os.environ.get("SCRAPING_SUCCESS_RATE_THRESHOLD", success_rate_threshold)
        )
        self.proxy_pool: Optional[ProxyPool] = ProxyPool.from_env()

    @property
    def result_processor(self) -> ScrapingResultProcessor:
        if self._result_processor is None:
            self._result_processor = ScrapingResultProcessor()
        return self._result_processor

    def scrape_all_clubs(self) -> List[ClubScrapingResult]:
        Logger.info("Starting scrape of all clubs...")
        clubs = self.club_handler.get_all_clubs()
        if not clubs:
            raise ValueError("No clubs found with valid scraper configurations")
        Logger.info(f"Found {len(clubs)} clubs with scraper configurations")
        self._try_validate_scraper_keys(clubs)
        results, summary, db_result = self._scrape_clubs_with_metrics(clubs)
        self._emit_summary(summary)
        self._check_and_alert(summary)
        self.result_processor.process_results(results, db_result)
        self.club_handler.refresh_club_total_shows()
        return results

    def scrape_single_club(self, club_id: Optional[int] = None) -> None:
        Logger.info(f"Starting scrape of club: (ID: {club_id})")
        clubs = self.club_handler.get_clubs_by_ids([club_id]) if club_id else self.selector.get_club_selection()
        if not clubs:
            raise ValueError(f"Club with ID {club_id} not found" if club_id else "No club selected")
        results, _, db_result = self._scrape_clubs_with_metrics(clubs)
        self.result_processor.process_results(results, db_result)

    def scrape_by_scraper_type(self, scraper_type: Optional[str] = None) -> None:
        Logger.info(f"Starting scrape of all clubs using scraper type: {scraper_type}")
        scraper_type = scraper_type or self.selector.get_scraper_type_selection()
        if not scraper_type:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
        clubs = self.club_handler.get_clubs_for_scraper(scraper_type)
        results, _, db_result = self._scrape_clubs_with_metrics(clubs)
        self.result_processor.process_results(results, db_result)

    # --- Internal helpers ---
    @property
    def _max_concurrent_clubs(self) -> int:
        return int(os.environ.get("MAX_CONCURRENT_CLUBS", _DEFAULT_MAX_CONCURRENT_CLUBS))

    def _try_validate_scraper_keys(self, clubs: List[Club]) -> None:
        try:
            from laughtrack.app.validators.scraper_config import validate_scraper_keys_for_clubs
            validate_scraper_keys_for_clubs(clubs)
        except Exception as e:  # pragma: no cover - defensive
            Logger.warn(f"Scraper config validation skipped due to error: {e}")

    def _scrape_clubs_with_metrics(
        self, clubs: List[Club]
    ) -> tuple[List[ClubScrapingResult], ScrapingRunSummary, DatabaseOperationResult]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self._scrape_clubs_concurrently(clubs))
                return future.result()
        return asyncio.run(self._scrape_clubs_concurrently(clubs))

    async def _scrape_clubs_concurrently(
        self, clubs: List[Club]
    ) -> tuple[List[ClubScrapingResult], ScrapingRunSummary, DatabaseOperationResult]:
        semaphore = asyncio.Semaphore(self._max_concurrent_clubs)
        loop = asyncio.get_running_loop()
        total_db_result = DatabaseOperationResult()
        # db_lock serializes all DB writes: only one club writes at a time,
        # which keeps ShowService thread-safe regardless of its internals.
        db_lock = asyncio.Lock()
        self.result_processor.start_run()

        async def scrape_one(
            club: Club,
        ) -> tuple[Optional[ClubScrapingResult], Optional[DomainRequestMetrics]]:
            nonlocal total_db_result
            if not getattr(club, "scraper", None):
                Logger.warn(f"Club '{club.name}' has no scraper key configured; skipping")
                return None, None
            key: str = club.scraper if club.scraper is not None else ""
            scraper_cls = self._scraping_resolver.get(key)
            if not scraper_cls:
                Logger.warn(f"No scraper found for club '{club.name}' with key '{key}'")
                return None, None
            async with semaphore:
                metrics = DomainRequestMetrics(club_name=club.name, club_id=getattr(club, "id", None))
                metrics.total += 1
                try:
                    scraper: BaseScraper = scraper_cls(club, proxy_pool=self.proxy_pool)
                    result = await loop.run_in_executor(None, _scrape_with_context, scraper, club)
                    if result.error:
                        metrics.error += 1
                    elif result.num_shows == 0:
                        metrics.none_resp += 1
                    else:
                        metrics.ok += 1
                    # Persist immediately after this club completes scraping.
                    # db_lock serializes writes so insert_club_result() is called
                    # from at most one thread at a time, ensuring ShowService thread safety.
                    try:
                        async with db_lock:
                            club_db_result = await loop.run_in_executor(
                                None, self.result_processor.insert_club_result, result
                            )
                            total_db_result = total_db_result + club_db_result
                    except Exception as insert_err:
                        Logger.error(f"Failed to persist shows for club '{club.name}': {insert_err}")
                    return result, metrics
                except Exception as e:
                    Logger.error(f"Failed to scrape club '{club.name}': {e}")
                    result = ClubScrapingResult(
                        club_name=club.name,
                        shows=[],
                        execution_time=0.0,
                        error=str(e),
                        club_id=club.id,
                    )
                    metrics.error += 1
                    return result, metrics

        task_results = await asyncio.gather(*[scrape_one(club) for club in clubs])

        results: List[ClubScrapingResult] = []
        summary = ScrapingRunSummary()
        skipped = 0
        for result, metrics in task_results:
            if result is not None:
                results.append(result)
            if metrics is not None:
                summary.per_club.append(metrics)
            elif result is None:
                skipped += 1
        if skipped > 0:
            Logger.warn(f"{skipped} club(s) skipped: no scraper key or no matching scraper class")
        return results, summary, total_db_result

    def _emit_summary(self, summary: ScrapingRunSummary) -> None:
        payload = {
            "total_clubs": summary.total_clubs,
            "clubs_ok": summary.clubs_ok,
            "clubs_empty": summary.clubs_empty,
            "clubs_errored": summary.clubs_errored,
            "per_club": [m.as_log_dict() for m in summary.per_club],
        }
        Logger.info(f"scrape_all summary: {json.dumps(payload)}")

    def _check_and_alert(self, summary: ScrapingRunSummary) -> None:
        failing = summary.below_threshold(self.success_rate_threshold)
        if not failing:
            return
        Logger.warn(
            f"{len(failing)} domain(s) below {self.success_rate_threshold}% success threshold: "
            + ", ".join(m.club_name for m in failing)
        )
        self._send_slack_alert(failing)

    def _send_slack_alert(self, failing: List[DomainRequestMetrics]) -> None:
        # Import guard is separate from execution guard so misconfigured environments
        # surface a distinct error rather than silently swallowing an ImportError.
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            from laughtrack.infrastructure.monitoring.channels import SlackAlertChannel
            from laughtrack.infrastructure.monitoring.alerts import Alert, AlertSeverity
        except ImportError as e:  # pragma: no cover
            Logger.error(f"Monitoring package not available; skipping Slack alert: {e}")
            return

        try:
            config = MonitoringConfig.default()
            if not config.is_slack_configured() or not config.slack_webhook_url:
                Logger.warn("Slack webhook not configured; skipping scraping success-rate alert")
                return

            lines = [
                f"• {m.club_name}: {m.success_rate:.0f}% ({m.ok}/{m.total} ok, "
                f"{m.none_resp} empty, {m.error} errors)"
                for m in failing
            ]
            alert = Alert(
                id=str(uuid.uuid4()),
                title=f"Scraping success rate below {self.success_rate_threshold:.0f}% threshold",
                description="\n".join(lines),
                severity=AlertSeverity.HIGH,
                timestamp=datetime.now(timezone.utc),
                source="ScrapingService",
                metadata={
                    "threshold_pct": self.success_rate_threshold,
                    "failing_domains": [m.club_name for m in failing],
                },
            )
            channel = SlackAlertChannel(
                webhook_url=config.slack_webhook_url,
                channel=config.slack_channel,
            )
            # Guard against being called from an already-running event loop
            # (e.g. async test runner, FastAPI handler) to avoid RuntimeError.
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    executor.submit(asyncio.run, channel.send_alert(alert)).result()
            else:
                asyncio.run(channel.send_alert(alert))
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to send Slack scraping alert: {e}")


__all__ = ["ScrapingService"]
