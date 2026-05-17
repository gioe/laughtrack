#!/usr/bin/env python3
"""Detect comedian appearances in canonical podcast episodes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from psycopg2.extras import execute_values

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection
from laughtrack.core.podcast_appearance_auto_acceptance import (
    AutoAcceptanceCandidate,
    apply_auto_acceptance_rules,
    normalize_match_text,
)

_SOURCE = "podcast_index"
_AUTO_ACCEPT_TITLE_CONFIDENCE = 0.95
_HOST_ASSOCIATION_TYPES = frozenset({"host", "cohost"})

_GUEST_TITLE_RE = re.compile(
    r"\b(with|ft\.?|feat\.?|featuring|guest|welcomes?|interviews?|in conversation with)\b",
    re.IGNORECASE,
)
_HOST_TEXT_RE = re.compile(r"\b(hosted by|host|co[- ]?host|owner)\b", re.IGNORECASE)
_MENTION_TEXT_RE = re.compile(r"\b(mention|mentioned|shout[- ]?out|talk about|discuss)\b", re.IGNORECASE)

_GET_MATCH_COMEDIANS_SQL = """
    SELECT
        c.id,
        c.name,
        COALESCE(
            array_remove(array_agg(a.name ORDER BY a.name), NULL),
            ARRAY[]::text[]
        ) AS aliases
    FROM comedians c
    LEFT JOIN comedians a ON a.parent_comedian_id = c.id
        AND NULLIF(BTRIM(a.name), '') IS NOT NULL
    WHERE c.parent_comedian_id IS NULL
      AND NULLIF(BTRIM(c.name), '') IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM comedian_deny_list d
          WHERE LOWER(BTRIM(d.name)) = LOWER(BTRIM(c.name))
      )
      {extra_filter}
    GROUP BY c.id, c.name
    ORDER BY c.popularity DESC NULLS LAST, c.total_shows DESC NULLS LAST, c.id
"""

_GET_EPISODES_SQL = """
    SELECT
        pe.id,
        pe.podcast_id,
        pe.source,
        pe.source_episode_id,
        p.title AS podcast_title,
        p.author_name AS podcast_author,
        pe.title,
        pe.description,
        pe.episode_url,
        pe.source_payload,
        COALESCE(
            array_remove(array_agg(cp.comedian_id ORDER BY cp.comedian_id), NULL),
            ARRAY[]::int[]
        ) AS host_comedian_ids,
        COALESCE(
            array_remove(array_agg(cp.association_type ORDER BY cp.comedian_id), NULL),
            ARRAY[]::text[]
        ) AS host_association_types
    FROM podcast_episodes pe
    JOIN podcasts p ON p.id = pe.podcast_id
    LEFT JOIN comedian_podcasts cp ON cp.podcast_id = p.id
        AND cp.review_status = 'accepted'
        AND cp.association_type IN ('host', 'cohost', 'owner')
    WHERE p.source = %s
      AND pe.source = %s
      AND EXISTS (
          SELECT 1
          FROM comedian_podcasts accepted_cp
          WHERE accepted_cp.podcast_id = p.id
            AND accepted_cp.review_status = 'accepted'
      )
      {extra_filter}
    GROUP BY pe.id, pe.podcast_id, pe.source, pe.source_episode_id, p.title, p.author_name,
        pe.title, pe.description, pe.episode_url, pe.source_payload
    ORDER BY pe.release_date DESC NULLS LAST, pe.id DESC
