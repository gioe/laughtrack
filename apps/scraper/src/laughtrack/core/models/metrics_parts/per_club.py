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
    errors: Optional[int] = None
    success_rate: Optional[float] = None
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
    # Count of shows transformed with an empty tickets list (pipeline WARNs per
    # show, shows still persisted). Lands in scraper_run_clubs.raw_stat via
    # asdict so Grafana can chart it without a schema migration (TASK-3629).
    ticketless_shows: Optional[int] = None
    # Synthetic-proxy discriminator carried from ClubScrapingResult so dashboards
    # and the postgres snapshot can attribute a per-company organizer scrape to
    # its ProductionCompany without inspecting club_id sign. Replaces the older
    # negative-club-id encoding (TASK-2552, TASK-2565). For synthetic rows,
    # club_id is typically the SYNTHETIC_PROXY_PLACEHOLDER_ID sentinel
    # which the postgres FK-membership check nulls before INSERT.
    is_synthetic: bool = False
    production_company_id: Optional[int] = None
