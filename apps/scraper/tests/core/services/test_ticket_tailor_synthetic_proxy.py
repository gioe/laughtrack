"""TASK-3023: the synthetic-proxy builder recognizes Ticket Tailor producers.

_build_synthetic_proxy_for_company previously only handled Eventbrite organizer
URLs (returning None for everything else, which skipped the company). It now
also synthesizes a proxy for Ticket Tailor box-office URLs, driving the
TicketTailorScraper.
"""

from laughtrack.core.entities.production_company.model import ProductionCompany
from laughtrack.core.services.scraping import (
    _build_synthetic_proxy_for_company,
    _extract_tickettailor_account,
)


def _company(scraping_url: str) -> ProductionCompany:
    return ProductionCompany(
        id=42,
        name="Milwaukee Comedy",
        slug="milwaukee-comedy",
        scraping_url=scraping_url,
        website="https://www.milwaukeecomedy.com/",
        visible=False,
    )


def test_extract_tickettailor_account():
    assert (
        _extract_tickettailor_account("https://www.tickettailor.com/events/milwaukeecomedy/")
        == "milwaukeecomedy"
    )
    assert (
        _extract_tickettailor_account("https://www.tickettailor.com/all-tickets/foo/")
        == "foo"
    )
    assert _extract_tickettailor_account("https://www.eventbrite.com/o/x-123456/") is None
    assert _extract_tickettailor_account("") is None


def test_synthetic_proxy_for_tickettailor_company():
    company = _company("https://www.tickettailor.com/events/milwaukeecomedy/")
    proxy = _build_synthetic_proxy_for_company(company)

    assert proxy is not None
    assert proxy.is_synthetic is True
    assert proxy.visible is False
    assert proxy.production_company_id == 42
    assert proxy.website == "https://www.milwaukeecomedy.com/"
    assert proxy.name == "Milwaukee Comedy (producer)"

    source = proxy.scraping_sources[0]
    assert source.scraper_key == "ticket_tailor"
    assert source.platform == "custom"
    assert source.source_url == "https://www.tickettailor.com/events/milwaukeecomedy/"
    assert source.metadata.get("account_slug") == "milwaukeecomedy"


def test_synthetic_proxy_still_handles_eventbrite():
    company = _company("https://www.eventbrite.com/o/encore-comedy/72313162423/")
    proxy = _build_synthetic_proxy_for_company(company)

    assert proxy is not None
    assert proxy.name == "Milwaukee Comedy (organizer)"
    assert proxy.scraping_sources[0].scraper_key == "eventbrite"


def test_synthetic_proxy_none_for_unsupported_url():
    assert _build_synthetic_proxy_for_company(_company("https://example.com/shows")) is None
