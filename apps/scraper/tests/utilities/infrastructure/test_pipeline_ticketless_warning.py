"""Unit tests for the per-show ticketless WARN + diagnostics counter (TASK-3629)."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import List
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Pre-stub laughtrack.utilities.infrastructure so __init__.py does not run
# (it imports RateLimiter → gioe_libs, an optional dep not installed here).
# Setting __path__ lets Python find submodules (pipeline/, transformer/) on disk.
# ---------------------------------------------------------------------------
_SCRAPER_SRC = Path(__file__).parents[3] / "src"
_infra_stub = ModuleType("laughtrack.utilities.infrastructure")
_infra_stub.__path__ = [str(_SCRAPER_SRC / "laughtrack/utilities/infrastructure")]
_infra_stub.__package__ = "laughtrack.utilities.infrastructure"
sys.modules.setdefault("laughtrack.utilities.infrastructure", _infra_stub)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.foundation.infrastructure.http.diagnostics import (
    ScrapeDiagnostics,
    bind_diagnostics,
    reset_diagnostics,
)
from laughtrack.utilities.infrastructure.pipeline import ShowTransformationPipeline


def _club() -> Club:
    _c = Club(id=1, name='Test Club', address='123 Main St', website='https://testclub.example.com', popularity=0, zip_code='10001', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://testclub.example.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _raw_data(events):
    """Return a minimal EventListContainer-compatible object."""
    container = MagicMock()
    container.event_list = events
    return container


@dataclass
class _FakeShow:
    """Stand-in exposing only the attributes the pipeline touches."""

    name: str = "Test Show"
    tickets: List[object] = field(default_factory=list)


def _pipeline_with_shows(shows):
    """Build a pipeline whose single transformer yields *shows* in order."""
    pipeline = ShowTransformationPipeline(_club())
    transformer = MagicMock()
    transformer.can_transform.return_value = True
    transformer.transform_to_show.side_effect = shows
    pipeline.register_transformer(transformer)
    return pipeline


class TestTicketlessShowWarning:
    """transform() WARNs per ticketless show, ticks diagnostics, never drops."""

    def test_ticketless_show_still_returned(self):
        show = _FakeShow(tickets=[])
        pipeline = _pipeline_with_shows([show])
        result = pipeline.transform(_raw_data(["event_a"]))
        assert result == [show]

    def test_ticketless_show_ticks_bound_diagnostics(self):
        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            pipeline = _pipeline_with_shows([_FakeShow(tickets=[]), _FakeShow(tickets=[])])
            pipeline.transform(_raw_data(["event_a", "event_b"]))
        finally:
            reset_diagnostics(token)
        assert diagnostics.ticketless_shows == 2

    def test_ticketed_show_does_not_tick_counter(self):
        diagnostics = ScrapeDiagnostics()
        token = bind_diagnostics(diagnostics)
        try:
            pipeline = _pipeline_with_shows([_FakeShow(tickets=[object()])])
            result = pipeline.transform(_raw_data(["event_a"]))
        finally:
            reset_diagnostics(token)
        assert len(result) == 1
        assert diagnostics.ticketless_shows == 0

    def test_ticketless_show_warns_per_show(self):
        with patch(
            "laughtrack.utilities.infrastructure.pipeline.pipeline.Logger"
        ) as mock_logger:
            pipeline = _pipeline_with_shows([_FakeShow(name="Open Mic", tickets=[])])
            pipeline.transform(_raw_data(["event_a"]))
        warn_messages = [str(c.args[0]) for c in mock_logger.warn.call_args_list]
        assert any("Ticketless show 'Open Mic'" in m for m in warn_messages)

    def test_no_bound_diagnostics_does_not_crash(self):
        show = _FakeShow(tickets=[])
        pipeline = _pipeline_with_shows([show])
        result = pipeline.transform(_raw_data(["event_a"]))
        assert result == [show]
