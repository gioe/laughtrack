"""Tests for the startup scraper-config validator.

Covers TASK-2097's selection invariant: every enabled scraping_sources row's
scraper_key must resolve to a registered scraper class. A fallback source whose
key was retargeted by a migration but whose code never landed should produce a
distinct startup warning, not silently fail nine clubs at run time.
"""

from __future__ import annotations

from unittest.mock import patch

from laughtrack.app.validators.scraper_config import validate_scraper_keys_for_clubs
from laughtrack.core.entities.club.model import Club, ScrapingSource


def _make_club(*sources: ScrapingSource, club_id: int = 1, name: str = "Test Club") -> Club:
    return Club(
        id=club_id,
        name=name,
        address="",
        website="",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        scraping_sources=list(sources),
    )


class TestValidateAllEnabledSources:
    def test_warns_when_fallback_source_has_unknown_scraper_key(self):
        primary = ScrapingSource(platform="custom", scraper_key="known_key", priority=0, enabled=True)
        fallback = ScrapingSource(platform="custom", scraper_key="missing_key", priority=1, enabled=True)
        club = _make_club(primary, fallback)

        with patch("laughtrack.app.validators.scraper_config.ScraperResolver") as resolver_cls:
            resolver_cls.return_value.keys.return_value = {"known_key"}
            with patch("laughtrack.app.validators.scraper_config.Logger.warn") as warn:
                validate_scraper_keys_for_clubs([club])

        messages = [call.args[0] for call in warn.call_args_list]
        assert any(
            "1 enabled scraping source(s) have unknown scraper keys" in m for m in messages
        ), messages

    def test_passes_when_all_enabled_sources_resolve(self):
        primary = ScrapingSource(platform="custom", scraper_key="known_key", priority=0, enabled=True)
        fallback = ScrapingSource(platform="custom", scraper_key="other_known", priority=1, enabled=True)
        club = _make_club(primary, fallback)

        with patch("laughtrack.app.validators.scraper_config.ScraperResolver") as resolver_cls:
            resolver_cls.return_value.keys.return_value = {"known_key", "other_known"}
            with patch("laughtrack.app.validators.scraper_config.Logger.warn") as warn:
                validate_scraper_keys_for_clubs([club])

        messages = [call.args[0] for call in warn.call_args_list]
        assert not any("unknown scraper keys" in m for m in messages), messages
        assert not any("missing scraper key" in m for m in messages), messages

    def test_disabled_fallback_with_unknown_key_is_ignored(self):
        primary = ScrapingSource(platform="custom", scraper_key="known_key", priority=0, enabled=True)
        disabled_fallback = ScrapingSource(
            platform="custom", scraper_key="missing_key", priority=1, enabled=False
        )
        club = _make_club(primary, disabled_fallback)

        with patch("laughtrack.app.validators.scraper_config.ScraperResolver") as resolver_cls:
            resolver_cls.return_value.keys.return_value = {"known_key"}
            with patch("laughtrack.app.validators.scraper_config.Logger.warn") as warn:
                validate_scraper_keys_for_clubs([club])

        messages = [call.args[0] for call in warn.call_args_list]
        assert not any("unknown scraper keys" in m for m in messages), messages

    def test_club_with_no_enabled_sources_reports_missing(self):
        disabled_only = ScrapingSource(
            platform="custom", scraper_key="known_key", priority=0, enabled=False
        )
        club = _make_club(disabled_only)

        with patch("laughtrack.app.validators.scraper_config.ScraperResolver") as resolver_cls:
            resolver_cls.return_value.keys.return_value = {"known_key"}
            with patch("laughtrack.app.validators.scraper_config.Logger.warn") as warn:
                validate_scraper_keys_for_clubs([club])

        messages = [call.args[0] for call in warn.call_args_list]
        assert any("missing scraper key" in m for m in messages), messages
