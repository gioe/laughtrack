"""Unit tests for ShowTransformationPipeline None-filtering behaviour."""

from unittest.mock import MagicMock

import pytest

from laughtrack.core.entities.club.model import Club
from laughtrack.utilities.infrastructure.pipeline import ShowTransformationPipeline


def _club() -> Club:
    return Club(
        id=1,
        name="Test Club",
        address="123 Main St",
        website="https://testclub.example.com",
        scraping_url="https://testclub.example.com",
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
        timezone="America/New_York",
    )


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
