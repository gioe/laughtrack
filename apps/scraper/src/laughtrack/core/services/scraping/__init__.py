"""Scraping service package (public path preserved)."""

import asyncio
import concurrent.futures
import json
import os
import threading
import uuid
from collections import defaultdict
from datetime import datetime, timezone
import copy
from typing import Optional, List

from laughtrack.app.scraper_resolver import ScraperResolver
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.production_company.handler import ProductionCompanyHandler
from laughtrack.core.entities.production_company.model import ProductionCompany
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


def _build_proxy_club(venue_club: Club, company: ProductionCompany) -> Club:
    """Create a Club proxy that uses the production company's scraping_url.

    Copies the venue club (preserving its id, timezone, etc.) but overrides the
    scraping_url with the production company's URL. The scraper resolver uses
    club.scraper to find the right scraper class, so the venue club must already
    have a compatible scraper key configured.
    """
    proxy = copy.copy(venue_club)
    proxy.scraping_url = company.scraping_url or ""
    # Tag so scrape_one can stamp production_company_id before persistence
    proxy._production_company_id = company.id  # type: ignore[attr-defined]
    proxy._production_company = company  # type: ignore[attr-defined]
    return proxy


def _build_source_proxy_club(club: Club, source: ScrapingSource) -> Club:
    """Copy a club and activate a specific scraping source for one scrape attempt."""
    proxy = copy.copy(club)
    proxy.activate_scraping_source(source)
    return proxy


