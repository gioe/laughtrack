import type { Prisma } from "@prisma/client";
import { PARENT_COMEDIAN_LINEUP_SELECT } from "@/lib/data/comedian/parentComedianSelect";

// Truly-common fields for the outer lineup-item comedian across the six lineup
// fetchers — show search/detail/home (findShowsWithCount, findShowById,
// findShowsForHome) and the comedian-detail trio (findUpcomingRunsForComedian,
// findPastShowsForComedian, findCoBilledComediansForComedian). Unlike PARENT_COMEDIAN_LINEUP_SELECT, this
// shape is not visibility-gate-critical — hidden comedians are filtered at the
// WHERE level via `comedian: { visible: true }`. Counted lineup callers compose
// buildLineupItemComedianSelect below; no-count callers can still spread this
// base and add parentComedian or path-specific fields.
export const LINEUP_COMEDIAN_SELECT = {
    id: true,
    uuid: true,
    name: true,
    hasImage: true,
    popularity: true,
    taggedComedians: {
        select: { tag: true },
    },
    imageAssets: {
        where: { isActive: true },
        orderBy: { publishedAt: "desc" },
        take: 1,
        select: { avatarPath: true, heroPath: true, isActive: true },
    },
} satisfies Prisma.ComedianSelect;

// Build the comedian select nested under each lineup item. The single source
// of the _count shape at both depths: no countWhere yields the all-time
// lineupItems count (search/home/upcoming/co-bill); a countWhere filters it
// (show detail passes an upcoming-only date bound).
export function buildLineupItemComedianSelect(
    countWhere?: Prisma.LineupItemWhereInput,
) {
    const lineupItemsCount = {
        select: {
            lineupItems: countWhere ? { where: countWhere } : true,
        },
    };
    return {
        ...LINEUP_COMEDIAN_SELECT,
        _count: lineupItemsCount,
        parentComedian: {
            select: {
                ...PARENT_COMEDIAN_LINEUP_SELECT,
                _count: lineupItemsCount,
            },
        },
    } satisfies Prisma.ComedianSelect;
}
