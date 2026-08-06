"""Shared comedian eligibility checks for podcast attribution writes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_LOAD_COMEDIAN_SQL = """
    SELECT id, name, parent_comedian_id, visible
    FROM comedians
    WHERE id = %s
"""

_COMEDIAN_DENIED_SQL = """
    SELECT EXISTS (
        SELECT 1
        FROM comedian_deny_list
        WHERE LOWER(BTRIM(REGEXP_REPLACE(REPLACE(name, CHR(160), ' '), '[[:space:]]+', ' ', 'g'))) =
              LOWER(BTRIM(REGEXP_REPLACE(REPLACE(%s, CHR(160), ' '), '[[:space:]]+', ' ', 'g')))
    )
"""


@dataclass(frozen=True)
class CanonicalComedianResolution:
    comedian_id: int
    comedian_name: str
    requested_comedian_id: int
    alias_path: list[int]


def resolve_canonical_comedian(
    conn: Any, requested_comedian_id: int
) -> tuple[CanonicalComedianResolution | None, str | None]:
    """Resolve an attribution target to an eligible canonical comedian.

    Alias chains are followed defensively even though the normal data model uses
    one level. A relationship may only be accepted for a visible root comedian
    whose normalized name is absent from ``comedian_deny_list``.
    """

    seen: set[int] = set()
    alias_path: list[int] = []
    comedian_id = requested_comedian_id

    with conn.cursor() as cur:
        while True:
            if comedian_id in seen:
                return None, "comedian alias cycle"
            seen.add(comedian_id)
            alias_path.append(comedian_id)

            cur.execute(_LOAD_COMEDIAN_SQL, (comedian_id,))
            row = cur.fetchone()
            if row is None:
                return None, "comedian or canonical parent not found"

            row_id, name, parent_comedian_id, visible = row
            if parent_comedian_id is not None:
                comedian_id = int(parent_comedian_id)
                continue
            if not visible:
                return None, "canonical comedian is hidden"

            cur.execute(_COMEDIAN_DENIED_SQL, (str(name or ""),))
            denied_row = cur.fetchone()
            if denied_row and bool(denied_row[0]):
                return None, "canonical comedian is deny-listed"

            return (
                CanonicalComedianResolution(
                    comedian_id=int(row_id),
                    comedian_name=str(name or ""),
                    requested_comedian_id=requested_comedian_id,
                    alias_path=alias_path,
                ),
                None,
            )


def preserve_canonical_comedian_provenance(
    evidence: dict[str, Any], resolution: CanonicalComedianResolution
) -> dict[str, Any]:
    """Copy evidence and record an alias-to-canonical attribution decision."""

    preserved = dict(evidence)
    if resolution.requested_comedian_id != resolution.comedian_id:
        preserved["canonical_comedian_resolution"] = {
            "requested_comedian_id": resolution.requested_comedian_id,
            "canonical_comedian_id": resolution.comedian_id,
            "alias_path": resolution.alias_path,
        }
    return preserved
