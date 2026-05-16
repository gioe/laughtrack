#!/usr/bin/env python3
"""Populate stable podcast slugs for TASK-2259.

Usage:
    cd apps/scraper && make run-script SCRIPT=scripts/core/populate_podcast_slugs.py ARGS='--dry-run'
    cd apps/scraper && make run-script SCRIPT=scripts/core/populate_podcast_slugs.py
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

_root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from dotenv import load_dotenv

load_dotenv(_root / ".env")

from laughtrack.infrastructure.database.connection import get_transaction

_METADATA_KEY = "task_2259_slug"


@dataclass(frozen=True)
class PodcastSlugCandidate:
    id: int
    title: str
    source_podcast_id: str
    current_slug: str | None


def build_podcast_slug(title: str, source_podcast_id: str) -> str:
    raw = f"{title or 'podcast'} {source_podcast_id or ''}"
    normalized = unicodedata.normalize("NFKD", html.unescape(raw))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug or "podcast"


def _dedupe_slugs(candidates: list[PodcastSlugCandidate]) -> dict[int, str]:
    seen: dict[str, int] = {}
    result: dict[int, str] = {}
    for candidate in sorted(candidates, key=lambda row: row.id):
        base = build_podcast_slug(candidate.title, candidate.source_podcast_id)
        count = seen.get(base, 0) + 1
        seen[base] = count
        result[candidate.id] = base if count == 1 else f"{base}-{count}"
    return result


def _load_candidates(conn) -> list[PodcastSlugCandidate]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, source_podcast_id, slug
            FROM podcasts
            WHERE slug IS NULL OR BTRIM(slug) = ''
            ORDER BY id
            """,
        )
        return [
            PodcastSlugCandidate(
                id=int(row[0]),
                title=str(row[1] or ""),
                source_podcast_id=str(row[2] or ""),
                current_slug=row[3],
            )
            for row in cur.fetchall()
        ]


def populate_podcast_slugs(dry_run: bool) -> int:
    with get_transaction() as conn:
        candidates = _load_candidates(conn)
        planned_slugs = _dedupe_slugs(candidates)

        print("=== BEFORE ===")
        print(f"podcasts missing slug: {len(candidates)}")
        for candidate in candidates[:10]:
            print(
                f"  [{candidate.id}] title={candidate.title!r} "
                f"source_podcast_id={candidate.source_podcast_id!r} "
                f"slug={candidate.current_slug!r}"
            )
        if len(candidates) > 10:
            print(f"  ... and {len(candidates) - 10} more")

        if dry_run:
            print("\n--dry-run: planning writes, no DB changes...")
            for candidate in candidates[:10]:
                print(f"  [{candidate.id}] -> {planned_slugs[candidate.id]}")
            print(f"\n--dry-run: {len(planned_slugs)} writes planned (none applied).")
            return len(planned_slugs)

        with conn.cursor() as cur:
            for candidate in candidates:
                cur.execute(
                    """
                    UPDATE podcasts
                    SET
                        slug = %s,
                        evidence = COALESCE(evidence, '{}'::jsonb) || %s::jsonb,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        planned_slugs[candidate.id],
                        (
                            '{"'
                            + _METADATA_KEY
                            + '":{"source":"populate_podcast_slugs.py"}}'
                        ),
                        candidate.id,
                    ),
                )

        print(f"\n=== AFTER ({len(planned_slugs)} writes pending commit on transaction exit) ===")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM podcasts WHERE slug IS NULL OR BTRIM(slug) = ''")
            remaining = int(cur.fetchone()[0])
        print(f"podcasts missing slug: {remaining}")
        return len(planned_slugs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    populate_podcast_slugs(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
