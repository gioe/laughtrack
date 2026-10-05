"""Offline verification of the reviewed TASK-4105 evidence, never a DB write."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from laughtrack.scrapers.implementations.api.crowdwork.utils import RAILS_TO_IANA, extract_performances
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

ROOT = Path(__file__).resolve().parent


def utc(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def verify():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    decisions = json.loads((ROOT / 'decisions.json').read_text())
    before = json.loads((ROOT / 'before.json').read_text())
    pages = {r['url']: r for r in json.loads((ROOT / 'pages.json').read_text())}
    feed = json.loads((ROOT / 'feed.json').read_text())
    assert len(feed) == 80 and len(pages) == 13
    identities = set()
    for event in feed:
        for p in extract_performances(event, rails_to_iana=RAILS_TO_IANA):
            identities.add((p.url, utc(ShowFactoryUtils.parse_datetime_with_timezone_fallback(p.date_str, p.timezone))))
    prior = [json.loads(line) for line in (ROOT.parent / '2026-09-28-io-stale-reconciliation/candidates.jsonl').read_text().splitlines()]
    assert len(decisions) == 42
    assert {r['id'] for r in decisions} == {r['id'] for r in prior}
    selected = [r for r in decisions if r['decision'] == 'delete']
    assert len(selected) == 29
    assert {480692, 3736581, 2084643, 3013099, 4282370, 5600935}.isdisjoint(r['id'] for r in selected)
    stored = {r['id']: r for r in before['shows']}
    for row in decisions:
        assert row['reasons']
        if row['decision'] != 'delete':
            continue
        current = stored[row['id']]
        for field in ('name', 'show_page_url', 'room', 'last_scraped_by'):
            assert current[field] == row[field]
        assert current['club_id'] == 182
        assert utc(current['date']) == utc(row['date']) > utc(manifest['cutoff'])
        assert utc(current['last_scraped_date']) == utc(row['current_last_scraped_date']) < utc(manifest['cutoff'])
        assert (row['show_page_url'], utc(row['date'])) not in identities
        local = utc(row['date']).astimezone(ZoneInfo('America/Chicago')).replace(tzinfo=None).isoformat()
        page = pages[row['show_page_url']]
        assert local not in page['visible_date_links_local']
        if row['classification'] == 'series_absent_past_only_page':
            assert page['sales_closed'] and not page['visible_date_links_local']
            assert not any(url == row['show_page_url'] for url, _ in identities)
        else:
            assert page['visible_date_links_local']
        if row.get('replacement_utc'):
            assert row['current_replacement_ids']
            assert (row['show_page_url'], utc(row['replacement_utc'])) in identities
            assert any(r['id'] in row['current_replacement_ids'] and r['show_page_url'] == row['show_page_url']
                       and utc(r['date']) == utc(row['replacement_utc']) for r in before['club_shows'])
    assert '11/05' in pages['https://www.crowdwork.com/e/flex-improv']['description']
    print('Verified 42 dispositions: 29 bounded deletions, 13 holds; fresh feed/pages and replacement checks pass.')
    return selected


if __name__ == '__main__':
    verify()
