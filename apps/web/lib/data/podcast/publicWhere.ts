import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";

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
    comedian: { visible: true, parentComedianId: null },
} satisfies Prisma.ComedianPodcastWhereInput;

export const ACCEPTED_PODCAST_COHOST_WHERE = {
    reviewStatus: "accepted",
    associationType: "cohost",
    comedian: { visible: true, parentComedianId: null },
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

type DeniedHostPodcastRow = {
    podcast_id: number;
};

export function buildPublicPodcastAcceptedAttributionWhere(
    deniedHostPodcastIds: number[],
): Prisma.PodcastWhereInput {
    if (deniedHostPodcastIds.length === 0) {
        return PUBLIC_PODCAST_ACCEPTED_ATTRIBUTION_WHERE;
    }

    return {
        ...PUBLIC_PODCAST_ACCEPTED_ATTRIBUTION_WHERE,
        AND: [
            {
                id: {
                    notIn: deniedHostPodcastIds,
                },
            },
        ],
    };
}

/**
 * Resolve podcasts whose accepted host/cohost attribution points at a
 * deny-listed comedian. ComedianDenyList is keyed by normalized name rather
 * than a Prisma relation, so this lookup must cross the tables in SQL.
 *
 * Errors intentionally propagate: silently dropping this guard would
 * re-expose podcasts that an operator explicitly denied.
 */
export async function getPublicPodcastAcceptedAttributionWhere(): Promise<Prisma.PodcastWhereInput> {
    const rows = await db.$queryRaw<DeniedHostPodcastRow[]>(
        Prisma.sql`
            SELECT DISTINCT cp.podcast_id
            FROM comedian_podcasts cp
            JOIN comedians c ON c.id = cp.comedian_id
            JOIN comedian_deny_list dl
              ON lower(btrim(regexp_replace(replace(c.name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) =
                 lower(btrim(regexp_replace(replace(dl.name, chr(160), ' '), '[[:space:]]+', ' ', 'g')))
            WHERE cp.review_status = 'accepted'
              AND cp.association_type IN ('host', 'cohost')
        `,
    );

    return buildPublicPodcastAcceptedAttributionWhere(
        rows.map((row) => row.podcast_id),
    );
}
