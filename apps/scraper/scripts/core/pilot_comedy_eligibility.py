"""Replay saved SeatEngine payloads for a bounded, model-free comedy pilot.

Default operation only reads source configuration and canonical identity snapshots.
--stage-shadow explicitly records candidate observations through the normal gate;
it never invokes a public show writer. Saved raw input is kept separate from this
classifier output so reviewers can label provider evidence independently.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.core.comedy_eligibility import PerformerObservation, classify_comedy_eligibility, normalize_name
from laughtrack.core.comedy_eligibility_gate import (
    EligibilityGate,
    _identity_snapshot,
    candidate_payload,
    event_evidence,
    event_key,
    stamp_source,
)
from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy
from laughtrack.core.comedy_eligibility_review import apply_review, baseline_identity_fingerprint
from laughtrack.core.comedy_eligibility_review_store import load_review
from laughtrack.core.comedy_eligibility_store import fingerprint, stage_candidate
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.seatengine.scraper import SeatEngineScraper
from scripts.core.rollout_comedy_eligibility import _rows, source_fingerprint, validate_manifest


def _source(cursor, sid):
    cursor.execute("SELECT * FROM scraping_sources WHERE id=%s", (sid,))
    rows = _rows(cursor)
    if not rows or not rows[0]["enabled"] or rows[0]["scraper_key"] != "seatengine":
        raise ValueError(f"Source {sid} must be an enabled SeatEngine source")
    source = rows[0]
    if source.get("source_target_id") or source.get("metadata", {}).get("seatengine_venue_routes"):
        raise ValueError("Pilot requires a direct venue source; aggregate routing needs separate validation")
    return source


def transform_saved(club, entry):
    scraper = SeatEngineScraper(club)
    # No fetch calls: preserve the website captured by the real client's fetch.
    scraper.seatengine_client.venue_website = entry.get("venue_website")
    events = entry["events"]
    filtered = scraper._filter_title_patterns(events)
    if scraper._comedy_filter:
        filtered = asyncio.run(scraper._filter_comedy(filtered))

    def identity(event):
        return {
            "source_id": club.scraping_source.id,
            "event_id": (event.get("event") or {}).get("id"),
            "occurrence_id": event.get("id"),
        }

    retained = {id(event) for event in filtered}
    losses = {
        "upstream_filtered": [identity(event) for event in events if id(event) not in retained],
        "conversion_lost": [],
    }
    shows = []
    for event in filtered:
        converted = scraper.transformation_pipeline.transform(type("SavedEvents", (), {"event_list": [event]})())
        if not converted:
            losses["conversion_lost"].append(identity(event))
        shows.extend(converted)
    stamp_source(shows, club.scraping_source)
    for show in shows:
        show.last_scraped_by = "seatengine"
    return shows, len(filtered), losses


def run(
    saved,
    source_ids,
    transaction,
    *,
    stage_shadow=False,
    prospective_manifest=None,
    stage_audit_off=False,
    audit_selection=None,
):
    if stage_audit_off and (stage_shadow or prospective_manifest is not None):
        raise ValueError("Off audit staging cannot combine with shadow or prospective policy")
    selected = {}
    audit_versions = {}
    if stage_audit_off:
        if not isinstance(audit_selection, dict) or not audit_selection.get("adjudications"):
            raise ValueError("Off audit staging requires explicit known-event adjudications")
        for item in audit_selection["adjudications"]:
            if not item.get("reason") or not (item.get("evidence") or {}).get("url"):
                raise ValueError("Audit selection requires event-specific reason and evidence URL")
            for occurrence in item["occurrence_ids"]:
                selected[(item["source_id"], str(item["event_id"]), str(occurrence))] = item
        audit_versions = {s["source_id"]: s["version"] for s in audit_selection["source_policy_snapshot"]}
        if set(source_ids) != {key[0] for key in selected}:
            raise ValueError("Selected sources must match explicit audit events")
    proposals = {}
    if prospective_manifest is not None:
        validate_manifest(prospective_manifest)
        if stage_shadow:
            raise ValueError("Prospective policy evaluation cannot stage observations")
        proposals = {t["source_id"]: t for t in prospective_manifest["targets"]}
        if set(proposals) != set(source_ids):
            raise ValueError("Prospective manifest must match selected source IDs")
    if os.getenv("COMEDY_MODEL_ENABLED", "0") == "1" or os.getenv("COMEDY_MODEL_CACHE_ENABLED", "0") == "1":
        raise ValueError("Pilot requires COMEDY_MODEL_ENABLED=0 and COMEDY_MODEL_CACHE_ENABLED=0")
    if not source_ids or len(set(source_ids)) != len(source_ids) or len(source_ids) > 100:
        raise ValueError("Select 1-100 distinct source IDs explicitly")
    entries = saved.get("sources", [])
    by_id = {entry["source_id"]: entry for entry in entries}
    if len(by_id) != len(entries) or any(sid not in by_id for sid in source_ids):
        raise ValueError("Saved source IDs are missing or duplicated")
    prepared = []
    # Validate the full selection before any optional staging.
    with transaction() as conn:
        with conn.cursor() as cursor:
            for sid in sorted(source_ids):
                source = _source(cursor, sid)
                entry = by_id[sid]
                if stage_audit_off:
                    if source["comedy_gate_mode"] != "off" or source["comedy_policy_version"] != audit_versions.get(
                        sid
                    ):
                        raise ValueError("Audit source must remain off at the reviewed policy version")
                    chosen = [
                        e
                        for e in entry["events"]
                        if (sid, str((e.get("event") or {}).get("id")), str(e.get("id"))) in selected
                    ]
                    found = {(sid, str(e["event"]["id"]), str(e["id"])) for e in chosen}
                    if found != {key for key in selected if key[0] == sid}:
                        raise ValueError("Saved payload is missing explicitly selected audit occurrences")
                    # Exclude every unselected group BEFORE any transform or classifier.
                    entry = {**entry, "events": chosen}
                typed = ScrapingSource.from_dict(source)
                if entry["club_id"] != source["club_id"] or str(entry["venue_id"]) != str(
                    typed.typed_id_for_platform("seatengine")
                ):
                    raise ValueError(f"Saved source {sid} ownership or provider account differs")
                if not isinstance(entry.get("events"), list):
                    raise ValueError("Saved events must be an array")
                if stage_shadow and (
                    source["comedy_policy"] not in {"mixed", "comedy_only"} or source["comedy_gate_mode"] != "shadow"
                ):
                    raise ValueError(f"Source {sid} must already be mixed/shadow or comedy_only/shadow")
                if sid in proposals and (
                    proposals[sid]["expected_version"] != source["comedy_policy_version"]
                    or proposals[sid]["config_fingerprint"] != source_fingerprint(source)
                ):
                    raise ValueError(f"Source {sid} prospective configuration/version changed")
                cursor.execute("SELECT * FROM clubs WHERE id=%s", (source["club_id"],))
                clubs = _rows(cursor)
                if len(clubs) != 1:
                    raise ValueError(f"Source {sid} venue missing")
                club = Club.from_db_row({**clubs[0], "scraping_sources": [source]})
                club.active_scraping_source = typed
                prepared.append((source, club, entry))
    reports = []
    for source, club, entry in prepared:
        shows, postfilter, losses = transform_saved(club, entry)
        decisions = []
        policy = SourceComedyPolicy.from_row(source)
        if source["id"] in proposals:
            proposed = proposals[source["id"]]
            policy = SourceComedyPolicy(
                proposed["policy"],
                proposed["gate_mode"],
                policy.version + 1,
                reviewed_by=prospective_manifest["actor"],
                reviewed_at=(proposed.get("source_trust_evidence") or {}).get("reviewed_at"),
                evidence={"prospective": True, "manifest": prospective_manifest},
            )
        with transaction() as conn:
            with conn.cursor() as cursor:
                identities = {}
                for show in shows:
                    names = tuple(
                        sorted(
                            {
                                normalize_name(name)
                                for name in (show.eligibility_performer_names or [])
                                if isinstance(name, str) and name.strip()
                            }
                        )
                    )
                    if names not in identities:
                        identities[names] = _identity_snapshot(cursor, list(names))
                    people, denied = identities[names]
                    decision = classify_comedy_eligibility(
                        source_id=source["id"],
                        policy=SourceComedyPolicy(version=source["comedy_policy_version"]),
                        evidence=event_evidence(show),
                        people=people,
                        denied=denied,
                        performers=[PerformerObservation(n) for n in names],
                    )
                    if names and not show.eligibility_raw_performers_preserved:
                        decision = replace(
                            decision,
                            lineup_status="partial",
                            reason_codes=tuple(sorted((*decision.reason_codes, "raw_lineup_partial"))),
                        )
                    effective = classify_comedy_eligibility(
                        source_id=source["id"],
                        policy=policy,
                        evidence=event_evidence(show),
                        people=people,
                        denied=denied,
                        performers=[PerformerObservation(n) for n in names],
                    )
                    if names and not show.eligibility_raw_performers_preserved:
                        effective = replace(
                            effective,
                            lineup_status="partial",
                            reason_codes=tuple(sorted((*effective.reason_codes, "raw_lineup_partial"))),
                        )
                    review = load_review(
                        cursor,
                        source["id"],
                        event_key(show),
                        fingerprint(candidate_payload(show)),
                        baseline_identity_fingerprint(effective, people, denied),
                        policy.version,
                    )
                    effective, human_hold, human_present = apply_review(effective, review)
                    decisions.append(
                        {
                            "event_key": event_key(show),
                            "payload": candidate_payload(show),
                            "baseline": decision.to_dict(),
                            "effective": effective.to_dict(),
                            "baseline_identity_fingerprint": baseline_identity_fingerprint(effective, people, denied),
                            "review": {
                                "version": review["review_version"],
                                "stale": review.get("stale", False),
                                "action_id": (review.get("review") or {}).get("id"),
                                "human_hold": human_hold,
                                "present": human_present,
                            },
                        }
                    )
        stage_result = None
        if stage_audit_off:
            staged = []
            with transaction() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM scraping_sources WHERE id=%s FOR SHARE", (source["id"],))
                    live = _rows(cursor)
                    if (
                        not live
                        or not live[0]["enabled"]
                        or live[0]["comedy_gate_mode"] != "off"
                        or live[0]["comedy_policy_version"] != source["comedy_policy_version"]
                        or source_fingerprint(live[0]) != source_fingerprint(source)
                    ):
                        raise ValueError("Source changed before off audit staging")
                    for decision in decisions:
                        token = stage_candidate(
                            cursor,
                            source_id=source["id"],
                            event_key=decision["event_key"],
                            club_id=club.id,
                            payload=decision["payload"],
                            decision=decision["effective"],
                            gate_mode="off",
                            baseline_identity_fingerprint=decision["baseline_identity_fingerprint"],
                            review_version=decision["review"]["version"],
                            allow_off_audit=True,
                        )
                        staged.append(asdict(token))
            stage_result = {"kind": "off_audit", "observations": staged, "public_writes": 0}
        if stage_shadow:

            @contextmanager
            def shadow_transaction():
                with transaction() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT * FROM scraping_sources WHERE id=%s FOR SHARE", (source["id"],))
                        live = _rows(cursor)
                        if (
                            not live
                            or not live[0]["enabled"]
                            or live[0]["comedy_policy"] != source["comedy_policy"]
                            or live[0]["comedy_gate_mode"] != "shadow"
                            or live[0]["comedy_policy_version"] != source["comedy_policy_version"]
                            or source_fingerprint(live[0]) != source_fingerprint(source)
                        ):
                            raise ValueError("Source changed during pilot; shadow staging refused")
                    yield conn

            with EligibilityGate(shadow_transaction).screen(shows) as screened:
                # Deliberately no writer; no show IDs or publication flags are set.
                stage_result = {
                    "admitted": len(screened.shows),
                    "withheld": screened.withheld,
                    "reconciliation_safe": screened.reconciliation_safe,
                    "public_writes": 0,
                }
        reports.append(
            {
                "source_id": source["id"],
                "club_id": club.id,
                "policy_version": source["comedy_policy_version"],
                "config_fingerprint": source_fingerprint(source),
                "provider_occurrences": len(entry["events"]),
                "provider_event_groups": len({str((e.get("event") or {}).get("id")) for e in entry["events"]}),
                "post_filter_occurrences": postfilter,
                "transformed_occurrences": len(shows),
                "unique_event_keys": len({d["event_key"] for d in decisions}),
                "baseline_decisions": dict(Counter(d["baseline"]["decision"] for d in decisions)),
                "effective_decisions": dict(Counter(d["effective"]["decision"] for d in decisions)),
                "effective_policy": asdict(policy),
                "evaluation_kind": "prospective" if prospective_manifest else "configured",
                "publication_semantics": "Eligibility evaluation only; off mode bypasses screening, shadow does not enforce classifier decisions. No public writer invoked.",
                "transformation_losses": {
                    "upstream_filtered": len(entry["events"]) - postfilter,
                    "conversion_lost": postfilter - len(shows),
                },
                "transformation_loss_identifiers": losses,
                "lineup_coverage": dict(Counter(d["baseline"]["lineup_status"] for d in decisions)),
                "decisions": decisions,
                "shadow": stage_result if stage_shadow else None,
                "audit_off": stage_result if stage_audit_off else None,
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_fetched_at": saved.get("fetched_at"),
        "stage_shadow": stage_shadow,
        "stage_audit_off": stage_audit_off,
        "model_requests": 0,
        "model_cost": 0,
        "sources": reports,
    }


def main(argv=None, *, transaction=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-id", type=int, action="append", required=True)
    parser.add_argument("--stage-shadow", action="store_true")
    parser.add_argument(
        "--stage-audit-off", action="store_true", help="Explicitly stage known audit events without enabling screening"
    )
    parser.add_argument(
        "--audit-selection", type=Path, help="Reviewed adjudication manifest restricting events/occurrences"
    )
    parser.add_argument(
        "--prospective-manifest", type=Path, help="Read-only policy simulation; never fabricates reviews"
    )
    args = parser.parse_args(argv)
    if transaction is None:
        from dotenv import load_dotenv

        load_dotenv(_root / ".env")
        from laughtrack.adapters.db import get_transaction

        transaction = get_transaction
    result = run(
        json.loads(args.input.read_text()),
        args.source_id,
        transaction,
        stage_shadow=args.stage_shadow,
        prospective_manifest=json.loads(args.prospective_manifest.read_text()) if args.prospective_manifest else None,
        stage_audit_off=args.stage_audit_off,
        audit_selection=json.loads(args.audit_selection.read_text()) if args.audit_selection else None,
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    print(
        json.dumps(
            {"output": str(args.output), "source_count": len(result["sources"]), "stage_shadow": args.stage_shadow}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