class ScrapingService:
    def __init__(self, success_rate_threshold: float = _DEFAULT_SUCCESS_RATE_THRESHOLD):
        self.club_handler = ClubHandler()
        self.production_company_handler = ProductionCompanyHandler()
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

    def _filter_off_season_festivals(self, clubs: List[Club]) -> List[Club]:
        """Remove festival clubs that are outside their active scraping window.

        Festivals only need scraping when they have shows within the next 90 days.
        Regular clubs (club_type != 'festival') are always included.
        """
        festivals = [c for c in clubs if c.club_type == "festival"]
        if not festivals:
            return clubs

        active_festival_ids = self.club_handler.get_active_festival_ids()
        kept: List[Club] = []
        skipped: List[str] = []
        for club in clubs:
            if club.club_type == "festival" and club.id not in active_festival_ids:
                skipped.append(club.name)
            else:
                kept.append(club)

        if skipped:
            Logger.info(
                f"Skipping {len(skipped)} off-season festival(s): {', '.join(skipped)}"
            )

        return kept

    def scrape_all_clubs(self) -> List[ClubScrapingResult]:
        Logger.info("Starting scrape of all clubs...")
        clubs = self.club_handler.get_all_clubs()
        if not clubs:
            raise ValueError("No clubs found with valid scraper configurations")
        Logger.info(f"Found {len(clubs)} clubs with scraper configurations")
        clubs = self._filter_off_season_festivals(clubs)
        self._try_validate_scraper_keys(clubs)
        results, summary, db_result = self._scrape_clubs_with_metrics(clubs)

        # Scrape production companies after regular clubs
        pc_results, pc_summary, pc_db_result = self._scrape_production_companies(clubs)
        results.extend(pc_results)
        summary = summary.merge(pc_summary)
        db_result = db_result + pc_db_result

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
        self.club_handler.refresh_club_total_shows()
        total_shows = sum(r.num_shows for r in results)
        club_label = clubs[0].name if len(clubs) == 1 else f"{len(clubs)} clubs"
        if total_shows == 0 and len(results) == 1:
            r = results[0]
            diag_suffix = (
                f" [http={r.http_status}, bot_block={r.bot_block_detected}, "
                f"provider={r.bot_block_provider}, type={r.bot_block_type}, "
                f"source={r.bot_block_source}, stage={r.bot_block_stage}, "
                f"fallback={r.playwright_fallback_used}, "
                f"items_before_filter={r.items_before_filter}]"
            )
            Logger.info(f"Scraped {total_shows} shows for {club_label}{diag_suffix}")
        else:
            Logger.info(f"Scraped {total_shows} shows for {club_label}")

    def scrape_by_scraper_type(self, scraper_type: Optional[str] = None) -> None:
        Logger.info(f"Starting scrape of all clubs using scraper type: {scraper_type}")
        scraper_type = scraper_type or self.selector.get_scraper_type_selection()
        if not scraper_type:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
        clubs = self.club_handler.get_clubs_for_scraper(scraper_type)
        results, _, db_result = self._scrape_clubs_with_metrics(clubs)
        self.result_processor.process_results(results, db_result)
        self.club_handler.refresh_club_total_shows()
        total_shows = sum(r.num_shows for r in results)
        Logger.info(f"Scraped {total_shows} shows for {scraper_type}")

    # --- Production company helpers ---

    def _scrape_production_companies(
        self, clubs: List[Club]
    ) -> tuple[List[ClubScrapingResult], ScrapingRunSummary, DatabaseOperationResult]:
        """Scrape all production companies and map shows to venue clubs.

        For each production company with a scraping_url, builds a proxy Club from
        the company's first mapped venue, runs the matching scraper, then stamps
        production_company_id on every resulting Show.

        Args:
            clubs: The full list of active clubs (used to look up venue details).

        Returns:
            Tuple of (scraping results, scraping run summary, database operation result).
        """
        companies = self.production_company_handler.get_all_production_companies()
        if not companies:
            return [], ScrapingRunSummary(), DatabaseOperationResult()

        club_by_id = {c.id: c for c in clubs}
        proxy_clubs: List[tuple[Club, ProductionCompany]] = []

        for company in companies:
            if not company.venue_club_ids:
                Logger.warn(f"Production company '{company.name}' has no venue mappings — skipping")
                continue

            # Use the first mapped venue as the primary club for this scrape
            primary_club_id = company.venue_club_ids[0]
            venue_club = club_by_id.get(primary_club_id)
            if not venue_club:
                Logger.warn(
                    f"Production company '{company.name}': primary venue club_id={primary_club_id} "
                    f"not found in active clubs — skipping"
                )
                continue

            proxy = _build_proxy_club(venue_club, company)
            proxy_clubs.append((proxy, company))

        if not proxy_clubs:
            Logger.info("No production companies eligible for scraping")
            return [], ScrapingRunSummary(), DatabaseOperationResult()

        Logger.info(f"Scraping {len(proxy_clubs)} production company(ies)")

        # Scrape using the same concurrent infrastructure as regular clubs.
        # production_company_id is stamped on shows inside scrape_one via the
        # _production_company_id attribute on the proxy Club, before persistence.
        proxies_only = [pc[0] for pc in proxy_clubs]
        results, pc_summary, db_result = self._scrape_clubs_with_metrics(proxies_only)

        # Clean up non-matching shows: the upsert uses COALESCE which preserves
        # old production_company_id values when the incoming value is NULL.
        # For companies with keyword filters, clear the stale stamps.
        for proxy, company in proxy_clubs:
            if company.show_name_keywords:
                venue_club_id = company.venue_club_ids[0] if company.venue_club_ids else None
                if venue_club_id:
                    self.production_company_handler.clear_unmatched_shows(company, venue_club_id)

        return results, pc_summary, db_result

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

    @staticmethod
    def _sorted_enabled_sources(club: Club) -> List[ScrapingSource]:
        return sorted(
            [source for source in club.scraping_sources if source.enabled],
            key=lambda source: (source.priority, source.id or 0),
        )

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
        max_concurrent = self._max_concurrent_clubs
        Logger.warn(f"Scraping {len(clubs)} clubs with max_concurrent_clubs={max_concurrent}")
        semaphore = asyncio.Semaphore(max_concurrent)
        loop = asyncio.get_running_loop()
        executor = concurrent.futures.ThreadPoolExecutor(thread_name_prefix="scraper-club")
        loop.set_default_executor(executor)
        total_db_result = DatabaseOperationResult()
        # db_lock serializes all DB writes: only one club writes at a time,
        # which keeps ShowService thread-safe regardless of its internals.
        db_lock = asyncio.Lock()
        self.result_processor.start_run()

        async def scrape_one(
            club: Club,
        ) -> tuple[Optional[ClubScrapingResult], Optional[DomainRequestMetrics]]:
            nonlocal total_db_result
            sources = self._sorted_enabled_sources(club)
            if not sources and club.scraping_source is not None:
                sources = [club.scraping_source]
            if not sources:
                Logger.warn(f"Club '{club.name}' has no scraper key configured; skipping")
                return None, None
            async with semaphore:
                metrics = DomainRequestMetrics(
                    club_name=club.name,
                    club_id=getattr(club, "id", None),
                    scraper_type=sources[0].scraper_key,
                )
                metrics.total += 1
                _PER_CLUB_TIMEOUT = 300  # seconds; unblocks gather if a thread stalls on network
                last_result: Optional[ClubScrapingResult] = None
                last_key = sources[0].scraper_key
                for index, source in enumerate(sources):
                    attempt_club = _build_source_proxy_club(club, source)
                    key = source.scraper_key
                    last_key = key
                    scraper_cls = self._scraping_resolver.get(key)
                    if not scraper_cls:
                        Logger.warn(f"No scraper found for club '{club.name}' with key '{key}'")
                        continue
                    if index > 0:
                        Logger.warn(
                            f"Club '{club.name}': trying fallback source priority={source.priority} "
                            f"with scraper '{key}'"
                        )
                    try:
                        scraper: BaseScraper = scraper_cls(attempt_club, proxy_pool=self.proxy_pool)
                        try:
                            result = await asyncio.wait_for(
                                loop.run_in_executor(None, _scrape_with_context, scraper, attempt_club),
                                timeout=_PER_CLUB_TIMEOUT,
                            )
                        except asyncio.TimeoutError:
                            Logger.warn(
                                f"scrape_one: club '{club.name}' timed out after {_PER_CLUB_TIMEOUT}s "
                                f"with scraper '{key}'"
                            )
                            last_result = ClubScrapingResult(
                                club_name=club.name,
                                shows=[],
                                execution_time=float(_PER_CLUB_TIMEOUT),
                                error=f"timed out after {_PER_CLUB_TIMEOUT}s",
                                club_id=club.id,
                            )
                            continue

                        last_result = result
                        if (result.error or result.num_shows == 0) and index < len(sources) - 1:
                            reason = result.error or "zero shows"
                            Logger.warn(
                                f"Club '{club.name}': scraper '{key}' produced {reason}; trying fallback"
                            )
                            continue

                        # Stamp production_company_id on matching shows before persistence
                        # when scraping via a production company proxy club.
                        # If the company has show_name_keywords configured, only shows
                        # whose name matches at least one keyword get stamped.
                        pc_id = getattr(club, "_production_company_id", None)
                        if pc_id is not None:
                            pc: Optional[ProductionCompany] = getattr(club, "_production_company", None)
                            stamped = 0
                            for show in result.shows:
                                if pc is None or pc.matches_show_name(show.name):
                                    show.production_company_id = pc_id
                                    stamped += 1
                            if pc and pc.show_name_keywords and stamped < len(result.shows):
                                Logger.info(
                                    f"Production company '{pc.name}': stamped {stamped}/{len(result.shows)} "
                                    f"shows (filtered by keywords)"
                                )

                        # Persist immediately after this club completes scraping.
                        # db_lock serializes writes so insert_club_result() is called
                        # from at most one thread at a time, ensuring ShowService thread safety.
                        _DB_WRITE_TIMEOUT = 60  # seconds; unblocks db_lock if Neon connection drops
                        try:
                            async with db_lock:
                                # Push club context before run_in_executor so the thread
                                # inherits it via contextvars copy - ensures DB log lines
                                # show the correct club name/id instead of club=-.
                                with Logger.use_context(club.as_context()):
                                    try:
                                        club_db_result = await asyncio.wait_for(
                                            loop.run_in_executor(
                                                None, self.result_processor.insert_club_result, result
                                            ),
                                            timeout=_DB_WRITE_TIMEOUT,
                                        )
                                    except asyncio.TimeoutError:
                                        Logger.warn(
                                            f"scrape_one: DB write for club '{club.name}' timed out after "
                                            f"{_DB_WRITE_TIMEOUT}s - skipping persist"
                                        )
                                        club_db_result = DatabaseOperationResult()
                                total_db_result = total_db_result + club_db_result
                        except Exception as insert_err:
                            Logger.error(f"Failed to persist shows for club '{club.name}': {insert_err}")

                        metrics.scraper_type = key
                        if result.error:
                            metrics.error += 1
                        elif result.num_shows == 0:
                            metrics.none_resp += 1
                        else:
                            metrics.ok += 1
                        return result, metrics
                    except Exception as e:
                        Logger.error(f"Failed to scrape club '{club.name}' with scraper '{key}': {e}")
                        last_result = ClubScrapingResult(
                            club_name=club.name,
                            shows=[],
                            execution_time=0.0,
                            error=str(e),
                            club_id=club.id,
                        )
                        if index == len(sources) - 1:
                            break

                metrics.scraper_type = last_key
                if last_result is None:
                    metrics.error += 1
                    return ClubScrapingResult(
                        club_name=club.name,
                        shows=[],
                        execution_time=0.0,
                        error="no enabled scraping source could be resolved",
                        club_id=club.id,
                    ), metrics
                if last_result.error:
                    metrics.error += 1
                elif last_result.num_shows == 0:
                    metrics.none_resp += 1
                else:
                    metrics.ok += 1
                return last_result, metrics

        # Close the shared Playwright browser while the event loop is still running
        # so Playwright objects are torn down on the correct loop — making the
        # atexit handler a safe no-op and preventing the 90-minute CI timeout.
        # The finally block ensures teardown even if gather raises unexpectedly.
        from laughtrack.foundation.infrastructure.http.client import close_js_browser  # noqa: PLC0415
        try:
            task_results = await asyncio.gather(*[scrape_one(club) for club in clubs])
        finally:
            _BROWSER_CLOSE_TIMEOUT = 30
            try:
                await asyncio.wait_for(close_js_browser(), timeout=_BROWSER_CLOSE_TIMEOUT)
            except asyncio.TimeoutError:
                Logger.warn(f"close_js_browser timed out after {_BROWSER_CLOSE_TIMEOUT}s — Playwright node may be unresponsive")
            # wait=True joins the worker threads before we enumerate. All futures
            # are already complete (gather() just returned), so the workers only
            # need one loop iteration to observe the shutdown flag and exit —
            # near-instant in practice. wait=False was racy with the subsequent
            # threading.enumerate(), producing a cosmetic "threads still alive"
            # WARNING because workers hadn't finished exiting their pool loop.
            executor.shutdown(wait=True)
            alive = [t.name for t in threading.enumerate() if t.name.startswith("scraper-club")]
            if alive:
                Logger.warn(f"scraper-club threads still alive after gather: {alive}")

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
            if not channel.send(gioe_alert):
                Logger.error(
                    f"Discord alert delivery failed (webhook may be expired or revoked): {config.discord_webhook_url[:60]}..."
                )
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
            if not channel.send(gioe_alert):
                Logger.error(
                    f"Discord run summary delivery failed (webhook may be expired or revoked): {config.discord_webhook_url[:60]}..."
                )
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
