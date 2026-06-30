import pytest

from laughtrack.foundation.infrastructure.http.playwright_browser import PlaywrightBrowser


class _FakePage:
    def __init__(self, html_by_url):
        self.html_by_url = html_by_url
        self.urls = []

    async def add_init_script(self, _script):
        return None

    async def goto(self, url, **_kwargs):
        self.urls.append(url)

    async def content(self):
        return self.html_by_url[self.urls[-1]]


class _FakeContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    async def new_page(self):
        return self.page

    async def close(self):
        self.closed = True


class _FakeBrowser:
    def __init__(self, context):
        self.context = context

    async def new_context(self, **_kwargs):
        return self.context


def _page(events):
    cards = "\n".join(
        f'''
        <div class="search-event" id="li{event_id}">
          <a aria-label="Buy tickets for {name} on {date}"
             href="/event/{slug}/{event_id}?afflky=ThePortComedyClub">GET TICKETS</a>
        </div>
        '''
        for event_id, name, date, slug in events
    )
    return f'<html><body><div class="events-grid">{cards}</div></body></html>'


@pytest.mark.asyncio
async def test_fetch_seetickets_whitelabel_pages_paginates_until_no_new_events(monkeypatch):
    browser = PlaywrightBrowser()
    first = _page([
        ("101", "First Show", "July 01 2026", "first-show"),
        ("102", "Second Show", "July 02 2026", "second-show"),
    ])
    second = _page([
        ("102", "Second Show", "July 02 2026", "second-show"),
        ("103", "Third Show", "July 03 2026", "third-show"),
    ])
    third = _page([
        ("103", "Third Show", "July 03 2026", "third-show"),
    ])
    html_by_url = {}
    page = _FakePage(html_by_url)
    context = _FakeContext(page)
    browser._browser = _FakeBrowser(context)

    async def fake_launch():
        return None

    monkeypatch.setattr(browser, "_launch_if_needed_locked", fake_launch)

    def html_for(url):
        if "_lfv=2" in url:
            return second
        if "_lfv=4" in url:
            return third
        return first

    async def fake_goto(url, **kwargs):
        page.urls.append(url)
        html_by_url[url] = html_for(url)

    monkeypatch.setattr(page, "goto", fake_goto)

    pages = await browser.fetch_seetickets_whitelabel_pages(
        profile_id="15127815",
        whitelabel_key="ThePortComedyClub",
        page_size=2,
        max_pages=5,
        max_months=1,
    )

    assert len(pages) == 2
    assert "First Show" in pages[0]
    assert "Third Show" in pages[1]
    assert any("ProfileID=15127815" in url for url in page.urls)
    assert any("WhiteLabelKey=ThePortComedyClub" in url for url in page.urls)
    assert any("_lfv=2" in url and "_sft=0" in url for url in page.urls)
    assert any("EventStart=" in url and "EventStart2=" in url for url in page.urls)
    assert context.closed is True
