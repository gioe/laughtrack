import type { Prisma } from "@prisma/client";

// Visibility-gate-relevant fields for parentComedian in lineup selects.
// getEffectiveComedian (util/comedian/comedianUtil.ts) requires `visible` so a
// hidden parent's name/social handles do not leak through a visible alias;
// taggedComedians flows through containsAliasTag once the parent has been
// substituted in. Sites that need a `_count` shape (e.g. total lineupItems vs.
// a filtered upcoming subset) spread this base and add their own.
export const PARENT_COMEDIAN_LINEUP_SELECT = {
    id: true,
    uuid: true,
    name: true,
    hasImage: true,
    visible: true,
    taggedComedians: {
        select: { tag: true },
    },
} satisfies Prisma.ComedianSelect;
