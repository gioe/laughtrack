import type { Prisma } from "@prisma/client";

export const PUBLIC_PODCAST_DENY_LIST_WHERE = {
    denyListEntries: {
        none: {
            restoredAt: null,
        },
    },
} satisfies Prisma.PodcastWhereInput;

export const ACCEPTED_PODCAST_HOST_WHERE = {
    reviewStatus: "accepted",
    associationType: "host",
} satisfies Prisma.ComedianPodcastWhereInput;

export const ACCEPTED_PODCAST_COHOST_WHERE = {
    reviewStatus: "accepted",
    associationType: "cohost",
} satisfies Prisma.ComedianPodcastWhereInput;

export const PUBLIC_PODCAST_HOST_ROLE_WHERE = {
    ...PUBLIC_PODCAST_DENY_LIST_WHERE,
    OR: [
        { comedianPodcasts: { some: ACCEPTED_PODCAST_HOST_WHERE } },
        {
            AND: [
                { comedianPodcasts: { none: ACCEPTED_PODCAST_HOST_WHERE } },
                { comedianPodcasts: { some: ACCEPTED_PODCAST_COHOST_WHERE } },
            ],
        },
    ],
} satisfies Prisma.PodcastWhereInput;

export const PUBLIC_PODCAST_ACCEPTED_ATTRIBUTION_WHERE =
    PUBLIC_PODCAST_HOST_ROLE_WHERE;
