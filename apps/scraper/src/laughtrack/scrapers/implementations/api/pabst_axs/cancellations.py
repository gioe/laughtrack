"""Explicit Pabst cancellation evidence; absence never means cancellation."""
import asyncio
import re
import unicodedata
from datetime import date
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from laughtrack.core.models.results import ShowCancellation
from laughtrack.foundation.infrastructure.http.diagnostics import current_diagnostics
from laughtrack.foundation.infrastructure.logger.logger import Logger

_KEYS = {'pabst_theater_group', 'pabst_axs'}
_DATE = re.compile(r'/(\d{4})\.(\d{2})\.(\d{2})-')


def _text(value):
    return ' '.join(unicodedata.normalize('NFKC', value or '').casefold().split())


def _official(url):
    parts = urlsplit(url)
    return parts.scheme == 'https' and parts.hostname in {'www.pabsttheatergroup.com', 'pabsttheatergroup.com', 'www.pabsttheater.org', 'pabsttheater.org'} and parts.path.startswith('/events/detail/')


def extract_detail_identity(html, requested_url):
    """Return identity and explicit state from this event's detail region only."""
    if not html or not _official(requested_url):
        return None
    soup = BeautifulSoup(html, 'html.parser')
    for canonical in soup.select('meta[property="og:url"],link[rel="canonical"]'):
        if (canonical.get('content') or canonical.get('href')) != requested_url:
            return None
    roots = soup.select('div.event_detail')
    if len(roots) != 1:
        return None
    root = roots[0]
    title = root.select_one('h1.title')
    venue = root.select_one('.sidebar_event_venue a')
    dates = {_DATE.search(img.get('src', '')).groups() for img in root.select('img[src]') if _DATE.search(img.get('src', ''))}
    if not title or not venue or len(dates) != 1:
        return None
    try:
        local_date = date(*map(int, next(iter(dates))))
    except ValueError:
        return None
    statuses = [_text(node.get_text(' ', strip=True)) for node in root.select('.sidebar_event_date > span,.buttonWrapper > .date,.tickets .text')]
    cancelled = any(value in {'canceled', 'cancelled'} for value in statuses)
    return dict(title=title.get_text(' ', strip=True), venue_name=venue.get_text(' ', strip=True), date=local_date, cancelled=cancelled)


def match_cancellation(detail, stored_rows, scraper_key, url):
    """Bind affirmative evidence to one existing identity, preserving its instant."""
    if not detail or not detail['cancelled'] or scraper_key not in _KEYS:
        return None
    candidates = [row for row in stored_rows if row['show_page_url'] == url and row['last_scraped_by'] == scraper_key]
    # A reused URL or duplicated identity must not choose one arbitrary show.
    if len(candidates) != 1:
        return None
    row = candidates[0]
    if (_text(row['name']) != _text(detail['title']) or _text(row['venue_name']) != _text(detail['venue_name'])
            or row['date'].utcoffset() is None or row['date'].astimezone(ZoneInfo('America/Chicago')).date() != detail['date']):
        return None
    return ShowCancellation(show_id=row['id'], club_id=row['club_id'], production_company_id=row['production_company_id'],
        scraper_key=scraper_key, show_page_url=url, date=row['date'], source_performance_id=row['source_performance_id'],
        name=row['name'], venue_name=row['venue_name'], venue_address=row['venue_address'], venue_zip=row['venue_zip'])


class PabstCancellationMixin:
    """Read-only collection; shared result persistence applies exact intents later."""
    def scrape_with_result(self):
        self._cancellations = []
        result = super().scrape_with_result()
        result.cancellations = list(self._cancellations)
        return result

    def _hold_cancellation_review(self, url):
        message = f'{self._log_prefix}: Pabst detail identity/state unverified at {url}; retaining stored inventory'
        Logger.warn(message)
        diagnostics = current_diagnostics()
        if diagnostics is not None:
            diagnostics.record_scrape_error(message)
            diagnostics.record_fetch_failed()

    async def _review_cancellations(self, events):
        self._cancellations = []
        query = '''SELECT s.id,s.club_id,s.production_company_id,s.last_scraped_by,s.show_page_url,s.date,
                   s.source_performance_id,s.name,c.name AS venue_name,c.address AS venue_address,c.zip_code AS venue_zip
                   FROM shows s JOIN clubs c ON c.id=s.club_id
                   WHERE s.last_scraped_by=%s AND s.date >= NOW()-INTERVAL '7 days' '''
        params = (self.key,)
        if self.key == 'pabst_axs':
            query += 'AND s.club_id=%s'
            params += (self.club.id,)
        try:
            rows = await asyncio.get_running_loop().run_in_executor(None,
                lambda: self._club_handler.execute_with_cursor(query, params, return_results=True))
        except Exception:
            self._hold_cancellation_review('stored source identities')
            raise
        rows = [dict(row) for row in rows or []]
        urls = sorted({event.show_page_url for event in events} | {row['show_page_url'] for row in rows})
        cancelled_urls = set()
        for url in urls:
            if not _official(url):
                self._hold_cancellation_review(url)
                continue
            try:
                html = await self.fetch_html(url, scraper_key=self.key)
                detail = extract_detail_identity(html, url)
            except Exception:
                detail = None
            if detail is None:
                self._hold_cancellation_review(url)
                continue
            if detail['cancelled']:
                cancelled_urls.add(url)
                intent = match_cancellation(detail, rows, self.key, url)
                if intent is not None:
                    self._cancellations.append(intent)
                else:
                    self._hold_cancellation_review(url)
        return [event for event in events if event.show_page_url not in cancelled_urls]
