import type { Prisma } from "@prisma/client";

export const PUBLIC_PODCAST_DENY_LIST_WHERE = {
    denyListEntries: {
        none: {
            restoredAt: null,
        },
    },
} satisfies Prisma.PodcastWhereInput;

export const PUBLIC_PODCAST_OWNER_OR_HOST_WHERE = {
    ...PUBLIC_PODCAST_DENY_LIST_WHERE,
    comedianPodcasts: {
        some: {
            reviewStatus: "accepted",
            associationType: { in: ["host", "owner"] },
        },
    },
} satisfies Prisma.PodcastWhereInput;

export const PUBLIC_PODCAST_ACCEPTED_OWNERSHIP_WHERE = {
    ...PUBLIC_PODCAST_DENY_LIST_WHERE,
    comedianPodcasts: {
        some: {
            reviewStatus: "accepted",
        },
    },
} satisfies Prisma.PodcastWhereInput;
