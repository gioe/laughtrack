"""Synchronous, transaction-fenced screening at the show write boundary."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field, replace
from typing import Any
from datetime import timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import re

from laughtrack.core.comedy_eligibility import (
    CanonicalPerson,
    DeniedName,
    EventEvidence,
    PerformerObservation,
    classify_comedy_eligibility,
    normalize_name,
)
from laughtrack.core.comedy_eligibility_store import (
    StagedCandidate,
    fingerprint,
    load_source,
    stage_candidate,
    verify_publication,
    link_published,
)
from laughtrack.core.comedy_eligibility_review import apply_review, baseline_identity_fingerprint
from laughtrack.core.comedy_eligibility_monitor import observe_show
from laughtrack.core.comedy_eligibility_review_store import load_review
from laughtrack.core.entities.club.comedy_policy import SourceComedyPolicy
from laughtrack.foundation.infrastructure.logger.logger import Logger

_COMEDY_BILLING = re.compile(
    r"\b(?:stand[ -]?up comedy|comedy (?:show|showcase|night|open mic)|(?:sketch|improv) comedy)\b", re.I
)
_MUSIC_BILLING = re.compile(r"\b(?:live music|dj set|(?:jazz|rock|blues|orchestra) concert|karaoke night)\b", re.I)
_SPORTS_BILLING = re.compile(r"\b(?:boxing match|basketball game|football game|wrestling match)\b", re.I)


def stamp_source(shows, source):
    """Called before both normal result delivery and early national chunk writes."""
    if source is None:
        return
    for show in shows:
        show.eligibility_source_id = source.id
        show.eligibility_gate_mode = source.comedy_policy.gate_mode


def capture_event_inputs(show, event):
    """Preserve raw evidence without making malformed metadata drop legacy events."""
    # SeatEngine transformers may remove title-shaped or reviewed label talents.
    # The pipeline supplies the original event, so eligibility still sees them.
    nested = event.get("event") if isinstance(event, dict) else None
    if isinstance(nested, dict) and "talents" in nested:
        talents = nested["talents"]
        names = [
            talent.get("name") if isinstance(talent, dict) else None
            for talent in talents
        ] if isinstance(talents, list) else []
        show.eligibility_performer_names = [name for name in names if isinstance(name, str) and name.strip()]
        show.eligibility_raw_performers_preserved = (
            isinstance(talents, list)
            and all(isinstance(name, str) and name.strip() for name in names)
        )
    raw = event.get("performers") if isinstance(event, dict) else getattr(event, "performers", None)
    if isinstance(raw, (list, tuple)):
        names = [
            p if isinstance(p, str) else p.get("name") if isinstance(p, dict) else getattr(p, "name", None) for p in raw
        ]
        show.eligibility_performer_names = [n for n in names if isinstance(n, str) and n.strip()]
        show.eligibility_raw_performers_preserved = True
    if not isinstance(event, dict) or "classifications" not in event:
        return
    embedded = event.get("_embedded")
    attractions = embedded.get("attractions") if isinstance(embedded, dict) else None
    if isinstance(attractions, list):
        show.eligibility_raw_performers_preserved = True
        show.eligibility_performer_names = [
            p["name"] for p in attractions if isinstance(p, dict) and isinstance(p.get("name"), str)
        ]
    classifications = event.get("classifications")
    if not isinstance(classifications, list):
        classifications = [None]
    for classification in classifications:
        if not isinstance(classification, dict):
            item = {
                "kind": "unknown",
                "provenance": "event_category",
                "detail": "Malformed Ticketmaster classifications",
            }
            if item not in show.eligibility_evidence:
                show.eligibility_evidence.append(item)
            continue
        for field in ("segment", "genre", "subGenre"):
            value = classification.get(field)
            name = value.get("name") if isinstance(value, dict) else None
            if not isinstance(name, str):
                continue
            kind = {"comedy": "comedy", "music": "music", "sports": "sports"}.get(name.lower())
            if kind:
                item = {"kind": kind, "provenance": "event_category", "detail": f"Ticketmaster {field}: {name}"}
                if item not in show.eligibility_evidence:
                    show.eligibility_evidence.append(item)


def event_evidence(show):
    evidence = [EventEvidence(**e) for e in (show.eligibility_evidence or [])]
    # Only qualified event billing; no venue names, biographies, tags or show_type.
    for kind, pattern in (("comedy", _COMEDY_BILLING), ("music", _MUSIC_BILLING), ("sports", _SPORTS_BILLING)):
        if pattern.search(show.name or ""):
            evidence.append(EventEvidence(kind, "event_billing", show.name))
    return evidence


def safe_url(value):
    parts = urlsplit(value or "")
    host = (parts.hostname or "").lower()
    if parts.port:
        host += f":{parts.port}"
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not re.search(r"token|secret|password|auth|credential|signature|api.?key|access.?key|session", k, re.I)
        and not k.lower().startswith("utm_")
        and k.lower() not in {"gclid", "fbclid"}
    ]
    fragment = parts.fragment
    if re.search(
        r"(?:^|[?&])[^=&]*(?:token|secret|password|auth|credential|signature|api.?key|access.?key|session)[^=&]*=",
        fragment,
        re.I,
    ):
        fragment = fragment.split("?", 1)[0] if "?" in fragment else ""
    return urlunsplit((parts.scheme.lower(), host, parts.path, urlencode(sorted(query)), fragment))


def _utc_date(show):
    # Show.to_unique_key treats legacy naive datetimes as UTC, not local time.
    return (
        show.date.replace(tzinfo=timezone.utc) if show.date.tzinfo is None else show.date.astimezone(timezone.utc)
    ).isoformat()


def candidate_payload(show):
    return {
        "name": show.name,
        "description": show.description,
        "club_id": show.club_id,
        "date": _utc_date(show),
        "room": show.room,
        "url": safe_url(show.show_page_url),
        "source_performance_id": show.source_performance_id,
        "performers": show.eligibility_performer_names,
        "raw_performers_preserved": show.eligibility_raw_performers_preserved,
        "evidence": show.eligibility_evidence,
        "tickets": [
            {"price": str(t.price), "type": t.type, "url": safe_url(t.purchase_url), "sold_out": t.sold_out}
            for t in show.tickets
        ],
    }


def event_key(show):
    if show.source_performance_id:
        return "native:" + show.source_performance_id
    if not show.show_page_url:
        raise ValueError("Cannot stage event without native identity or URL")
    return "fallback:" + fingerprint(
        {
            "url": safe_url(show.show_page_url),
            "date": _utc_date(show),
            "room": " ".join((show.room or "").split()),
            "club_id": show.club_id,
        }
    )


def _identity_snapshot(cursor, names):
    cursor.execute(
        """WITH RECURSIVE people AS (
      SELECT id,name,visible,parent_comedian_id,block_reason FROM comedians
      WHERE LOWER(BTRIM(REGEXP_REPLACE(REPLACE(name, CHR(160), ' '), '[[:space:]]+', ' ', 'g'))) = ANY(%s)
      UNION
      SELECT c.id,c.name,c.visible,c.parent_comedian_id,c.block_reason FROM comedians c
      JOIN people p ON p.parent_comedian_id=c.id
    ) SELECT * FROM people ORDER BY id""",
        (names,),
    )
    rows = cursor.fetchall()
    people = [CanonicalPerson(id=r[0], name=r[1], visible=r[2], parent_id=r[3], block_reason=r[4]) for r in rows]
    all_names = sorted(set(names) | {normalize_name(p.name) for p in people})
    cursor.execute(
        """SELECT name,reason FROM comedian_deny_list WHERE
      LOWER(BTRIM(REGEXP_REPLACE(REPLACE(name, CHR(160), ' '), '[[:space:]]+', ' ', 'g'))) = ANY(%s)
      ORDER BY name""",
        (all_names,),
    )
    denied = [DeniedName(r[0], r[1] or "deny_list") for r in cursor.fetchall()]
    return people, denied


@dataclass
class GateBatch:
    shows: list = field(default_factory=list)
    withheld: int = 0
    reconciliation_safe: bool = True


class EligibilityGate:
    def __init__(self, transaction):
        self.transaction = transaction

    def _source(self, cursor, show):
        sid = show.eligibility_source_id
        if sid is None:
            cursor.execute(
                "SELECT id FROM scraping_sources WHERE club_id=%s AND scraper_key=%s ORDER BY id",
                (show.club_id, show.last_scraped_by),
            )
            matches = cursor.fetchall()
            if len(matches) != 1:
                raise ValueError("Missing or ambiguous managed scraping source")
            sid = matches[0][0]
        source = load_source(cursor, sid, lock=True)
        if source is None or not source["enabled"]:
            raise ValueError("Scraping source missing or disabled")
        return source

    @contextmanager
    def screen(self, shows):
        outcome = GateBatch()
        prepared: list[tuple[Any, dict, StagedCandidate | None]] = []
        off_sources: dict[tuple, dict] = {}
        identity_snapshots = {}
        review_scopes = {}
        # Staging commits before the independently fenced public write attempt.
        for show in shows:
            if getattr(show, "eligibility_source_id", None) is None and (
                not getattr(show, "last_scraped_by", None) or show.last_scraped_by == "tour_dates"
            ):
                outcome.shows.append(show)
                continue
            show.eligibility_persisted = False
            source_key = (getattr(show, "eligibility_source_id", None), show.club_id, show.last_scraped_by)
            if source_key in off_sources and off_sources[source_key]["comedy_policy"] != "comedy_only":
                prepared.append((show, off_sources[source_key], None))
                continue
            source = off_sources.get(source_key)
            allow_shadow_fallback = False
            try:
                with self.transaction() as conn:
                    with conn.cursor() as cursor:
                        source = source or self._source(cursor, show)
                        mode = source["comedy_gate_mode"]
                        policy = SourceComedyPolicy.from_row(source)
                        staged = None
                        if mode == "off":
                            off_sources[source_key] = source
                        if mode != "off" or policy.policy == "comedy_only":
                            observe_show(cursor, source, show, identity_snapshots)
                        if mode != "off":
                            names = sorted(
                                {
                                    normalize_name(n)
                                    for n in (show.eligibility_performer_names or [])
                                    if isinstance(n, str) and n.strip()
                                }
                            )
                            if tuple(names) not in identity_snapshots:
                                identity_snapshots[tuple(names)] = _identity_snapshot(cursor, names)
                            people, denied = identity_snapshots[tuple(names)]
                            decision = classify_comedy_eligibility(
                                source_id=source["id"],
                                policy=policy,
                                evidence=event_evidence(show),
                                performers=[PerformerObservation(n) for n in names],
                                people=people,
                                denied=denied,
                            )
                            if names and not show.eligibility_raw_performers_preserved:
                                decision = replace(
                                    decision,
                                    lineup_status="partial",
                                    reason_codes=tuple(sorted((*decision.reason_codes, "raw_lineup_partial"))),
                                )
                            from laughtrack.core.comedy_eligibility_model import cached_decision

                            baseline = baseline_identity_fingerprint(decision, people, denied)
                            scope = (source["id"], event_key(show), fingerprint(candidate_payload(show)),
                                     baseline, policy.version)
                            review_scopes[id(show)] = scope
                            review_state = load_review(cursor, *scope)
                            decision, human_hold, human_present = apply_review(decision, review_state)
                            allow_shadow_fallback = not human_present
                            if not human_present:
                                decision = cached_decision(
                                    self.transaction, candidate_payload(show), decision, people, denied
                                )
                            staged = stage_candidate(
                                cursor,
                                source_id=source["id"],
                                event_key=event_key(show),
                                club_id=show.club_id,
                                payload=candidate_payload(show),
                                decision=decision,
                                gate_mode=mode,
                                baseline_identity_fingerprint=baseline,
                                review_version=review_state["review_version"],
                            )
                            if human_hold or (mode == "enforce" and decision.decision != "accept"):
                                outcome.withheld += 1
                                outcome.reconciliation_safe = False
                                continue
                        prepared.append((show, source, staged))
            except Exception as exc:
                outcome.reconciliation_safe = False
                Logger.warn(f"Eligibility staging failed: {exc}")
                # Recording failure may preserve shadow publication only under a
                # NEW source fence proving it is still enabled and in shadow mode.
                if source and source["comedy_gate_mode"] == "shadow" and allow_shadow_fallback:
                    prepared.append((show, source, None))
                else:
                    outcome.withheld += 1
        stack = ExitStack()
        verified: list[tuple[Any, StagedCandidate]] = []
        fenced_shows = []
        cursor = None
        conn = None
        try:
            if prepared:
                try:
                    conn = stack.enter_context(self.transaction())
                    cursor = stack.enter_context(conn.cursor())
                    # Acquire every source before candidates: no inverted lock order.
                    exclusive_sources = {s["id"] for _, s, staged in prepared
                                         if staged is None and s["comedy_gate_mode"] == "shadow"}
                    current_sources = {}
                    for sid in sorted({s["id"] for _, s, _ in prepared}):
                        if sid in exclusive_sources:
                            # Review apply and staging lock source SHARE first. An
                            # exclusive lock closes the no-candidate fallback race.
                            cursor.execute("SELECT id FROM scraping_sources WHERE id=%s FOR UPDATE", (sid,))
                        current_sources[sid] = load_source(cursor, sid, lock=sid not in exclusive_sources)
                    for show, source, staged in sorted(prepared, key=lambda x: (x[1]["id"], x[2].id if x[2] else 0)):
                        current = current_sources[source["id"]]
                        fresh = bool(
                            current
                            and current["enabled"]
                            and current["comedy_policy_version"] == source["comedy_policy_version"]
                            and current["comedy_gate_mode"] == source["comedy_gate_mode"]
                        )
                        if fresh and staged is None and source["comedy_gate_mode"] == "shadow":
                            review = load_review(cursor, *review_scopes[id(show)])
                            fresh = not review["review_version"] and not review.get("stale")
                        if fresh and (staged is None or verify_publication(cursor, staged)):
                            fenced_shows.append(show)
                            if staged:
                                verified.append((show, staged))
                        else:
                            outcome.withheld += 1
                            outcome.reconciliation_safe = False
                except Exception as exc:
                    Logger.warn(f"Eligibility publication fence failed: {exc}")
                    outcome.reconciliation_safe = False
                    if conn is not None:
                        conn.rollback()
                    outcome.withheld = len(shows) - len(outcome.shows)
                    fenced_shows = []
                    verified = []
                    stack.close()
            outcome.shows.extend(fenced_shows)
            yield outcome
            for show, staged in verified:
                if show.id is not None and show.eligibility_persisted:
                    try:
                        link_published(cursor, staged, show.id)
                    except Exception as exc:
                        outcome.reconciliation_safe = False
                        Logger.warn(f"Eligibility publication link failed: {exc}")
                        if conn is not None:
                            conn.rollback()
                        break
        except BaseException:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            stack.close()


def safe_to_reconcile(handler, result):
    """Absence cannot establish cancellation for gated or multiply-owned feeds."""
    if result.eligibility_source_id is None:
        return False
    try:
        with handler.transaction() as conn:
            with conn.cursor() as cursor:
                if result.eligibility_source_id is not None:
                    source = load_source(cursor, result.eligibility_source_id)
                    if not source or not source["enabled"] or source["comedy_gate_mode"] != "off":
                        return False
                cursor.execute("SELECT count(*) FROM scraping_sources WHERE club_id=%s", (result.club_id,))
                if cursor.fetchone()[0] > 1:
                    return False
                cursor.execute("SELECT to_regclass('comedy_event_publications')")
                if cursor.fetchone()[0] is not None:
                    cursor.execute(
                        "SELECT EXISTS(SELECT 1 FROM comedy_event_publications p JOIN shows s ON s.id=p.show_id WHERE s.club_id=%s)",
                        (result.club_id,),
                    )
                    if cursor.fetchone()[0]:
                        return False
                # Source-target and organizer ownership cannot be established by last writer.
                if result.is_synthetic or result.club_id is None:
                    return False
                return True
    except Exception as exc:
        Logger.warn(f"Eligibility reconciliation check failed: {exc}")
        return False
