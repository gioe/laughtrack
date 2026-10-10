"""Offline behavioral contracts for the read-only eligibility audit."""

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

PATH = Path(__file__).resolve().parents[2] / "scripts/core/audit_comedy_eligibility.py"
spec = importlib.util.spec_from_file_location("eligibility_audit", PATH)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


def person(i, visible=True, parent=None, name=None):
    return {
        "id": i,
        "uuid": str(i),
        "name": name or f"Person {i}",
        "visible": visible,
        "parent_comedian_id": parent,
        "block_reason": None if visible else "not a comic",
    }


def snapshot(people, casts):
    return {
        "clubs": [
            {"id": 1, "name": "Mixed venue", "visible": True},
            {"id": 2, "name": "Empty venue", "visible": False},
        ],
        "sources": [{"id": 1, "club_id": 1, "scraper_key": "test", "enabled": True}],
        "comedians": people,
        "denied": [],
        "shows": [
            {
                "id": i,
                "club_id": 1,
                "date": NOW,
                "is_cancelled": False,
                "last_scraped_by": "test",
                "scraped_by_organizer_id": None,
            }
            for i in range(len(casts))
        ],
        "lineups": [{"show_id": i, "comedian_id": str(p)} for i, cast in enumerate(casts) for p in cast],
    }


def test_contract_1():
    data = snapshot(
        [person(1), person(2, False, 1), person(3, False), person(4, False)], [[1, 2, 3], [3], [3, 4], [], [1]]
    )
    data["shows"][-1]["is_cancelled"] = True
    result = audit.analyze_snapshot(data, NOW)
    all_time = result["clubs"][0]["all_history"]
    upcoming = result["clubs"][0]["upcoming"]
    assert all_time["appearances"] == 6  # alias/root count only once in a show
    assert all_time["blocked_appearances"] == 4
    assert all_time["blocked_appearance_ratio"] == 4 / 6
    assert all_time["distinct_performers"] == 3
    assert all_time["blocked_distinct_ratio"] == 2 / 3
    assert all_time["blocked_only_shows"] == 2
    assert all_time["majority_blocked_shows"] == 2  # exactly half is not majority
    assert all_time["missing_lineups"] == 1
    assert all_time["lineup_coverage"] == 4 / 5
    assert upcoming["shows"] == 4
    assert upcoming["blocked_appearance_ratio"] == 4 / 5
    assert result["clubs"][1]["all_history"]["blocked_appearance_ratio"] is None
    assert sum(f["all_history"]["shows"] for f in result["feeds"]) == 5


def test_contract_2():
    people = [
        person(1),
        person(2, False, 1),
        person(3, False, 2),
        person(4, False),
        person(5, False, 4),
        person(6, False, 999),
        person(7, False, 8),
        person(8, False, 7),
        person(9, name="  Denied\u00a0 Name "),
        person(10, False, 9),
        person(11, True, 999),
    ]
    data = snapshot(people, [[1, 2, 3], [4, 5], [6], [7, 8], [9, 10], [11], [999]])
    data["denied"] = [{"name": "denied name", "reason": "music"}]
    result = audit.analyze_snapshot(data, NOW)
    m = result["clubs"][0]["all_history"]
    assert m["rescued_alias_appearances"] == 2
    assert m["blocked_only_shows"] == 4
    assert m["blocked_appearances"] == 5
    assert m["appearances"] == 8
    assert m["unknown_appearances"] == 2
    assert m["resolution_states"]["cycle"] == 2
    assert m["resolution_states"]["missing_parent"] == 2
    assert m["resolution_states"]["blocked_root"] == 4
    assert "music" in m["block_reason_appearances"]
    assert result["legacy_raw_comparison"]["all_history"]["visible_majority_blocked_clubs"] == 1


def test_contract_3():
    data = snapshot([person(1), person(2, False)], [[1], [2], [], [2], [1], [2]])
    data["sources"] += [
        {"id": 2, "club_id": 1, "scraper_key": "ambiguous", "enabled": False},
        {"id": 3, "club_id": 1, "scraper_key": "ambiguous", "enabled": True},
        {"id": 4, "club_id": None, "source_target_id": 8, "scraper_key": "aggregate", "enabled": True},
    ]
    for show, key in zip(data["shows"], ["test", "ambiguous", None, "aggregate", "unknown", "test"]):
        show["last_scraped_by"] = key
    data["shows"][-1]["scraped_by_organizer_id"] = 17
    result = audit.analyze_snapshot(data, NOW)
    feeds = {f["bucket"]: f for f in result["feeds"]}
    assert feeds["source:1"]["all_history"]["shows"] == 1
    assert feeds["source:4"]["all_history"]["shows"] == 0
    assert feeds["unattributed:ambiguous:ambiguous"]["all_history"]["shows"] == 1
    assert feeds["unattributed:missing_key:None"]["all_history"]["missing_lineups"] == 1
    assert feeds["organizer:17:test"]["all_history"]["shows"] == 1
    assert sum(f["all_history"]["shows"] for f in feeds.values()) == 6
    assert result["clubs"][0]["all_history"]["unblocked_is_not_verified_comedy"]
    json.dumps(result)
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.description = [("id",)]
    cursor.fetchall.return_value = []
    factory = MagicMock()
    factory.return_value.__enter__.return_value = conn
    audit.collect_snapshot(factory)
    factory.assert_called_once_with(autocommit=False)
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    assert statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    assert all(s.startswith(("SET ", "SELECT ")) for s in statements)
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()
