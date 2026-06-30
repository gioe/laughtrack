"""Unit tests for DetailPagePriceMixin's Playwright-fallback opt-out (TASK-3544).

The shared detail-page price enrichment fetches only need a page's JSON-LD
offers and degrade to price-unknown on failure, so they must pass
``skip_js_fallback=True`` to ``fetch_html`` — a bot-blocked detail page should
never spin a per-URL headless browser.
"""

import pytest

from laughtrack.scrapers.base.detail_price_mixin import DetailPagePriceMixin


class _FakeRateLimiter:
    async def await_if_needed(self, url):
        return None


class _Host(DetailPagePriceMixin):
    """Minimal concrete host exposing the attributes the mixin requires."""

    _log_prefix = "test"
    logger_context = {}

    def __init__(self):
        super().__init__()
        self.rate_limiter = _FakeRateLimiter()
        self.fetch_calls = []

    async def fetch_html(self, url, **kwargs):
        self.fetch_calls.append((url, kwargs))
        # A JSON-LD page whose lowest offer is 25.0.
        return (
            '<html><head><script type="application/ld+json">'
            '{"@type":"Event","offers":[{"@type":"Offer","price":"25.00"}]}'
            "</script></head><body></body></html>"
        )


class _Item:
    def __init__(self, url):
        self._url = url
        self.price = None


@pytest.mark.asyncio
async def test_detail_price_fetch_passes_skip_js_fallback():
    """_fetch_detail_page_price must call fetch_html with skip_js_fallback=True."""
    host = _Host()
    item = _Item("https://example.com/event/1")

    await host._attach_detail_page_prices([item], lambda i: i._url)

    assert item.price == 25.0
    assert len(host.fetch_calls) == 1
    _url, kwargs = host.fetch_calls[0]
    assert kwargs.get("skip_js_fallback") is True


@pytest.mark.asyncio
async def test_failed_fetch_degrades_to_price_unknown_without_browser():
    """A raising fetch_html leaves the item price-unknown and is retryable."""

    class _RaisingHost(_Host):
        async def fetch_html(self, url, **kwargs):
            self.fetch_calls.append((url, kwargs))
            raise RuntimeError("detail page blocked")

    host = _RaisingHost()
    item = _Item("https://example.com/event/2")

    await host._attach_detail_page_prices([item], lambda i: i._url)

    assert item.price is None
    # Still asked for the opt-out, and the failed URL is evicted from the memo
    # so a later run can retry it.
    assert host.fetch_calls[0][1].get("skip_js_fallback") is True
    assert "https://example.com/event/2" not in host._detail_price_tasks
