"""Expected failure: actual persistence dedup loses a distinct live iO event.

Run from apps/scraper with PYTHONPATH=src:. .venv/bin/python3
    docs/audits/2026-09-28-io-stale-reconciliation/collision_repro.py
No database or network access; uses saved source events and the actual helper
called by ShowHandler._process_single_batch.
"""

import json

from replay import read_rows, utc
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.crowdwork.utils import RAILS_TO_IANA, extract_performances
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.utilities.domain.show.utils import ShowUtils


def main():
    target = utc("2026-10-03T02:30:00+00:00")
    names = {"Paranormal Laughtivity", "People Being Funny"}
    shows = []
    for event in read_rows("feed.jsonl"):
        if event["name"] not in names:
            continue
        for performance in extract_performances(event, rails_to_iana=RAILS_TO_IANA):
            timestamp = utc(ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                performance.date_str, performance.timezone
            ))
            if timestamp == target:
                shows.append(Show(name=performance.name, club_id=182, date=timestamp,
                                  show_page_url=performance.url, room=""))
    assert len(shows) == 2 and len({show.show_page_url for show in shows}) == 2
    kept, details = ShowUtils.deduplicate_shows_with_details(shows)
    print(json.dumps({"input_events": [show.name for show in shows],
                      "input_urls": [show.show_page_url for show in shows],
                      "timestamp": target.isoformat(),
                      "retained_events": [show.name for show in kept],
                      "collision_groups": len(details)}, sort_keys=True), flush=True)
    assert len(kept) == 2, "Distinct live Crowdwork events collapse onto one empty-room slot"


if __name__ == "__main__":
    main()
