"""Generic validation & deduplication helpers for database entities."""

from typing import Any, Callable, Dict, Hashable, List, Sequence, Tuple, TypeVar

from laughtrack.foundation.protocols.database_entity import DatabaseEntity
from laughtrack.foundation.infrastructure.logger.logger import Logger

T = TypeVar("T", bound=DatabaseEntity)
Detail = Dict[str, Any]
Key = Tuple[Hashable, ...]


def detect_duplicate_keys(entities: Sequence[DatabaseEntity]) -> Dict[Tuple, int]:
    """Detect duplicate unique keys for any DatabaseEntity sequence.

    Returns a mapping of key -> count for keys that appear more than once.
    """
    counts: Dict[Tuple, int] = {}
    for entity in entities:
        try:
            key = entity.to_unique_key()
        except Exception:
            # Skip entities that cannot produce a key
            continue
        counts[key] = counts.get(key, 0) + 1
    return {k: c for k, c in counts.items() if c > 1}


def summarize_duplicates(dups: Dict[Tuple, int], limit: int = 5) -> str:
    """Create a concise summary string of duplicate keys.

    Example: "(k1) x2, (k2) x3 (+1 more)"
    """
    if not dups:
        return ""
    items = list(dups.items())
    sample = items[:limit]
    sample_str = ", ".join([f"({k}) x{c}" for k, c in sample])
    more = "" if len(items) <= limit else f" (+{len(items) - limit} more)"
    return sample_str + more


def deduplicate_entities_with_details(
    entities: Sequence[T],
    map_detail: Callable[[T], Detail],
) -> Tuple[List[T], Dict[Key, Dict[str, Any]]]:
    """Deduplicate a sequence and capture kept/dropped detail per key.

    - Keeps the first occurrence for each unique key as defined by key_func.
    - Returns the deduplicated list and a mapping of key -> { kept, dropped } where
      kept is the mapped detail of the first occurrence and dropped is a list of
      mapped details for subsequent duplicates.

    This function emits a concise summary log when duplicates are found.
    """
    if not entities:
        return [], {}

    unique_index: Dict[Key, int] = {}
    deduped: List[T] = []
    details: Dict[Key, Dict[str, Any]] = {}

    for item in entities:
        try:
            key = item.to_unique_key()
        except Exception:
            # Skip items that cannot produce a key
            continue
        if key not in unique_index:
            unique_index[key] = len(deduped)
            deduped.append(item)
        else:
            kept_item = deduped[unique_index[key]]
            if key not in details:
                details[key] = {
                    "kept": map_detail(kept_item),
                    "dropped": [],
                }
            details[key]["dropped"].append(map_detail(item))

    removed = len(entities) - len(deduped)
    if removed > 0:
        # Log the unique keys that had duplicates (sample to avoid noisy logs)
        keys = list(details.keys())
        sample = keys[:5]
        sample_str = ", ".join(str(k) for k in sample)
        more = f" (+{len(keys) - len(sample)} more)" if len(keys) > len(sample) else ""
        Logger.warning(
            f"Deduplicated {removed} duplicate entries across {len(details)} key(s): {sample_str}{more} (kept {len(deduped)})"
        )
    return deduped, details
