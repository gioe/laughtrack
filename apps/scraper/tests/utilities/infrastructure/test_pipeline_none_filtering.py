"""Unit tests for ShowTransformationPipeline None-filtering behaviour."""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

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


class TestPipelineNoneFiltering:
    """ShowTransformationPipeline.transform() skips None from transform_to_show."""

    def _pipeline_with_transformer(self, transform_side_effect):
        """Build a pipeline with one mock transformer whose transform_to_show uses side_effect."""
        pipeline = ShowTransformationPipeline(_club())
        transformer = MagicMock()
        transformer.can_transform.return_value = True
        transformer.transform_to_show.side_effect = transform_side_effect
        pipeline.register_transformer(transformer)
        return pipeline

    def test_none_result_excluded_from_output(self):
        """transform() does not include None in the returned list."""
        pipeline = self._pipeline_with_transformer(lambda event: None)
        result = pipeline.transform(_raw_data(["event_a"]))
        assert result == []

    def test_valid_show_included_in_output(self):
        """transform() includes the Show returned by transform_to_show."""
        mock_show = MagicMock()
        pipeline = self._pipeline_with_transformer(lambda event: mock_show)
        result = pipeline.transform(_raw_data(["event_a"]))
        assert result == [mock_show]

    def test_mixed_none_and_valid_show(self):
        """One None and one valid Show: only the valid Show appears in the output."""
        mock_show = MagicMock()
        side_effects = [None, mock_show]

        pipeline = ShowTransformationPipeline(_club())
        transformer = MagicMock()
        transformer.can_transform.return_value = True
        transformer.transform_to_show.side_effect = side_effects
        pipeline.register_transformer(transformer)

        result = pipeline.transform(_raw_data(["event_none", "event_show"]))

        assert mock_show in result
        assert None not in result
        assert len(result) == 1
