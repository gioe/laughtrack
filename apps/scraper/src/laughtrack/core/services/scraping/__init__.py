"""Scraping service package (public path preserved)."""

import asyncio
import json
import os
import uuid
from collections import defaultdict
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
_OUTAGE_THRESHOLD = 0.80  # fraction of clubs per scraper type that must fail to trigger a summary alert
_DISCORD_DESCRIPTION_LIMIT = 2048  # conservative limit; Discord's actual embed description cap is 4096
_TEXT_CHANNEL_BODY_LIMIT = 8000  # soft cap for email/webhook channels; no hard limit but avoids huge payloads


def _truncate_description_lines(lines: List[str], limit: int = _DISCORD_DESCRIPTION_LIMIT) -> str:
    """Join lines into a Discord embed description, truncating with a count suffix if over limit.

    Uses greedy packing: skips lines that don't fit but continues checking subsequent (shorter)
    lines, so a single long line doesn't silently drop all remaining content.
    """
    if not lines:
        return ""
    full = "\n".join(lines)
    if len(full) <= limit:
        return full
    kept: List[str] = []
    for i, line in enumerate(lines):
        body_with_line = "\n".join(kept + [line])
        # Conservatively estimate the suffix as if all remaining lines are omitted,
        # so we never overshoot the limit when the real suffix is computed at the end.
        omitted_estimate = len(lines) - len(kept) - 1  # lines after this one + this one if skipped
        suffix_estimate = f"\n...and {omitted_estimate} more" if omitted_estimate > 0 else ""
        if len(body_with_line) + len(suffix_estimate) <= limit:
            kept.append(line)
        # else: skip this line and try the next one (greedy packing)
    omitted = len(lines) - len(kept)
    if omitted > 0:
        prefix = "\n".join(kept)
        suffix = f"...and {omitted} more"
        return f"{prefix}\n{suffix}" if prefix else suffix
    return "\n".join(kept)