"""

_UPSERT_REVIEW_SQL = """
    INSERT INTO episode_appearance_reviews (
        comedian_id,
        episode_id,
        source,
        source_episode_id,
        candidate_status,
        appearance_role,
        confidence,
        evidence
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
    ON CONFLICT (comedian_id, source, source_episode_id) DO UPDATE SET
        episode_id = EXCLUDED.episode_id,
        candidate_status = EXCLUDED.candidate_status,
        appearance_role = EXCLUDED.appearance_role,
        confidence = EXCLUDED.confidence,
        evidence = EXCLUDED.evidence,
        updated_at = NOW()
"""

_UPSERT_REVIEW_BULK_SQL = """
    INSERT INTO episode_appearance_reviews (
        comedian_id,
        episode_id,
        source,
        source_episode_id,
        candidate_status,
        appearance_role,
        confidence,
        evidence
    )
    VALUES %s
    ON CONFLICT (comedian_id, source, source_episode_id) DO UPDATE SET
        episode_id = EXCLUDED.episode_id,
        candidate_status = EXCLUDED.candidate_status,
        appearance_role = EXCLUDED.appearance_role,
        confidence = EXCLUDED.confidence,
        evidence = EXCLUDED.evidence,
        updated_at = NOW()
"""

_UPSERT_APPEARANCE_SQL = """
    INSERT INTO episode_appearances (
        comedian_id,
        episode_id,
        source,
        appearance_role,
        review_status,
        confidence,
        reviewed_by,
        reviewed_at,
        evidence
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s::jsonb)
    ON CONFLICT (comedian_id, episode_id, source) DO UPDATE SET
        appearance_role = EXCLUDED.appearance_role,
        review_status = EXCLUDED.review_status,
        confidence = EXCLUDED.confidence,
        reviewed_by = EXCLUDED.reviewed_by,
        reviewed_at = EXCLUDED.reviewed_at,
        evidence = EXCLUDED.evidence,
        updated_at = NOW()
"""

_UPSERT_APPEARANCE_BULK_SQL = """
    INSERT INTO episode_appearances (
        comedian_id,
        episode_id,
        source,
        appearance_role,
        review_status,
        confidence,
        reviewed_by,
        reviewed_at,
        evidence
    )
    VALUES %s
    ON CONFLICT (comedian_id, episode_id, source) DO UPDATE SET
        appearance_role = EXCLUDED.appearance_role,
        review_status = EXCLUDED.review_status,
        confidence = EXCLUDED.confidence,
        reviewed_by = EXCLUDED.reviewed_by,
        reviewed_at = EXCLUDED.reviewed_at,
        evidence = EXCLUDED.evidence,
        updated_at = NOW()
"""


@dataclass(frozen=True)
class MatchComedian:
    comedian_id: int
    name: str
    aliases: list[str]


@dataclass(frozen=True)
class MatchTerm:
    raw: str
    normalized: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class PodcastEpisodeCandidateInput:
    episode_id: int
    podcast_id: int
    source: str
    source_episode_id: str
    podcast_title: str
    podcast_author: str
    title: str
    description: str
    episode_url: str
    source_payload: dict[str, Any]
    host_comedian_ids: list[int]
    host_association_types: list[str]


@dataclass(frozen=True)
class EpisodeAppearanceCandidate:
    comedian_id: int
    episode_id: int
    source: str
    source_episode_id: str
    matched_name: str
    source_field: str
    role_guess: str
    confidence: float
    evidence_text: str
    evidence: dict[str, Any]
    status: str


@dataclass
class DetectSummary:
    candidates: int = 0
    auto_accepted: int = 0
    pending: int = 0
    ignored: int = 0
    written: int = 0


def _term_variants(term: str) -> list[str]:
    normalized = normalize_match_text(term)
    if not normalized:
        return []
    words = normalized.split()
    variants = {normalized}
    if len(words) >= 2 and all(len(word) == 1 for word in words[:-1]):
        variants.add("".join(words[:-1]) + " " + words[-1])
        variants.add("".join(words))
    if len(words) == 3 and len(words[0]) == len(words[1]) == 1:
        variants.add(f"{words[0]}{words[1]} {words[2]}")
        variants.add(f"{words[0]} {words[1]}{words[2]}")
        variants.add(f"{words[0]}{words[1]}{words[2]}")
    return sorted(variants, key=lambda value: (-len(value), value))


def _compile_term_pattern(variant: str) -> re.Pattern[str]:
    words = variant.split()
    separator = r"[\W_]*" if len(words) == 1 else r"[\W_]+"
    body = separator.join(re.escape(word) for word in words)
    return re.compile(rf"(?<![a-z0-9]){body}(?![a-z0-9])", re.IGNORECASE)


def build_match_terms(comedian: MatchComedian, *, include_aliases: bool = True) -> list[MatchTerm]:
    terms: list[MatchTerm] = []
    seen: set[str] = set()
    raw_terms = [comedian.name, *comedian.aliases] if include_aliases else [comedian.name]
    for raw in raw_terms:
        cleaned = str(raw or "").strip()
        if not cleaned:
            continue
        for variant in _term_variants(cleaned):
            if variant in seen:
                continue
            seen.add(variant)
            terms.append(MatchTerm(cleaned, variant, _compile_term_pattern(variant)))
    return terms


def _best_field_match(term: MatchTerm, episode: PodcastEpisodeCandidateInput) -> Optional[tuple[str, str]]:
    for field, text in (("title", episode.title), ("description", episode.description or "")):
        match = term.pattern.search(text or "")
        if match:
            return field, match.group(0)
    return None


def _guess_role(
    *,
    comedian: MatchComedian,
    episode: PodcastEpisodeCandidateInput,
    source_field: str,
    evidence_text: str,
) -> str:
    text = f"{episode.title} {episode.description or ''}"
    if comedian.comedian_id in episode.host_comedian_ids:
        if _HOST_TEXT_RE.search(text):
            return "host"
        return "unknown"
    if source_field == "description" and _MENTION_TEXT_RE.search(text):
        return "mention"
    if source_field == "title" and (_GUEST_TITLE_RE.search(episode.title) or evidence_text):
        return "guest"
    if source_field == "description":
        return "mention"
    return "unknown"


def _confidence(source_field: str, role: str, term: MatchTerm) -> float:
    score = 0.72 if source_field == "title" else 0.48
    if role == "guest":
        score += 0.22
    elif role == "host":
        score += 0.08
    elif role == "mention":
        score -= 0.08
    elif role == "unknown":
        score -= 0.16
    if len(term.normalized.split()) >= 2:
        score += 0.03
    return max(0.05, min(round(score, 2), 0.99))


def _person_entries(source_payload: dict[str, Any]) -> list[dict[str, Any]]:
    persons = source_payload.get("persons") if isinstance(source_payload, dict) else None
    if not isinstance(persons, list):
        return []
    return [person for person in persons if isinstance(person, dict)]


def _person_role_is_guest(role: str) -> bool:
    normalized = normalize_match_text(role)
    return bool(normalized) and "guest" in normalized.split()


def _person_match_candidate(
    *,
    comedian: MatchComedian,
    episode: PodcastEpisodeCandidateInput,
    person: dict[str, Any],
    auto_accept: bool,
) -> Optional[EpisodeAppearanceCandidate]:
    role = str(person.get("role") or "")
    if not _person_role_is_guest(role):
        return None
    person_name = str(person.get("name") or "").strip()
    if not person_name:
        return None
    if normalize_match_text(person_name) != normalize_match_text(comedian.name):
        return None
    evidence = {
        "matched_name": comedian.name,
        "normalized_match": normalize_match_text(comedian.name),
        "source_field": "persons",
        "match_source": "podcast_index_person",
        "role_guess": "guest",
        "evidence_text": person_name,
        "podcast_title": episode.podcast_title,
        "episode_title": episode.title,
        "episode_url": episode.episode_url,
        "host_comedian_ids": episode.host_comedian_ids,
        "host_association_types": episode.host_association_types,
        "podcast_index_person_id": person.get("id"),
        "podcast_index_person_name": person_name,
        "podcast_index_person_role": role,
        "podcast_index_person_href": person.get("href"),
        "podcast_index_person_img": person.get("img"),
        "podcast_index_person_group": person.get("group"),
        "detected_by": "detect_podcast_episode_appearances",
    }
    status, evidence = _apply_rules(
        auto_accept=auto_accept,
        candidate=AutoAcceptanceCandidate(
            candidate_id=0,
            comedian_id=comedian.comedian_id,
            comedian_name=comedian.name,
            podcast_title=episode.podcast_title,
            podcast_author=episode.podcast_author,
            episode_title=episode.title,
            role_guess="guest",
            confidence=0.99,
            source=episode.source,
            source_field="persons",
            evidence_text=person_name,
            evidence=evidence,
            host_association_types=episode.host_association_types,
        ),
    )
    return EpisodeAppearanceCandidate(
        comedian_id=comedian.comedian_id,
        episode_id=episode.episode_id,
        source=episode.source,
        source_episode_id=episode.source_episode_id,
        matched_name=comedian.name,
        source_field="persons",
        role_guess="guest",
        confidence=0.99,
        evidence_text=person_name,
        evidence=evidence,
        status=status,
    )


def _comedian_host_association_types(
    comedian: MatchComedian,
    episode: PodcastEpisodeCandidateInput,
) -> list[str]:
    return [
        association_type
        for host_id, association_type in zip(episode.host_comedian_ids, episode.host_association_types)
        if host_id == comedian.comedian_id
    ]


def _host_relationship_candidate(
    *,
    comedian: MatchComedian,
    episode: PodcastEpisodeCandidateInput,
    association_types: list[str],
    auto_accept: bool,
) -> Optional[EpisodeAppearanceCandidate]:
    relationship_types = [normalize_match_text(value) for value in association_types]
    role = next((value for value in relationship_types if value in _HOST_ASSOCIATION_TYPES), None)
    if role is None:
        return None
    evidence = {
        "matched_name": comedian.name,
        "normalized_match": normalize_match_text(comedian.name),
        "source_field": "podcast_relationship",
        "role_guess": role,
        "evidence_text": comedian.name,
        "podcast_title": episode.podcast_title,
        "episode_title": episode.title,
        "episode_url": episode.episode_url,
        "host_comedian_ids": episode.host_comedian_ids,
        "host_association_types": episode.host_association_types,
        "detected_by": "detect_podcast_episode_appearances",
    }
    status, evidence = _apply_rules(
        auto_accept=auto_accept,
        candidate=AutoAcceptanceCandidate(
            candidate_id=0,
            comedian_id=comedian.comedian_id,
            comedian_name=comedian.name,
            podcast_title=episode.podcast_title,
            podcast_author=episode.podcast_author,
            episode_title=episode.title,
            role_guess=role,
            confidence=0.99,
            source=episode.source,
            source_field="podcast_relationship",
            evidence_text=comedian.name,
            evidence=evidence,
            host_association_types=relationship_types,
        ),
    )
    return EpisodeAppearanceCandidate(
        comedian_id=comedian.comedian_id,
        episode_id=episode.episode_id,
        source=episode.source,
        source_episode_id=episode.source_episode_id,
        matched_name=comedian.name,
        source_field="podcast_relationship",
        role_guess=role,
        confidence=0.99,
        evidence_text=comedian.name,
        evidence=evidence,
        status=status,
    )


def _apply_rules(
    *,
    auto_accept: bool,
    candidate: AutoAcceptanceCandidate,
) -> tuple[str, dict[str, Any]]:
    if not auto_accept:
        return "pending", dict(candidate.evidence)
    result = apply_auto_acceptance_rules(candidate)
    return result.status, result.evidence


def _normalized_text_matches(
    text: str,
    terms_by_normalized: dict[str, list[tuple[MatchComedian, MatchTerm]]],
    max_term_words: int,
) -> list[tuple[MatchComedian, MatchTerm]]:
    words = normalize_match_text(text).split()
    if not words:
        return []
    matches: list[tuple[MatchComedian, MatchTerm]] = []
    seen: set[tuple[int, str]] = set()
    for start in range(len(words)):
        for size in range(1, max_term_words + 1):
            end = start + size
            if end > len(words):
                break
            normalized = " ".join(words[start:end])
            for comedian, term in terms_by_normalized.get(normalized, []):
                key = (comedian.comedian_id, term.normalized)
                if key in seen:
                    continue
                seen.add(key)
                matches.append((comedian, term))
    return matches


def detect_episode_candidates(
    comedians: list[MatchComedian],
    episodes: list[PodcastEpisodeCandidateInput],
    *,
    include_aliases: bool = True,
    auto_accept: bool = True,
) -> list[EpisodeAppearanceCandidate]:
    candidates: list[EpisodeAppearanceCandidate] = []
    terms_by_comedian_id = {
        comedian.comedian_id: build_match_terms(comedian, include_aliases=include_aliases)
        for comedian in comedians
    }
    comedians_by_id = {comedian.comedian_id: comedian for comedian in comedians}
    comedians_by_normalized_name: dict[str, list[MatchComedian]] = defaultdict(list)
    terms_by_normalized: dict[str, list[tuple[MatchComedian, MatchTerm]]] = defaultdict(list)
    max_term_words = 1
    for comedian in comedians:
        normalized_name = normalize_match_text(comedian.name)
        if normalized_name:
            comedians_by_normalized_name[normalized_name].append(comedian)
        for term in terms_by_comedian_id[comedian.comedian_id]:
            terms_by_normalized[term.normalized].append((comedian, term))
            max_term_words = max(max_term_words, len(term.normalized.split()))

    for episode in episodes:
        text_matches_by_comedian_id: dict[int, list[tuple[str, str, MatchTerm]]] = defaultdict(list)
        for source_field, text in (("title", episode.title), ("description", episode.description or "")):
            for comedian, term in _normalized_text_matches(text, terms_by_normalized, max_term_words):
                text_matches_by_comedian_id[comedian.comedian_id].append((source_field, term.raw, term))

        person_matches_by_comedian_id: dict[int, dict[str, Any]] = {}
        for person in _person_entries(episode.source_payload):
            if not _person_role_is_guest(str(person.get("role") or "")):
                continue
            person_name = str(person.get("name") or "").strip()
            if not person_name:
                continue
            for comedian in comedians_by_normalized_name.get(normalize_match_text(person_name), []):
                person_matches_by_comedian_id[comedian.comedian_id] = person

        episode_comedian_ids = set(text_matches_by_comedian_id)
        episode_comedian_ids.update(person_matches_by_comedian_id)
        episode_comedian_ids.update(episode.host_comedian_ids)

        for comedian_id in episode_comedian_ids:
            comedian = comedians_by_id.get(comedian_id)
            if comedian is None:
                continue
            host_association_types = _comedian_host_association_types(comedian, episode)
            if host_association_types:
                host_candidate = _host_relationship_candidate(
                    comedian=comedian,
                    episode=episode,
                    association_types=host_association_types,
                    auto_accept=auto_accept,
                )
                if host_candidate is not None:
                    candidates.append(host_candidate)
                continue
            if comedian.comedian_id in episode.host_comedian_ids:
                continue
            best: Optional[EpisodeAppearanceCandidate] = None
            person = person_matches_by_comedian_id.get(comedian.comedian_id)
            if person is not None:
                person_candidate = _person_match_candidate(
                    comedian=comedian,
                    episode=episode,
                    person=person,
                    auto_accept=auto_accept,
                )
                if person_candidate is not None:
                    best = person_candidate
            for source_field, evidence_text, term in text_matches_by_comedian_id.get(
                comedian.comedian_id,
                [],
            ):
                if best is not None and best.source_field == "persons":
                    break
                role = _guess_role(
                    comedian=comedian,
                    episode=episode,
                    source_field=source_field,
                    evidence_text=evidence_text,
                )
                confidence = _confidence(source_field, role, term)
                evidence = {
                    "matched_name": term.raw,
                    "normalized_match": term.normalized,
                    "source_field": source_field,
                    "role_guess": role,
                    "evidence_text": evidence_text,
                    "podcast_title": episode.podcast_title,
                    "episode_title": episode.title,
                    "episode_url": episode.episode_url,
                    "host_comedian_ids": episode.host_comedian_ids,
                    "host_association_types": episode.host_association_types,
                    "detected_by": "detect_podcast_episode_appearances",
                }
                status, evidence = _apply_rules(
                    auto_accept=auto_accept,
                    candidate=AutoAcceptanceCandidate(
                        candidate_id=0,
                        comedian_id=comedian.comedian_id,
                        comedian_name=comedian.name,
                        podcast_title=episode.podcast_title,
                        podcast_author=episode.podcast_author,
                        episode_title=episode.title,
                        role_guess=role,
                        confidence=confidence,
                        source=episode.source,
                        source_field=source_field,
                        evidence_text=evidence_text,
                        evidence=evidence,
                        host_association_types=episode.host_association_types,
                    ),
                )
                candidate = EpisodeAppearanceCandidate(
                    comedian_id=comedian.comedian_id,
                    episode_id=episode.episode_id,
                    source=episode.source,
                    source_episode_id=episode.source_episode_id,
                    matched_name=term.raw,
                    source_field=source_field,
                    role_guess=role,
                    confidence=confidence,
                    evidence_text=evidence_text,
                    evidence=evidence,
                    status=status,
                )
                if best is None or candidate.confidence > best.confidence:
                    best = candidate
            if best is not None:
                candidates.append(best)
    candidates.sort(key=lambda c: (c.episode_id, c.comedian_id, -c.confidence))
    return candidates


def load_match_comedians(
    *,
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]] = None,
    limit: Optional[int] = None,
) -> list[MatchComedian]:
    with get_connection() as conn:
        return load_match_comedians_from_conn(
            conn,
            comedian_ids=comedian_ids,
            comedian_names=comedian_names,
            limit=limit,
        )


def load_match_comedians_from_conn(
    conn: Any,
    *,
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]] = None,
    limit: Optional[int] = None,
) -> list[MatchComedian]:
    filters: list[str] = []
    params: list[Any] = []
    if comedian_ids:
        filters.append("AND c.id = ANY(%s::int[])")
        params.append(comedian_ids)
    if comedian_names:
        filters.append("AND c.name = ANY(%s::text[])")
        params.append(comedian_names)
    query = _GET_MATCH_COMEDIANS_SQL.format(extra_filter="\n      ".join(filters))
    if limit:
        query += "\n    LIMIT %s"
        params.append(int(limit))
    with conn.cursor() as cur:
        cur.execute(query, tuple(params) if params else None)
        return [MatchComedian(int(row[0]), str(row[1]), list(row[2] or [])) for row in cur.fetchall()]


def load_episode_inputs(
    *,
    episode_ids: Optional[list[int]] = None,
    limit: Optional[int] = None,
) -> list[PodcastEpisodeCandidateInput]:
    with get_connection() as conn:
        return load_episode_inputs_from_conn(conn, episode_ids=episode_ids, limit=limit)


def load_episode_inputs_from_conn(
    conn: Any,
    *,
    episode_ids: Optional[list[int]] = None,
    limit: Optional[int] = None,
) -> list[PodcastEpisodeCandidateInput]:
    filters: list[str] = []
    params: list[Any] = [_SOURCE, _SOURCE]
    if episode_ids:
        filters.append("AND pe.id = ANY(%s::int[])")
        params.append(episode_ids)
    query = _GET_EPISODES_SQL.format(extra_filter="\n      ".join(filters))
    if limit:
        query += "\n    LIMIT %s"
        params.append(int(limit))
    with conn.cursor() as cur:
        cur.execute(query, tuple(params))
        return [
            PodcastEpisodeCandidateInput(
                episode_id=int(row[0]),
                podcast_id=int(row[1]),
                source=str(row[2]),
                source_episode_id=str(row[3]),
                podcast_title=str(row[4] or ""),
                podcast_author=str(row[5] or ""),
                title=str(row[6] or ""),
                description=str(row[7] or ""),
                episode_url=str(row[8] or ""),
                source_payload=dict(row[9] or {}),
                host_comedian_ids=[int(v) for v in (row[10] or [])],
                host_association_types=[str(v) for v in (row[11] or [])],
            )
            for row in cur.fetchall()
        ]


def persist_candidates(candidates: list[EpisodeAppearanceCandidate], dry_run: bool) -> DetectSummary:
    summary = DetectSummary(candidates=len(candidates))
    summary.auto_accepted = sum(1 for c in candidates if c.status == "accepted")
    summary.pending = sum(1 for c in candidates if c.status == "pending")
    summary.ignored = sum(1 for c in candidates if c.status == "ignored")
    if dry_run:
        for candidate in candidates:
            print(
                f"candidate comedian_id={candidate.comedian_id} episode_id={candidate.episode_id} "
                f"role={candidate.role_guess} status={candidate.status} confidence={candidate.confidence:.2f} "
                f"matched={candidate.matched_name!r} field={candidate.source_field}"
            )
        return summary

    with get_connection() as conn:
        summary = persist_candidates_with_conn(conn, candidates, dry_run=False)
        conn.commit()
    return summary


def persist_candidates_with_conn(
    conn: Any,
    candidates: list[EpisodeAppearanceCandidate],
    dry_run: bool,
) -> DetectSummary:
    summary = DetectSummary(candidates=len(candidates))
    summary.auto_accepted = sum(1 for c in candidates if c.status == "accepted")
    summary.pending = sum(1 for c in candidates if c.status == "pending")
    summary.ignored = sum(1 for c in candidates if c.status == "ignored")
    if dry_run:
        return summary

    review_rows: list[tuple[Any, ...]] = []
    appearance_rows: list[tuple[Any, ...]] = []
    for candidate in candidates:
        evidence_json = json.dumps(candidate.evidence, sort_keys=True)
        review_rows.append(
            (
                candidate.comedian_id,
                candidate.episode_id,
                candidate.source,
                candidate.source_episode_id,
                candidate.status,
                candidate.role_guess,
                candidate.confidence,
                evidence_json,
            )
        )
        if candidate.status == "accepted":
            appearance_rows.append(
                (
                    candidate.comedian_id,
                    candidate.episode_id,
                    candidate.source,
                    candidate.role_guess,
                    "accepted",
                    candidate.confidence,
                    "auto:detect_podcast_episode_appearances",
                    evidence_json,
                )
            )

    with conn.cursor() as cur:
        if review_rows:
            execute_values(
                cur,
                _UPSERT_REVIEW_BULK_SQL,
                review_rows,
                template="(%s, %s, %s, %s, %s, %s, %s, %s::jsonb)",
                page_size=1000,
            )
        if appearance_rows:
            execute_values(
                cur,
                _UPSERT_APPEARANCE_BULK_SQL,
                appearance_rows,
                template="(%s, %s, %s, %s, %s, %s, %s, NOW(), %s::jsonb)",
                page_size=1000,
            )
    summary.written = len(candidates)
    return summary


def detect_podcast_episode_appearances(
    *,
    dry_run: bool,
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]],
    episode_ids: Optional[list[int]],
    episode_limit: Optional[int],
    comedian_limit: Optional[int],
    include_aliases: bool,
    auto_accept: bool,
) -> DetectSummary:
    comedians = load_match_comedians(
        comedian_ids=comedian_ids,
        comedian_names=comedian_names,
        limit=comedian_limit,
    )
    episodes = load_episode_inputs(episode_ids=episode_ids, limit=episode_limit)
    candidates = detect_episode_candidates(
        comedians,
        episodes,
        include_aliases=include_aliases,
        auto_accept=auto_accept,
    )
    return persist_candidates(candidates, dry_run=dry_run)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect comedian appearances in podcast episodes")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--comedian-id", dest="comedian_ids", action="append", type=int, default=None)
    parser.add_argument("--comedian-name", dest="comedian_names", action="append", default=None)
    parser.add_argument("--episode-id", dest="episode_ids", action="append", type=int, default=None)
    parser.add_argument("--episode-limit", type=int, default=None)
    parser.add_argument("--limit", dest="episode_limit", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--comedian-limit", type=int, default=None)
    parser.add_argument("--no-aliases", action="store_true")
    parser.add_argument(
        "--review-only",
        action="store_true",
        help="Keep all detections pending in episode_appearance_reviews; do not auto-materialize appearances",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = detect_podcast_episode_appearances(
        dry_run=args.dry_run,
        comedian_ids=args.comedian_ids,
        comedian_names=args.comedian_names,
        episode_ids=args.episode_ids,
        episode_limit=args.episode_limit,
        comedian_limit=args.comedian_limit,
        include_aliases=not args.no_aliases,
        auto_accept=not args.review_only,
    )
    print(
        {
            "candidates": summary.candidates,
            "auto_accepted": summary.auto_accepted,
            "pending": summary.pending,
            "ignored": summary.ignored,
            "written": summary.written,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
