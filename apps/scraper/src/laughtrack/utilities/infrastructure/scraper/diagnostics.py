"""
Diagnostics utilities for scraper pipelines.

Provides reusable logging helpers to understand why certain items are
excluded before an enrichment step (e.g., ticket APIs), without changing
scraper behavior.
"""

from typing import Any, Callable, Iterable, List, Optional, Sequence

from laughtrack.foundation.infrastructure.logger.logger import Logger


def log_filter_breakdown(
    items: Sequence[Any],
    logger_context: Optional[dict],
    *,
    id_getter: Callable[[Any], Optional[str]],
    accept_predicate: Callable[[Any], bool],
    label: str = "enrichment",
    name_getter: Optional[Callable[[Any], str]] = None,
    date_getter: Optional[Callable[[Any], str]] = None,
    sample_size: int = 5,
) -> List[str]:
    """
    Log a standardized breakdown of which items pass a filter and return deduped IDs.

    Use this before calling any batch enrichment API to observe why some items are
    excluded (missing id or failing the acceptance predicate).

    Args:
        items: Sequence of item-like objects (e.g., events)
        logger_context: Context for Logger (club, scraper, etc.)
        id_getter: Function to extract the id (returns str or None)
        accept_predicate: Function that returns True if the item should be enriched
        label: Short label for log lines (e.g., "Tessera enrichment")
        name_getter: Optional function to extract display name for samples
        date_getter: Optional function to extract display date for samples
        sample_size: Number of sample items to include in debug logs

    Returns:
        List of deduplicated IDs for items that passed the filter
    """

    total = len(items)

    def safe_list(it: Iterable[Any]) -> List[Any]:
        return list(it) if not isinstance(it, list) else it

    missing_id = safe_list(x for x in items if not id_getter(x))
    excluded = safe_list(x for x in items if id_getter(x) and not accept_predicate(x))
    candidates = safe_list(x for x in items if id_getter(x) and accept_predicate(x))

    ids = [id_getter(x) for x in candidates]
    unique_ids = len({i for i in ids if i})
    duplicate_ids = len(ids) - unique_ids

    with_id = total - len(missing_id)
    Logger.info(
        (
            f"{label} filter: total={total}, with_id={with_id}, "
            f"missing_id={len(missing_id)}, excluded={len(excluded)}, "
            f"candidates={len(candidates)}, unique_ids={unique_ids}, duplicates={duplicate_ids}"
        ),
        logger_context,
    )

    def render_name(x: Any) -> str:
        try:
            return name_getter(x) if name_getter else "n/a"
        except Exception:
            return "n/a"

    def render_date(x: Any) -> str:
        try:
            return date_getter(x) if date_getter else "n/a"
        except Exception:
            return "n/a"

    if missing_id:
        sample = ", ".join(
            [f"(name={render_name(x)}, date={render_date(x)})" for x in missing_id[:sample_size]]
        )
        Logger.debug(f"Sample missing_id items: {sample}", logger_context)

    if excluded:
        sample = ", ".join(
            [f"(id={id_getter(x)}, name={render_name(x)})" for x in excluded[:sample_size]]
        )
        Logger.debug(f"Sample excluded items: {sample}", logger_context)

    # Return deduped list of IDs to fetch
    return [i for i in {id_getter(x) for x in candidates} if i]
