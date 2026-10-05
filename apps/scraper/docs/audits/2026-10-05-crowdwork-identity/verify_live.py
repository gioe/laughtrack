#!/usr/bin/env python3
"""Verify the retained live Crowdwork collision; restore only with --apply.

Default mode reads the database and converts exactly two feed occurrences.
--apply requires a private backup path and atomically persists the pair twice,
using the real ShowHandler and child handlers on one bound connection. No other
date, reconciliation, stale sweep, or venue capacity operation is requested.
"""

import argparse
import hashlib
import json
import runpy
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.core.data.base_handler import BaseDatabaseHandler
from laughtrack.core.entities.club.handler import ClubHandler
from laughtrack.core.entities.club.model import ScrapingSource
from laughtrack.core.entities.show.handler import ShowHandler
from laughtrack.foundation.db_util import connect_with_retry
from laughtrack.scrapers.implementations.api.crowdwork.utils import RAILS_TO_IANA, extract_performances

WHEN = datetime(2026, 10, 3, 2, 30, tzinfo=timezone.utc)
URLS = {
    13849: "https://www.crowdwork.com/e/paranormal-laughtivity",
    13224: "https://www.crowdwork.com/e/people-being-funny",
}
EXISTING_ID = 480923
shared = runpy.run_path(str(_root / "scripts/core/repair_annoyance_identity.py"))
PLAN = {"club_id": 182, "source_id": 45, "expected_shows": {str(EXISTING_ID): {}}}


@contextmanager
def bound_handlers(connection):
    """Keep real handler operations in the caller's atomic transaction.

    The normal handlers acquire and commit separate connections. This script
    binds only connection ownership; validation, SQL, and child writes remain
    the production implementations. The caller alone commits or rolls back.
    """

    @contextmanager
    def acquire(self, conn=None):
        if conn is not None and conn is not connection:
            raise ValueError("Unexpected separate handler connection")
        yield connection

    @contextmanager
    def transaction(self):
        yield connection

    with (
        patch.object(BaseDatabaseHandler, "_acquire_connection", acquire),
        patch.object(BaseDatabaseHandler, "transaction", transaction),
    ):
        yield


def convert_pair(feed, club):
    if feed.get("status") != 200 or feed.get("type") != "success":
        raise ValueError("Feed is not a successful Crowdwork response")
    matches = [item for item in feed["data"] if item.get("id") in URLS]
    if len(matches) != 2 or {item["id"] for item in matches} != set(URLS):
        raise ValueError("Feed event ID cohort changed")
    shows = []
    for item in matches:
        if item.get("url") != URLS[item["id"]] or (item.get("theatre") or {}).get("id") != 33450:
            raise ValueError("Feed URL or venue identity changed")
        exact = [
            event
            for event in extract_performances(item, rails_to_iana=RAILS_TO_IANA)
            if datetime.fromisoformat(event.date_str).astimezone(timezone.utc) == WHEN
        ]
        if len(exact) != 1:
            raise ValueError("Expected exactly one occurrence per URL at the reviewed instant")
        show = exact[0].to_show(club, enhanced=False)
        if show is None or show.room or not show.source_performance_id:
            raise ValueError("Conversion lost source identity or fabricated a room")
        # The feed is a partial ticket observation, not authority to remove tiers.
        show.tickets_complete = False
        shows.append(show)
    if len({show.to_unique_key() for show in shows}) != 2:
        raise ValueError("Source conversion still collapses the pair")
    return shows


def pair_rows(state):
    rows = [
        row
        for row in state["shows"]
        if row["show_page_url"] in URLS.values()
        and datetime.fromisoformat(row["date"]).astimezone(timezone.utc) == WHEN
    ]
    indexed = {row["show_page_url"]: row for row in rows}
    if len(rows) != len(indexed):
        raise ValueError("Multiple database rows already represent one reviewed occurrence")
    return indexed


def reference_values(rows):
    # Ticket refresh timestamps may advance; relationship and business fields may not disappear.
    return {json.dumps({k: v for k, v in row.items() if k != "updated_at"}, sort_keys=True) for row in rows}


