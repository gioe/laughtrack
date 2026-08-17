import type { ShowDTO } from "@/objects/class/show/show.interface";
import { inferHeadliner } from "@/util/show/showHeroImage";

export const HOME_SHOW_RAIL_LIMIT = 8;
export const HOME_SHOW_RAIL_CANDIDATE_LIMIT = 50;

interface ShowRailSelectionConstraints {
    maxPerTimestamp?: number;
}

function compareShowsByTime(a: ShowDTO, b: ShowDTO): number {
    const timeDifference = a.date.getTime() - b.date.getTime();
    return timeDifference !== 0 ? timeDifference : a.id - b.id;
}

/**
 * Prefer one show per inferred headliner, backfill when inventory is thin,
 * then restore chronological display order for the selected rail.
 */
export function selectDiverseShowsByTime(
    shows: readonly ShowDTO[],
    limit: number = HOME_SHOW_RAIL_LIMIT,
    constraints: ShowRailSelectionConstraints = {},
): ShowDTO[] {
    return selectDiverseShowItemsByTime(
        shows,
        (show) => show,
        limit,
        constraints,
    );
}

export function selectDiverseShowItemsByTime<T>(
    items: readonly T[],
    getShow: (item: T) => ShowDTO,
    limit: number = HOME_SHOW_RAIL_LIMIT,
    constraints: ShowRailSelectionConstraints = {},
): T[] {
    if (limit <= 0) return [];

    const maxPerTimestamp = Math.max(
        1,
        Math.trunc(constraints.maxPerTimestamp ?? Number.POSITIVE_INFINITY),
    );
    const chronologicalItems = [...items].sort((a, b) =>
        compareShowsByTime(getShow(a), getShow(b)),
    );
    const diverseItems: T[] = [];
    const repeatedHeadlinerItems: T[] = [];
    const seenHeadlinerIds = new Set<number>();
    const selectedTimestampCounts = new Map<number, number>();

    const hasTimestampCapacity = (item: T): boolean => {
        if (!Number.isFinite(maxPerTimestamp)) return true;
        const timestamp = getShow(item).date.getTime();
        return (selectedTimestampCounts.get(timestamp) ?? 0) < maxPerTimestamp;
    };
    const markTimestampSelected = (item: T): void => {
        if (!Number.isFinite(maxPerTimestamp)) return;
        const timestamp = getShow(item).date.getTime();
        selectedTimestampCounts.set(
            timestamp,
            (selectedTimestampCounts.get(timestamp) ?? 0) + 1,
        );
    };

    for (const item of chronologicalItems) {
        const show = getShow(item);
        const headlinerId = inferHeadliner(show)?.id;

        if (headlinerId === undefined || !seenHeadlinerIds.has(headlinerId)) {
            if (!hasTimestampCapacity(item)) continue;
            diverseItems.push(item);
            markTimestampSelected(item);
            if (headlinerId !== undefined) seenHeadlinerIds.add(headlinerId);
        } else {
            repeatedHeadlinerItems.push(item);
        }
    }

    const selectedItems = diverseItems.slice(0, limit);
    for (const item of repeatedHeadlinerItems) {
        if (selectedItems.length === limit) break;
        if (!hasTimestampCapacity(item)) continue;
        selectedItems.push(item);
        markTimestampSelected(item);
    }

    return selectedItems.sort((a, b) =>
        compareShowsByTime(getShow(a), getShow(b)),
    );
}
