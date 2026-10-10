"""Read-only parent-aware venue/feed triage. Flags are not proof of genre."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

QUERIES = {
    "clubs": "SELECT id, name, visible FROM clubs ORDER BY id",
    "sources": "SELECT id, club_id, source_target_id, scraper_key, enabled FROM scraping_sources ORDER BY id",
    "shows": "SELECT id, club_id, date, is_cancelled, last_scraped_by, scraped_by_organizer_id FROM shows ORDER BY id",
    "lineups": "SELECT show_id, comedian_id FROM lineup_items ORDER BY show_id, comedian_id",
    "comedians": "SELECT id, uuid, name, visible, block_reason, parent_comedian_id FROM comedians ORDER BY id",
    "denied": "SELECT name, reason FROM comedian_deny_list ORDER BY name",
}


def collect_snapshot(connection_factory=None):
    if connection_factory is None:
        from dotenv import load_dotenv

        load_dotenv(_root / ".env")
        from laughtrack.adapters.db import get_connection

        connection_factory = get_connection
    data = {}
    with connection_factory(autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cur.execute("SET LOCAL statement_timeout = '120s'")
            for key, sql in QUERIES.items():
                cur.execute(sql)
                data[key] = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
        conn.rollback()
    return data


def normalize(name):
    return " ".join((name or "").split()).casefold()


def analyze_snapshot(data, as_of):
    if as_of.tzinfo is None:
        raise ValueError("as_of must include a timezone")
    people = {p["id"]: p for p in data["comedians"]}
    uuids = {p["uuid"]: p for p in people.values()}
    denied = {normalize(d["name"]): d["reason"] or "deny_list" for d in data["denied"]}

    def reasons(p):
        result = []
        if p.get("visible") is not True:
            result.append(p.get("block_reason") or "hidden_without_reason")
        if normalize(p["name"]) in denied:
            result.append(denied[normalize(p["name"])])
        return sorted(set(result))

    cache = {}

    def resolve(pid):
        if pid in cache:
            return cache[pid]
        path, seen = [], set()
        current = pid
        while current in people and current not in seen:
            seen.add(current)
            path.append(current)
            parent = people[current].get("parent_comedian_id")
            if parent is None:
                result = (current, "blocked_root" if reasons(people[current]) else "valid_root")
                break
            current = parent
        else:
            result = (None, "cycle" if current in seen else "missing_parent")
        for member in path:
            cache[member] = result
        return result

    lineups = defaultdict(list)
    for item in data["lineups"]:
        lineups[item["show_id"]].append(item["comedian_id"])
    source_matches = defaultdict(list)
    groups = {f"source:{s['id']}": {"source": s, "shows": []} for s in data["sources"]}
    for source in data["sources"]:
        if source.get("club_id") is not None:
            source_matches[(source["club_id"], source["scraper_key"])].append(source["id"])
    clubs = {c["id"]: {**c, "shows": []} for c in data["clubs"]}
    evidence = []
    for show in data["shows"]:
        identities, raw_reasons, resolutions = {}, Counter(), Counter()
        raw_blocked = rescued = raw_total = 0
        for uuid in lineups[show["id"]]:
            p = uuids.get(uuid)
            raw_total += 1
            if p is None:
                identities[f"missing:{uuid}"] = None
                resolutions["missing_identity"] += 1
                continue
            root, state = resolve(p["id"])
            own = reasons(p)
            parent = people.get(p.get("parent_comedian_id"))
            raw_blocked += bool(own or (parent and reasons(parent)))
            resolutions[state] += 1
            if root is not None:
                identities[f"person:{root}"] = state == "blocked_root"
                raw_reasons.update(set(own) | set(reasons(people[root])))
                rescued += bool(own and state == "valid_root")
            else:
                raw_reasons.update(own)
                # Broken links never rescue blocked identities; otherwise unknown.
                identities[f"unresolved:{p['id']}"] = True if own else None
        key = show.get("last_scraped_by")
        organizer = show.get("scraped_by_organizer_id")
        candidates = source_matches.get((show["club_id"], key), []) if key else []
        if organizer is not None:
            bucket, attribution = f"organizer:{organizer}:{key}", "organizer_feed_unresolved"
        elif len(candidates) == 1:
            bucket, attribution = f"source:{candidates[0]}", "inferred_club_and_last_writer"
        else:
            attribution = "missing_key" if not key else "ambiguous" if candidates else "no_match"
            bucket = f"unattributed:{attribution}:{key}"
        date = show["date"]
        if isinstance(date, str):
            date = datetime.fromisoformat(date.replace("Z", "+00:00"))
        row = {
            "id": show["id"],
            "identities": identities,
            "raw_total": raw_total,
            "raw_blocked": raw_blocked,
            "rescued": rescued,
            "reasons": raw_reasons,
            "resolutions": resolutions,
            "cancelled": bool(show.get("is_cancelled")),
            "upcoming": date >= as_of and not show.get("is_cancelled"),
        }
        clubs[show["club_id"]]["shows"].append(row)
        groups.setdefault(bucket, {"source": None, "shows": []})["shows"].append(row)
        if identities and (
            any(v is True for v in identities.values()) or rescued or any(v is None for v in identities.values())
        ):
            evidence.append(
                {
                    "show_id": show["id"],
                    "club_id": show["club_id"],
                    "bucket": bucket,
                    "attribution": attribution,
                    "candidate_source_ids": candidates if organizer is None else [],
                    "resolved_identities": identities,
                    "raw_block_reasons": dict(raw_reasons),
                    "resolution_states": dict(resolutions),
                    "rescued_aliases": rescued,
                }
            )

    def metrics(rows):
        appearances = blocked = unknown = with_lineup = only = majority = 0
        distinct, block_reasons, states = {}, Counter(), Counter()
        for row in rows:
            values = row["identities"]
            n, b = len(values), sum(v is True for v in values.values())
            appearances += n
            blocked += b
            unknown += sum(v is None for v in values.values())
            with_lineup += n > 0
            only += n > 0 and b == n
            majority += b * 2 > n
            distinct.update(values)
            block_reasons.update(row["reasons"])
            states.update(row["resolutions"])
        return {
            "shows": len(rows),
            "cancelled_shows": sum(r["cancelled"] for r in rows),
            "shows_with_lineups": with_lineup,
            "missing_lineups": len(rows) - with_lineup,
            "lineup_coverage": with_lineup / len(rows) if rows else None,
            "blocked_only_shows": only,
            "majority_blocked_shows": majority,
            "appearances": appearances,
            "blocked_appearances": blocked,
            "unknown_appearances": unknown,
            "blocked_appearance_ratio": blocked / appearances if appearances else None,
            "distinct_performers": len(distinct),
            "blocked_distinct_performers": sum(v is True for v in distinct.values()),
            "blocked_distinct_ratio": sum(v is True for v in distinct.values()) / len(distinct) if distinct else None,
            "unblocked_is_not_verified_comedy": True,
            "rescued_alias_appearances": sum(r["rescued"] for r in rows),
            "raw_appearances": sum(r["raw_total"] for r in rows),
            "raw_blocked_appearances": sum(r["raw_blocked"] for r in rows),
            "block_reason_appearances": dict(sorted(block_reasons.items())),
            "resolution_states": dict(sorted(states.items())),
        }

    def windows(rows):
        return {"all_history": metrics(rows), "upcoming": metrics([r for r in rows if r["upcoming"]])}

    club_results = [{k: v for k, v in c.items() if k != "shows"} | windows(c["shows"]) for c in clubs.values()]

    def triage(raw=False):
        result = {}
        for window in ("all_history", "upcoming"):
            ms = [c[window] for c in club_results if c["visible"]]
            nkey, bkey = (
                ("raw_appearances", "raw_blocked_appearances") if raw else ("appearances", "blocked_appearances")
            )
            result[window] = {
                "visible_clubs_with_lineups": sum(m[nkey] > 0 for m in ms),
                "visible_majority_blocked_clubs": sum(m[bkey] * 2 > m[nkey] for m in ms),
                "visible_all_blocked_clubs": sum(m[nkey] > 0 and m[bkey] == m[nkey] for m in ms),
            }
        return result

    return {
        "as_of": as_of.isoformat(),
        "purpose": "triage_only_not_false_positive_totals",
        "triage": triage(),
        "legacy_raw_comparison": triage(True),
        "clubs": club_results,
        "feeds": [{"bucket": k, "source": g["source"], **windows(g["shows"])} for k, g in sorted(groups.items())],
        "show_evidence": evidence,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=datetime.fromisoformat, default=datetime.now(timezone.utc))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.as_of.tzinfo is None:
        parser.error("--as-of requires a timezone")
    report = analyze_snapshot(collect_snapshot(), args.as_of)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("as_of", "triage", "legacy_raw_comparison")}, indent=2))


if __name__ == "__main__":
    main()