def verify_transition(before, after, identities):
    pair = pair_rows(after)
    if set(pair) != set(URLS.values()) or pair[URLS[13849]]["id"] != EXISTING_ID:
        raise ValueError("Pair is missing or existing Paranormal show ID changed")
    if len({row["id"] for row in pair.values()}) != 2:
        raise ValueError("Distinct performances share a database ID")
    if any(pair[url]["id"] != row["id"] for url, row in pair_rows(before).items()):
        raise ValueError("Existing performance ID changed")
    for url, row in pair.items():
        if row["room"] != "" or row["source_performance_id"] != identities[url]:
            raise ValueError("Stored source identity or empty room changed")
        if not any(t["show_id"] == row["id"] and t["purchase_url"] == url for t in after["tickets"]):
            raise ValueError("Stored performance lacks its exact ticket URL")
    target_ids = {row["id"] for row in pair.values()}
    for table in shared["CHILDREN"]:
        if not reference_values(before[table]).issubset(reference_values(after[table])):
            raise ValueError(f"Existing relationship or business value changed: {table}")
        outside_before = [r for r in before[table] if r["show_id"] not in target_ids]
        outside_after = [r for r in after[table] if r["show_id"] not in target_ids]
        if outside_before != outside_after:
            raise ValueError(f"Unrelated child rows changed: {table}")
    if [r for r in before["shows"] if r["id"] not in target_ids] != [
        r for r in after["shows"] if r["id"] not in target_ids
    ] or before["scraping_sources"] != after["scraping_sources"]:
        raise ValueError("Unrelated shows or source settings changed")
    return {url: row["id"] for url, row in pair.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed", type=Path, default=Path("/private/tmp/task4106-live-feed.json"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error("--apply requires a new private --backup path")
    if args.backup and (args.backup.exists() or args.backup.resolve().is_relative_to(_root.parents[1])):
        parser.error("Use a new private backup file outside the checkout")
    if datetime.now(timezone.utc) - datetime.fromtimestamp(args.feed.stat().st_mtime, timezone.utc) > timedelta(
        hours=24
    ):
        raise ValueError("Refresh the native HTTP feed capture; it is more than 24 hours old")
    raw_feed = args.feed.read_bytes()
    feed = json.loads(raw_feed)
    query = runpy.run_path(str(_root / "bin/query"))
    connection = connect_with_retry(query["_resolve_database_url"]())
    try:
        if not args.apply:
            connection.set_session(readonly=True)
        with bound_handlers(connection), connection.cursor() as cur:
            if args.apply:
                shared["lock_schema"](cur)
            cur.execute("SET LOCAL statement_timeout='30s'")
            before = shared["snapshot"](cur, PLAN)
            sources = [row for row in before["scraping_sources"] if row["id"] == 45]
            if len(sources) != 1:
                raise ValueError("Source45 missing")
            source = sources[0]
            metadata = source.get("metadata") or {}
            if source["club_id"] != 182 or source["scraper_key"] != "crowdwork" or not source["enabled"]:
                raise ValueError("Source45 venue, scraper, or activation changed")
            if metadata.get("source_performance_identity") is not True or not metadata.get("task_4106_identity_repair"):
                raise ValueError("Apply the reviewed source45 backfill and activation first")
            club = ClubHandler().get_club_by_id(182)
            club.active_scraping_source = ScrapingSource.from_dict(source)
            shows = convert_pair(feed, club)
            identities = {show.show_page_url: show.source_performance_id for show in shows}
            existing = pair_rows(before).get(URLS[13849])
            if (
                existing is None
                or existing["id"] != EXISTING_ID
                or existing["source_performance_id"] != identities[URLS[13849]]
            ):
                raise ValueError("Existing Paranormal row/backfilled identity drift")
            output = {
                "mode": "read_only",
                "converted": 2,
                "existing_pair_count": len(pair_rows(before)),
                "feed_sha256": hashlib.sha256(raw_feed).hexdigest(),
            }
            if args.apply:
                results = []
                handler = ShowHandler()
                for iteration in range(2):
                    batch = shows if iteration == 0 else list(reversed(convert_pair(feed, club)))
                    result = handler.insert_shows(batch, batch_size=100, club_name=club.name, scraper_key="crowdwork")
                    if result.errors or result.db_errors or result.validation_errors or result.total != 2:
                        raise ValueError("Actual ShowHandler rejected the bounded pair")
                    after = shared["snapshot"](cur, PLAN)
                    ids = verify_transition(before, after, identities)
                    if iteration == 0:
                        if result.inserts != 2 - len(pair_rows(before)):
                            raise ValueError("Unexpected insertion count for the bounded pair")
                        first_ids = ids
                    elif ids != first_ids or result.inserts != 0:
                        raise ValueError("Repeated refresh changed IDs or inserted another show")
                    results.append({"inserts": result.inserts, "updates": result.updates})
                shared["save_backup"](
                    args.backup,
                    {
                        "task_id": 4106,
                        "purpose": "bounded_pair_restore",
                        "feed_sha256": output["feed_sha256"],
                        "before": before,
                        "after": after,
                    },
                )
                connection.commit()
                output.update(mode="applied", pair_ids=ids, passes=results, existing_relationships_preserved=True)
            else:
                connection.rollback()
        print(json.dumps(output, sort_keys=True))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
