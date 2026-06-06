"""Round-trip coverage for the typed synthetic-proxy discriminator (TASK-2565).

The pre-TASK-2565 code identified synthetic production_company proxies by their
negative ``Club.id`` (``id=-company.id`` in ``_build_synthetic_proxy_for_company``).
That implicit encoding had two failure modes the new typed discriminator avoids:
1. A future refactor could accidentally use a positive id for a synthetic proxy
   and silently route metrics under a real club.id.
2. Downstream consumers of ``PerClubStat.club_id`` had to know about the
   convention to interpret the row.

The new contract:
- ``Club.is_synthetic: bool`` is the authoritative flag.
- ``Club.production_company_id: Optional[int]`` carries the typed linkage.
- ``Club.id`` for synthetic proxies is ``Club.SYNTHETIC_PROXY_PLACEHOLDER_ID``
  (0), which never collides with a real ``clubs.id`` (Postgres SERIAL starts at
  1). The placeholder is filtered out by the postgres FK-membership check.
- The discriminator survives the full
  ``Club -> ClubScrapingResult -> PerClubStat`` aggregation path and round-trips
  through ``ScrapingMetricsSnapshot`` JSON.
"""

from __future__ import annotations

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.production_company.model import ProductionCompany
from laughtrack.core.models.metrics_parts import PerClubStat
from laughtrack.core.models.metrics_snapshot.blocks import (
    ClubsBlock,
    ErrorsBlock,
    SessionBlock,
    ShowsBlock,
)
from laughtrack.core.models.metrics_snapshot.snapshot import ScrapingMetricsSnapshot
from laughtrack.core.models.results import ClubScrapingResult
from laughtrack.core.services.metrics.aggregator import MetricsAggregator
from laughtrack.core.services.scraping import _build_synthetic_proxy_for_company


_ENCORE_ORGANIZER_URL = "https://www.eventbrite.com/o/encore-comedy/72313162423/"


def _encore_company() -> ProductionCompany:
    return ProductionCompany(
        id=42,
        name="Encore Comedy",
        slug="encore-comedy",
        scraping_url=_ENCORE_ORGANIZER_URL,
    )


def test_synthetic_proxy_uses_typed_flag_not_negative_id():
    """The proxy must be discriminable via ``is_synthetic`` rather than by
    inspecting the sign of ``Club.id``. The placeholder id is the documented
    sentinel and is never the negation of company.id."""
    company = _encore_company()

    proxy = _build_synthetic_proxy_for_company(company)

    assert proxy is not None
    assert proxy.is_synthetic is True
    assert proxy.id == Club.SYNTHETIC_PROXY_PLACEHOLDER_ID
    assert proxy.id != -company.id
    assert proxy.production_company_id == company.id
    assert proxy.production_company is company


def test_real_club_defaults_are_non_synthetic():
    real = Club(
        id=7,
        name="Real Venue",
        address="",
        website="",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
    )

    assert real.is_synthetic is False
    assert real.production_company_id is None
    assert real.production_company is None


def test_discriminator_survives_aggregation_to_per_club_stat():
    """MetricsAggregator must carry is_synthetic and production_company_id from
    ClubScrapingResult into PerClubStat so dashboards and the postgres snapshot
    can attribute the row to a ProductionCompany without inspecting club_id."""
    company = _encore_company()
    synthetic_result = ClubScrapingResult(
        club_name="Encore Comedy (organizer)",
        shows=[],
        execution_time=0.5,
        club_id=Club.SYNTHETIC_PROXY_PLACEHOLDER_ID,
        is_synthetic=True,
        production_company_id=company.id,
    )
    real_result = ClubScrapingResult(
        club_name="Real Venue",
        shows=[],
        execution_time=0.3,
        club_id=7,
    )

    session = MetricsAggregator().aggregate([synthetic_result, real_result])

    assert len(session.per_club_stats) == 2
    by_name = {s.club: s for s in session.per_club_stats}

    synthetic_stat = by_name["Encore Comedy (organizer)"]
    assert synthetic_stat.is_synthetic is True
    assert synthetic_stat.production_company_id == company.id
    assert synthetic_stat.club_id == Club.SYNTHETIC_PROXY_PLACEHOLDER_ID

    real_stat = by_name["Real Venue"]
    assert real_stat.is_synthetic is False
    assert real_stat.production_company_id is None
    assert real_stat.club_id == 7


def test_discriminator_round_trips_through_snapshot_json():
    """ScrapingMetricsSnapshot's JSON parser must preserve is_synthetic and
    production_company_id. Without parser changes the snapshot would lose the
    discriminator on every save/load cycle."""
    import datetime as _dt

    dt = _dt.datetime(2026, 6, 1, 12, 0, tzinfo=_dt.timezone.utc)
    stats = [
        PerClubStat(
            club="Encore Comedy (organizer)",
            club_id=Club.SYNTHETIC_PROXY_PLACEHOLDER_ID,
            num_shows=4,
            execution_time=2.1,
            success=True,
            is_synthetic=True,
            production_company_id=42,
        ),
        PerClubStat(
            club="Real Venue",
            club_id=7,
            num_shows=2,
            execution_time=1.2,
            success=True,
        ),
    ]
    snapshot = ScrapingMetricsSnapshot(
        timestamp=dt.isoformat(),
        datetime=dt,
        session=SessionBlock(duration_seconds=3.3, exported_at=dt.isoformat()),
        shows=ShowsBlock(),
        clubs=ClubsBlock(),
        errors=ErrorsBlock(),
        per_club_stats=stats,
    )

    payload = snapshot.to_full_json()
    rehydrated = ScrapingMetricsSnapshot.from_json(payload, dt.isoformat(), dt)

    assert len(rehydrated.per_club_stats) == 2
    synthetic = rehydrated.per_club_stats[0]
    real = rehydrated.per_club_stats[1]
    assert synthetic.is_synthetic is True
    assert synthetic.production_company_id == 42
    assert real.is_synthetic is False
    assert real.production_company_id is None
