"""Unit tests for widget_detector.py — Bandsintown and Songkick widget detection."""

import pytest

from laughtrack.scrapers.implementations.api.comedian_websites.widget_detector import (
    WidgetResult,
    detect_widgets,
)


class TestWidgetResult:
    def test_has_any_with_bandsintown(self):
        r = WidgetResult(bandsintown_id="Artist Name")
        assert r.has_any is True

    def test_has_any_with_songkick(self):
        r = WidgetResult(songkick_id="12345")
        assert r.has_any is True

    def test_has_any_with_both(self):
        r = WidgetResult(bandsintown_id="Artist", songkick_id="12345")
        assert r.has_any is True

    def test_has_any_empty(self):
        r = WidgetResult()
        assert r.has_any is False


class TestDetectBandsintown:
    def test_data_artist_name(self):
        html = '<div class="bit-widget-initializer" data-artist-name="John Mulaney" data-artist-id="123"></div>'
        result = detect_widgets(html)
        assert result.bandsintown_id == "John Mulaney"

    def test_data_artist_id_fallback(self):
        """When data-artist-name is absent, falls back to data-artist-id."""
        html = '<div class="bit-widget-initializer" data-artist-id="99887"></div>'
        result = detect_widgets(html)
        assert result.bandsintown_id == "99887"

    def test_data_artist_name_whitespace_falls_to_id(self):
        """Whitespace-only artist-name is skipped; falls back to artist-id."""
        html = '<div class="bit-widget-initializer" data-artist-name="   " data-artist-id="555"></div>'
        result = detect_widgets(html)
        assert result.bandsintown_id == "555"

    def test_data_bit_artist_fallback(self):
        """When no bit-widget-initializer exists, detects data-bit-artist attribute."""
        html = '<span data-bit-artist="Hasan Minhaj"></span>'
        result = detect_widgets(html)
        assert result.bandsintown_id == "Hasan Minhaj"

    def test_data_bit_artist_whitespace_ignored(self):
        html = '<span data-bit-artist="   "></span>'
        result = detect_widgets(html)
        assert result.bandsintown_id is None

    def test_strips_whitespace(self):
        html = '<div class="bit-widget-initializer" data-artist-name="  Ali Wong  "></div>'
        result = detect_widgets(html)
        assert result.bandsintown_id == "Ali Wong"


class TestDetectSongkick:
    def test_href_url_extraction(self):
        html = '<a class="songkick-widget" href="https://www.songkick.com/artists/12345-john-doe"></a>'
        result = detect_widgets(html)
        assert result.songkick_id == "12345"

    def test_data_songkick_id_attribute(self):
        """When href has no songkick URL, falls back to data-songkick-id."""
        html = '<a class="songkick-widget" href="" data-songkick-id="67890"></a>'
        result = detect_widgets(html)
        assert result.songkick_id == "67890"

    def test_data_songkick_id_on_any_element(self):
        """Fallback: data-songkick-id on a non-widget element."""
        html = '<div data-songkick-id="11111"></div>'
        result = detect_widgets(html)
        assert result.songkick_id == "11111"

    def test_raw_html_regex_fallback(self):
        """Songkick URL in a script tag (not in a widget element)."""
        html = '<script>var url = "https://www.songkick.com/artists/77777-someone";</script>'
        result = detect_widgets(html)
        assert result.songkick_id == "77777"

    def test_data_songkick_id_whitespace_ignored(self):
        html = '<a class="songkick-widget" href="" data-songkick-id="  "></a>'
        result = detect_widgets(html)
        assert result.songkick_id is None

    def test_case_insensitive_url_match(self):
        html = '<a class="songkick-widget" href="https://WWW.SONGKICK.COM/artists/55555-name"></a>'
        result = detect_widgets(html)
        assert result.songkick_id == "55555"


class TestBothWidgets:
    def test_page_with_both_widgets(self):
        html = """
        <div class="bit-widget-initializer" data-artist-name="Bo Burnham"></div>
        <a class="songkick-widget" href="https://www.songkick.com/artists/99999-bo-burnham"></a>
        """
        result = detect_widgets(html)
        assert result.bandsintown_id == "Bo Burnham"
        assert result.songkick_id == "99999"
        assert result.has_any is True


class TestNoWidgets:
    def test_empty_html(self):
        result = detect_widgets("")
        assert result.bandsintown_id is None
        assert result.songkick_id is None
        assert result.has_any is False

    def test_plain_html(self):
        html = "<html><body><p>No widgets here</p></body></html>"
        result = detect_widgets(html)
        assert result.has_any is False

    def test_unrelated_classes(self):
        html = '<div class="some-other-widget" data-artist-name="Nope"></div>'
        result = detect_widgets(html)
        assert result.bandsintown_id is None
