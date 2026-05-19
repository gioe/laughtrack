import { db } from "@/lib/db";

type DenyListRow = {
    name: string;
    reason: string;
    added_by: string;
    deleted_at: Date | string;
};

export type AdminComedianListItem = {
    id: number;
    uuid: string;
    name: string;
    popularity: number;
    totalShows: number;
    parent: {
        id: number;
        name: string;
    } | null;
    childCount: number;
    isBlocked: boolean;
    blockReason: string | null;
    blockAddedBy: string | null;
    blockAddedAt: string | null;
    attributedPodcasts: Array<{
        id: number;
        slug: string;
        title: string;
        feedUrl: string | null;
        websiteUrl: string | null;
        associationType: string;
        source: string;
        reviewStatus: string;
        confidence: number;
    }>;
    latestTicketPurchase: {
        url: string;
        showId: number;
        showName: string | null;
        showDate: string;
        clubName: string;
    } | null;
};

export type AdminComedianListResult = {
    comedians: AdminComedianListItem[];
    denyListCount: number;
};

function serializeDate(value: Date | string | null | undefined) {
    if (!value) return null;
    return value instanceof Date
        ? value.toISOString()
        : new Date(value).toISOString();
}

function normalizeDenyListName(name: string) {
    return name.trim().toLowerCase();
}

export async function listAdminComedians(): Promise<AdminComedianListResult> {
    const [comedians, denyListRows] = await Promise.all([
        db.comedian.findMany({
            select: {
                id: true,
                uuid: true,
                name: true,
                popularity: true,
                totalShows: true,
                parentComedian: {
                    select: {
                        id: true,
                        name: true,
                    },
                },
                comedianPodcasts: {
                    select: {
                        associationType: true,
                        source: true,
                        reviewStatus: true,
                        confidence: true,
                        podcast: {
                            select: {
                                id: true,
                                slug: true,
                                title: true,
                                feedUrl: true,
                                websiteUrl: true,
                            },
                        },
                    },
                    orderBy: [
                        { reviewStatus: "asc" },
                        { confidence: "desc" },
                        { podcast: { title: "asc" } },
                    ],
                },
                lineupItems: {
                    where: {
                        show: {
                            tickets: {
                                some: {
                                    AND: [
                                        { purchaseUrl: { not: null } },
                                        { purchaseUrl: { not: "" } },
                                    ],
                                },
                            },
                        },
                    },
                    select: {
                        show: {
                            select: {
                                id: true,
                                name: true,
                                date: true,
                                club: {
                                    select: {
                                        name: true,
                                    },
                                },
                                tickets: {
                                    where: {
                                        AND: [
                                            { purchaseUrl: { not: null } },
                                            { purchaseUrl: { not: "" } },
                                        ],
                                    },
                                    select: {
                                        purchaseUrl: true,
                                    },
                                    orderBy: [
                                        { soldOut: "asc" },
                                        { id: "asc" },
                                    ],
                                    take: 1,
                                },
                            },
                        },
                    },
                    orderBy: [{ show: { date: "desc" } }],
                    take: 1,
                },
                _count: {
                    select: {
                        alternativeNames: true,
                    },
                },
            },
            orderBy: [{ name: "asc" }, { id: "asc" }],
        }),
        db.$queryRaw<DenyListRow[]>`
            SELECT name, reason, added_by, deleted_at
            FROM comedian_deny_list
        `,
    ]);

    const denyListByName = new Map(
        denyListRows.map((row) => [normalizeDenyListName(row.name), row]),
    );

    return {
        comedians: comedians.map((comedian) => {
            const denyListEntry = denyListByName.get(
                normalizeDenyListName(comedian.name),
            );
            const latestTicketShow = comedian.lineupItems[0]?.show ?? null;
            const latestTicketUrl =
                latestTicketShow?.tickets[0]?.purchaseUrl ?? null;
            return {
                id: comedian.id,
                uuid: comedian.uuid,
                name: comedian.name,
                popularity: comedian.popularity,
                totalShows: comedian.totalShows,
                parent: comedian.parentComedian,
                childCount: comedian._count.alternativeNames,
                isBlocked: Boolean(denyListEntry),
                blockReason: denyListEntry?.reason ?? null,
                blockAddedBy: denyListEntry?.added_by ?? null,
                blockAddedAt: serializeDate(denyListEntry?.deleted_at),
                attributedPodcasts: comedian.comedianPodcasts.map((link) => ({
                    id: link.podcast.id,
                    slug: link.podcast.slug,
                    title: link.podcast.title,
                    feedUrl: link.podcast.feedUrl,
                    websiteUrl: link.podcast.websiteUrl,
                    associationType: link.associationType,
                    source: link.source,
                    reviewStatus: link.reviewStatus,
                    confidence: link.confidence,
                })),
                latestTicketPurchase:
                    latestTicketShow && latestTicketUrl
                        ? {
                              url: latestTicketUrl,
                              showId: latestTicketShow.id,
                              showName: latestTicketShow.name,
                              showDate: latestTicketShow.date.toISOString(),
                              clubName: latestTicketShow.club.name,
                          }
                        : null,
            };
        }),
        denyListCount: denyListRows.length,
    };
}
