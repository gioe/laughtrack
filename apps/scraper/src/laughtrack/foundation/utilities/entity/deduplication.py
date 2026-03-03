"""Generic deduplication helpers for database entities.

This module provides reusable functions to deduplicate arbitrary sequences
of items using a caller-provided key function. It deliberately contains no
logging so that domain layers can decide how and what to log.
"""

from typing import Any, Callable, Dict, Hashable, List, Mapping, MutableMapping, Sequence, Tuple, TypeVar

T = TypeVar("T")
Detail = Dict[str, Any]
Key = Tuple[Hashable, ...]


def deduplicate_entities_with_details(
    entities: Sequence[T],
    key_func: Callable[[T], Key],
    map_detail: Callable[[T], Detail],
) -> Tuple[List[T], Dict[Key, Dict[str, Any]]]:
    """Deduplicate a sequence and capture kept/dropped detail per key.

    - Keeps the first occurrence for each unique key as defined by key_func.
    - Returns the deduplicated list and a mapping of key -> { kept, dropped } where
      kept is the mapped detail of the first occurrence and dropped is a list of
      mapped details for subsequent duplicates.

    This function is generic and performs no logging.
    """
    if not entities:
        return [], {}

    unique_index: Dict[Key, int] = {}
    deduped: List[T] = []
    details: Dict[Key, Dict[str, Any]] = {}

    for item in entities:
        key = key_func(item)
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

    return deduped, details