def _scrape_with_context(scraper: BaseScraper, club: Club) -> ClubScrapingResult:
    """Run scrape_with_result() inside the club's log context (thread-safe)."""
    Logger.reset_error_count()
    try:
        with Logger.use_context(club.as_context()):
            result = scraper.scrape_with_result()
    except Exception:
        Logger.get_error_count()  # deactivate counter even when scrape raises
        raise
    result.error_log_count = Logger.get_error_count()
    return result


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
        self._log_configured_alert_channels()

    def _log_configured_alert_channels(self) -> None:
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            config = MonitoringConfig.default()
            channels = config.get_configured_channels()
        except Exception as e:  # pragma: no cover - defensive
            Logger.warn(f"Could not determine configured alert channels: {e}")
            return
        if channels:
            Logger.info(f"Alert channels configured: {', '.join(channels)}")
        else:
            Logger.warn("No alert channels configured (email, Discord, or webhook) — failures will not be reported")

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
        self._send_run_summary(summary, db_result)
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
        total_shows = sum(r.num_shows for r in results)
        club_label = clubs[0].name if len(clubs) == 1 else f"{len(clubs)} clubs"
        Logger.info(f"Scraped {total_shows} shows for {club_label}")

    def scrape_by_scraper_type(self, scraper_type: Optional[str] = None) -> None:
        Logger.info(f"Starting scrape of all clubs using scraper type: {scraper_type}")
        scraper_type = scraper_type or self.selector.get_scraper_type_selection()
        if not scraper_type:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
        clubs = self.club_handler.get_clubs_for_scraper(scraper_type)
        results, _, db_result = self._scrape_clubs_with_metrics(clubs)
        self.result_processor.process_results(results, db_result)
        total_shows = sum(r.num_shows for r in results)
        Logger.info(f"Scraped {total_shows} shows for {scraper_type}")

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
                metrics = DomainRequestMetrics(club_name=club.name, club_id=getattr(club, "id", None), scraper_type=key)
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
                            # Push club context before run_in_executor so the thread
                            # inherits it via contextvars copy — ensures DB log lines
                            # show the correct club name/id instead of club=-.
                            with Logger.use_context(club.as_context()):
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

        outage_lines, individual_failing = self._classify_failing(failing, summary)
        warn_parts = outage_lines + [m.club_name for m in individual_failing]
        Logger.warn(
            f"{len(failing)} domain(s) below {self.success_rate_threshold}% success threshold: "
            + ", ".join(warn_parts)
        )
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            config = MonitoringConfig.default()
            channels = config.get_configured_channels()
        except ImportError as e:  # pragma: no cover
            Logger.error(f"Monitoring package not available; skipping alerts: {e}")
            channels = ["discord"]

        for channel in channels:
            if channel == "discord":
                self._send_discord_alert(individual_failing, outage_lines=outage_lines)
            elif channel == "email":
                self._send_email_alert(individual_failing, outage_lines=outage_lines)
            elif channel == "webhook":
                self._send_webhook_alert(individual_failing, outage_lines=outage_lines)

    def _classify_failing(
        self, failing: List[DomainRequestMetrics], summary: ScrapingRunSummary
    ) -> tuple[List[str], List[DomainRequestMetrics]]:
        """Split failing clubs into provider-wide outages and individual failures.

        When >=80% of all clubs sharing a scraper type are below the success-rate
        threshold, emit one summary line instead of listing each club individually.

        Returns:
            outage_lines: one summary string per scraper type that crossed the outage threshold
            individual_failing: remaining failing clubs whose type is below the outage threshold
        """
        all_by_type: dict[str, list] = defaultdict(list)
        for m in summary.per_club:
            if m.scraper_type:
                all_by_type[m.scraper_type].append(m)

        failing_by_type: dict[str, list] = defaultdict(list)
        no_type_failing: List[DomainRequestMetrics] = []
        for m in failing:
            if m.scraper_type and m.scraper_type in all_by_type:
                failing_by_type[m.scraper_type].append(m)
            else:
                no_type_failing.append(m)

        outage_lines: List[str] = []
        individual_failing: List[DomainRequestMetrics] = list(no_type_failing)

        for scraper_type, failed_clubs in failing_by_type.items():
            total_of_type = len(all_by_type[scraper_type])
            failed_count = len(failed_clubs)
            if total_of_type > 0 and failed_count / total_of_type >= _OUTAGE_THRESHOLD:
                outage_lines.append(
                    f"{scraper_type} appears to be down ({failed_count}/{total_of_type} venues failed)"
                )
            else:
                individual_failing.extend(failed_clubs)

        return outage_lines, individual_failing

    def _send_discord_alert(self, failing: List[DomainRequestMetrics], *, outage_lines: Optional[List[str]] = None) -> None:
        # Import guard is separate from execution guard so misconfigured environments
        # surface a distinct error rather than silently swallowing an ImportError.
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            from gioe_libs.alerting import DiscordAlertChannel, Alert as GioeAlert, AlertSeverity as GioeSeverity
        except ImportError as e:  # pragma: no cover
            Logger.error(f"Monitoring package not available; skipping Discord alert: {e}")
            return

        try:
            config = MonitoringConfig.default()
            if not config.is_discord_configured() or not config.discord_webhook_url:
                Logger.warn("Discord webhook not configured; skipping scraping success-rate alert")
                return

            all_lines: List[str] = []
            if outage_lines:
                all_lines.extend(f"⚠️ {l}" for l in outage_lines)
            all_lines.extend(
                f"• {m.club_name}: {m.success_rate:.0f}% ({m.ok}/{m.total} ok, "
                f"{m.none_resp} empty, {m.error} errors)"
                for m in failing
            )
            if not all_lines:
                return
            gioe_alert = GioeAlert(
                title=f"Scraping success rate below {self.success_rate_threshold:.0f}% threshold",
                message=_truncate_description_lines(all_lines),
                severity=GioeSeverity.HIGH,
                metadata={
                    "threshold_pct": self.success_rate_threshold,
                    "outage_summaries": list(outage_lines or []),
                    "failing_domains": [m.club_name for m in failing],
                },
            )
            channel = DiscordAlertChannel(webhook_url=config.discord_webhook_url)
            channel.send(gioe_alert)
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to send Discord scraping alert: {e}")

    def _send_run_summary(self, summary: ScrapingRunSummary, db_result: "DatabaseOperationResult") -> None:
        """Dispatch the post-run summary to all configured alert channels."""
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            config = MonitoringConfig.default()
            channels = config.get_configured_channels()
        except ImportError as e:  # pragma: no cover
            Logger.error(f"Monitoring package not available; skipping run summary: {e}")
            channels = ["discord"]

        for channel in channels:
            if channel == "discord":
                self._send_discord_run_summary(summary, db_result)
            elif channel == "email":
                self._send_email_run_summary(summary, db_result)
            elif channel == "webhook":
                self._send_webhook_run_summary(summary, db_result)

    def _send_discord_run_summary(self, summary: ScrapingRunSummary, db_result: "DatabaseOperationResult") -> None:
        """Post an unconditional run summary to Discord after every scrape_all_clubs run."""
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            from gioe_libs.alerting import DiscordAlertChannel, Alert as GioeAlert, AlertSeverity as GioeSeverity
        except ImportError as e:  # pragma: no cover
            Logger.error(f"Monitoring package not available; skipping Discord run summary: {e}")
            return

        try:
            config = MonitoringConfig.default()
            if not config.is_discord_configured() or not config.discord_webhook_url:
                Logger.warn("Discord webhook not configured; skipping run summary")
                return

            title = f"Scrape run: {summary.clubs_ok}/{summary.total_clubs} clubs OK"

            failing = [m for m in summary.per_club if m.success_rate < self.success_rate_threshold]
            body_lines = [
                f"Shows scraped: {db_result.total}",
                f"Shows inserted: {db_result.inserts}",
                f"Shows updated: {db_result.updates}",
            ]
            if failing:
                body_lines += ["", f"**{len(failing)} club(s) below threshold:**"]
                for m in failing:
                    body_lines.append(
                        f"⚠️ {m.club_name}: {m.success_rate:.0f}% ({m.ok}/{m.total} ok, "
                        f"{m.none_resp} empty, {m.error} errors)"
                    )
            else:
                body_lines.append("All clubs at or above threshold ✅")

            gioe_alert = GioeAlert(
                title=title,
                message=_truncate_description_lines(body_lines),
                severity=GioeSeverity.LOW,
                metadata={
                    "clubs_ok": summary.clubs_ok,
                    "total_clubs": summary.total_clubs,
                    "shows_total": db_result.total,
                    "shows_inserted": db_result.inserts,
                    "shows_updated": db_result.updates,
                },
            )
            channel = DiscordAlertChannel(webhook_url=config.discord_webhook_url)
            channel.send(gioe_alert)
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to send Discord run summary: {e}")

    def _send_email_run_summary(self, summary: ScrapingRunSummary, db_result: "DatabaseOperationResult") -> None:
        """Post an unconditional run summary to the email channel after every scrape_all_clubs run."""
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            from laughtrack.infrastructure.monitoring.channels import EmailAlertChannel
            from gioe_libs.alerting import Alert as GioeAlert, AlertSeverity as GioeSeverity
        except ImportError as e:  # pragma: no cover
            Logger.error(f"Monitoring package not available; skipping email run summary: {e}")
            return

        try:
            config = MonitoringConfig.default()
            if not config.is_email_configured() or not config.alert_recipients:
                Logger.warn("Email not configured; skipping run summary")
                return

            title = f"Scrape run: {summary.clubs_ok}/{summary.total_clubs} clubs OK"
            body_lines = [
                f"Shows scraped: {db_result.total}",
                f"Shows inserted: {db_result.inserts}",
                f"Shows updated: {db_result.updates}",
                "",
                "Per-club breakdown:",
            ]
            for m in summary.per_club:
                icon = "OK" if m.success_rate >= self.success_rate_threshold else "WARN"
                body_lines.append(
                    f"[{icon}] {m.club_name}: {m.success_rate:.0f}% ({m.ok}/{m.total} ok, "
                    f"{m.none_resp} empty, {m.error} errors)"
                )

            gioe_alert = GioeAlert(
                title=title,
                message=_truncate_description_lines(body_lines, limit=_TEXT_CHANNEL_BODY_LIMIT),
                severity=GioeSeverity.LOW,
                metadata={
                    "clubs_ok": summary.clubs_ok,
                    "total_clubs": summary.total_clubs,
                    "shows_total": db_result.total,
                    "shows_inserted": db_result.inserts,
                    "shows_updated": db_result.updates,
                },
            )
            channel = EmailAlertChannel(recipients=config.alert_recipients)
            channel.send(gioe_alert)
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to send email run summary: {e}")

    def _send_webhook_run_summary(self, summary: ScrapingRunSummary, db_result: "DatabaseOperationResult") -> None:
        """Post an unconditional run summary to the webhook channel after every scrape_all_clubs run."""
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            from gioe_libs.alerting import WebhookAlertChannel, Alert as GioeAlert, AlertSeverity as GioeSeverity
        except ImportError as e:  # pragma: no cover
            Logger.error(f"Monitoring package not available; skipping webhook run summary: {e}")
            return

        try:
            config = MonitoringConfig.default()
            if not config.is_webhook_configured() or not config.webhook_url:
                Logger.warn("Webhook not configured; skipping run summary")
                return

            title = f"Scrape run: {summary.clubs_ok}/{summary.total_clubs} clubs OK"
            body_lines = [
                f"Shows scraped: {db_result.total}",
                f"Shows inserted: {db_result.inserts}",
                f"Shows updated: {db_result.updates}",
                "",
                "Per-club breakdown:",
            ]
            for m in summary.per_club:
                icon = "OK" if m.success_rate >= self.success_rate_threshold else "WARN"
                body_lines.append(
                    f"[{icon}] {m.club_name}: {m.success_rate:.0f}% ({m.ok}/{m.total} ok, "
                    f"{m.none_resp} empty, {m.error} errors)"
                )

            gioe_alert = GioeAlert(
                title=title,
                message=_truncate_description_lines(body_lines, limit=_TEXT_CHANNEL_BODY_LIMIT),
                severity=GioeSeverity.LOW,
                metadata={
                    "clubs_ok": summary.clubs_ok,
                    "total_clubs": summary.total_clubs,
                    "shows_total": db_result.total,
                    "shows_inserted": db_result.inserts,
                    "shows_updated": db_result.updates,
                },
            )
            channel = WebhookAlertChannel(url=config.webhook_url, headers=config.webhook_headers)
            channel.send(gioe_alert)
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to send webhook run summary: {e}")

    def _send_email_alert(self, failing: List[DomainRequestMetrics], *, outage_lines: Optional[List[str]] = None) -> None:
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            from laughtrack.infrastructure.monitoring.channels import EmailAlertChannel
            from gioe_libs.alerting import Alert as GioeAlert, AlertSeverity as GioeSeverity
        except ImportError as e:  # pragma: no cover
            Logger.error(f"Monitoring package not available; skipping email alert: {e}")
            return

        try:
            config = MonitoringConfig.default()
            if not config.is_email_configured() or not config.alert_recipients:
                Logger.warn("Email not configured; skipping scraping success-rate alert")
                return

            all_lines: List[str] = []
            if outage_lines:
                all_lines.extend(f"⚠️ {l}" for l in outage_lines)
            all_lines.extend(
                f"• {m.club_name}: {m.success_rate:.0f}% ({m.ok}/{m.total} ok, "
                f"{m.none_resp} empty, {m.error} errors)"
                for m in failing
            )
            if not all_lines:
                return
            gioe_alert = GioeAlert(
                title=f"Scraping success rate below {self.success_rate_threshold:.0f}% threshold",
                message=_truncate_description_lines(all_lines, limit=_TEXT_CHANNEL_BODY_LIMIT),
                severity=GioeSeverity.HIGH,
                metadata={
                    "threshold_pct": self.success_rate_threshold,
                    "outage_summaries": list(outage_lines or []),
                    "failing_domains": [m.club_name for m in failing],
                },
            )
            channel = EmailAlertChannel(recipients=config.alert_recipients)
            channel.send(gioe_alert)
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to send email scraping alert: {e}")

    def _send_webhook_alert(self, failing: List[DomainRequestMetrics], *, outage_lines: Optional[List[str]] = None) -> None:
        try:
            from laughtrack.infrastructure.config.monitoring_config import MonitoringConfig
            from gioe_libs.alerting import WebhookAlertChannel, Alert as GioeAlert, AlertSeverity as GioeSeverity
        except ImportError as e:  # pragma: no cover
            Logger.error(f"Monitoring package not available; skipping webhook alert: {e}")
            return

        try:
            config = MonitoringConfig.default()
            if not config.is_webhook_configured() or not config.webhook_url:
                Logger.warn("Webhook not configured; skipping scraping success-rate alert")
                return

            all_lines: List[str] = []
            if outage_lines:
                all_lines.extend(f"⚠️ {l}" for l in outage_lines)
            all_lines.extend(
                f"• {m.club_name}: {m.success_rate:.0f}% ({m.ok}/{m.total} ok, "
                f"{m.none_resp} empty, {m.error} errors)"
                for m in failing
            )
            if not all_lines:
                return
            gioe_alert = GioeAlert(
                title=f"Scraping success rate below {self.success_rate_threshold:.0f}% threshold",
                message=_truncate_description_lines(all_lines, limit=_TEXT_CHANNEL_BODY_LIMIT),
                severity=GioeSeverity.HIGH,
                metadata={
                    "threshold_pct": self.success_rate_threshold,
                    "outage_summaries": list(outage_lines or []),
                    "failing_domains": [m.club_name for m in failing],
                },
            )
            channel = WebhookAlertChannel(url=config.webhook_url, headers=config.webhook_headers)
            channel.send(gioe_alert)
        except Exception as e:  # pragma: no cover - defensive
            Logger.error(f"Failed to send webhook scraping alert: {e}")


__all__ = ["ScrapingService"]
