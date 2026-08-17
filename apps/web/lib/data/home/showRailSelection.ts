import type { ShowDTO } from "@/objects/class/show/show.interface";
import { inferHeadliner } from "@/util/show/showHeroImage";

export const HOME_SHOW_RAIL_LIMIT = 8;
export const HOME_SHOW_RAIL_CANDIDATE_LIMIT = 50;

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
): ShowDTO[] {
    return selectDiverseShowItemsByTime(shows, (show) => show, limit);
}

export function selectDiverseShowItemsByTime<T>(
    items: readonly T[],
    getShow: (item: T) => ShowDTO,
    limit: number = HOME_SHOW_RAIL_LIMIT,
): T[] {
    if (limit <= 0) return [];

    const chronologicalItems = [...items].sort((a, b) =>
        compareShowsByTime(getShow(a), getShow(b)),
    );
    const diverseItems: T[] = [];
    const repeatedHeadlinerItems: T[] = [];
    const seenHeadlinerIds = new Set<number>();

    for (const item of chronologicalItems) {
        const show = getShow(item);
        const headlinerId = inferHeadliner(show)?.id;

        if (headlinerId === undefined || !seenHeadlinerIds.has(headlinerId)) {
            diverseItems.push(item);
            if (headlinerId !== undefined) seenHeadlinerIds.add(headlinerId);
        } else {
            repeatedHeadlinerItems.push(item);
        }
    }

    const selectedItems = diverseItems
        .slice(0, limit)
        .concat(
            repeatedHeadlinerItems.slice(
                0,
                Math.max(0, limit - diverseItems.length),
            ),
        );

    return selectedItems.sort((a, b) =>
        compareShowsByTime(getShow(a), getShow(b)),
    );
}
