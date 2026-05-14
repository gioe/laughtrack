#!/usr/bin/env python3
"""Detect comedian appearances in canonical podcast episodes."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
for _path in (_root / "src", _root):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from laughtrack.adapters.db import get_connection

_SOURCE = "podcast_index"
_AUTO_ACCEPT_CONFIDENCE = 0.9

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
        pe.title,
        pe.description,
        pe.episode_url,
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
    GROUP BY pe.id, pe.podcast_id, pe.source, pe.source_episode_id, p.title,
        pe.title, pe.description, pe.episode_url
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
    title: str
    description: str
    episode_url: str
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
    written: int = 0


def normalize_match_text(value: str) -> str:
    unescaped = html.unescape(value or "")
    normalized = unicodedata.normalize("NFKD", unescaped)
    normalized = normalized.replace("\u2019", "'").replace("\u2018", "'")
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-")
    normalized = re.sub(r"(?i)\b([a-z0-9]+)'s\b", r"\1", normalized)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip().lower()


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


def build_match_terms(comedian: MatchComedian) -> list[MatchTerm]:
    terms: list[MatchTerm] = []
    seen: set[str] = set()
    for raw in [comedian.name, *comedian.aliases]:
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


def detect_episode_candidates(
    comedians: list[MatchComedian],
    episodes: list[PodcastEpisodeCandidateInput],
) -> list[EpisodeAppearanceCandidate]:
    candidates: list[EpisodeAppearanceCandidate] = []
    for episode in episodes:
        for comedian in comedians:
            best: Optional[EpisodeAppearanceCandidate] = None
            for term in build_match_terms(comedian):
                match = _best_field_match(term, episode)
                if match is None:
                    continue
                source_field, evidence_text = match
                role = _guess_role(
                    comedian=comedian,
                    episode=episode,
                    source_field=source_field,
                    evidence_text=evidence_text,
                )
                confidence = _confidence(source_field, role, term)
                status = "accepted" if role == "guest" and confidence >= _AUTO_ACCEPT_CONFIDENCE else "pending"
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
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params) if params else None)
            return [MatchComedian(int(row[0]), str(row[1]), list(row[2] or [])) for row in cur.fetchall()]


def load_episode_inputs(
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
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return [
                PodcastEpisodeCandidateInput(
                    episode_id=int(row[0]),
                    podcast_id=int(row[1]),
                    source=str(row[2]),
                    source_episode_id=str(row[3]),
                    podcast_title=str(row[4] or ""),
                    title=str(row[5] or ""),
                    description=str(row[6] or ""),
                    episode_url=str(row[7] or ""),
                    host_comedian_ids=[int(v) for v in (row[8] or [])],
                    host_association_types=[str(v) for v in (row[9] or [])],
                )
                for row in cur.fetchall()
            ]


def persist_candidates(candidates: list[EpisodeAppearanceCandidate], dry_run: bool) -> DetectSummary:
    summary = DetectSummary(candidates=len(candidates))
    summary.auto_accepted = sum(1 for c in candidates if c.status == "accepted")
    summary.pending = sum(1 for c in candidates if c.status == "pending")
    if dry_run:
        for candidate in candidates:
            print(
                f"candidate comedian_id={candidate.comedian_id} episode_id={candidate.episode_id} "
                f"role={candidate.role_guess} status={candidate.status} confidence={candidate.confidence:.2f} "
                f"matched={candidate.matched_name!r} field={candidate.source_field}"
            )
        return summary

    with get_connection() as conn:
        with conn.cursor() as cur:
            for candidate in candidates:
                evidence_json = json.dumps(candidate.evidence, sort_keys=True)
                cur.execute(
                    _UPSERT_REVIEW_SQL,
                    (
                        candidate.comedian_id,
                        candidate.episode_id,
                        candidate.source,
                        candidate.source_episode_id,
                        candidate.status,
                        candidate.role_guess,
                        candidate.confidence,
                        evidence_json,
                    ),
                )
                if candidate.status == "accepted":
                    cur.execute(
                        _UPSERT_APPEARANCE_SQL,
                        (
                            candidate.comedian_id,
                            candidate.episode_id,
                            candidate.source,
                            candidate.role_guess,
                            "accepted",
                            candidate.confidence,
                            "auto:detect_podcast_episode_appearances",
                            evidence_json,
                        ),
                    )
        conn.commit()
    summary.written = len(candidates)
    return summary


def detect_podcast_episode_appearances(
    *,
    dry_run: bool,
    comedian_ids: Optional[list[int]],
    comedian_names: Optional[list[str]],
    episode_ids: Optional[list[int]],
    limit: Optional[int],
) -> DetectSummary:
    comedians = load_match_comedians(comedian_ids=comedian_ids, comedian_names=comedian_names)
    episodes = load_episode_inputs(episode_ids=episode_ids, limit=limit)
    candidates = detect_episode_candidates(comedians, episodes)
    return persist_candidates(candidates, dry_run=dry_run)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect comedian appearances in podcast episodes")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--comedian-id", dest="comedian_ids", action="append", type=int, default=None)
    parser.add_argument("--comedian-name", dest="comedian_names", action="append", default=None)
    parser.add_argument("--episode-id", dest="episode_ids", action="append", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = detect_podcast_episode_appearances(
        dry_run=args.dry_run,
        comedian_ids=args.comedian_ids,
        comedian_names=args.comedian_names,
        episode_ids=args.episode_ids,
        limit=args.limit,
    )
    print(
        {
            "candidates": summary.candidates,
            "auto_accepted": summary.auto_accepted,
            "pending": summary.pending,
            "written": summary.written,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
