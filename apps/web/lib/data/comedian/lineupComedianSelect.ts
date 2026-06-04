import type { Prisma } from "@prisma/client";

// Truly-common fields for the outer lineup-item comedian across the six show
// fetchers (findShowsWithCount, findShowById, findShowsForHome,
// findUpcomingRunsForComedian, findPastShowsForComedian,
// findCoBilledComediansForComedian). Unlike PARENT_COMEDIAN_LINEUP_SELECT, this
// shape is not visibility-gate-critical — hidden comedians are filtered at the
// WHERE level via `comedian: { visible: true }`. Sites spread this and add
// their own _count flavor (lineupItems vs filtered-upcoming subset),
// parentComedian, and the conditional profileId-keyed favoriteComedians block.
export const LINEUP_COMEDIAN_SELECT = {
    id: true,
    uuid: true,
    name: true,
    hasImage: true,
    taggedComedians: {
        select: { tag: true },
    },
} satisfies Prisma.ComedianSelect;
