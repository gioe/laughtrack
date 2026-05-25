import { db } from "@/lib/db";
import {
    buildComedianImageAssetUrl,
    buildComedianImageUrls,
} from "@/lib/data/comedian/imageAssets";

type DenyListRow = {
    name: string;
    reason: string;
    added_by: string;
    deleted_at: Date | string;
};

export type AdminComedianListItem = {
    id: number;
    uuid: string;
    createdAt: string;
    name: string;
    website: string | null;
    websiteScrapingUrl: string | null;
    hasImage: boolean;
    activeImageAsset: {
        id: number;
        sourceImageUrl: string;
        avatarPath: string | null;
        heroPath: string | null;
        avatarUrl: string | null;
        heroUrl: string | null;
        mimeType: string | null;
        width: number | null;
        height: number | null;
    } | null;
    legacyImageUrl: string;
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
    podcastCandidateReviews: Array<{
        id: number;
        source: string;
        sourcePodcastId: string;
        candidateStatus: string;
        associationType: string | null;
        confidence: number;
        createdAt: string;
        updatedAt: string;
        podcast: {
            id: number;
            slug: string;
            title: string;
            authorName: string | null;
            feedUrl: string | null;
            websiteUrl: string | null;
            denyListEntry: {
                id: number;
                reason: string | null;
                deniedAt: string;
                deniedBy: string | null;
            } | null;
        } | null;
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
    return name.replace(/\s+/g, " ").trim().toLowerCase();
}

export async function listAdminComedians(): Promise<AdminComedianListResult> {
    const [comedians, denyListRows] = await Promise.all([
        db.comedian.findMany({
            select: {
                id: true,
                uuid: true,
                createdAt: true,
                name: true,
                website: true,
                websiteScrapingUrl: true,
                hasImage: true,
                imageAssets: {
                    where: { isActive: true },
                    select: {
                        id: true,
                        sourceImageUrl: true,
                        avatarPath: true,
                        heroPath: true,
                        mimeType: true,
                        width: true,
                        height: true,
                    },
                    orderBy: [{ publishedAt: "desc" }, { id: "desc" }],
                    take: 1,
                },
                popularity: true,
                totalShows: true,
                parentComedian: {
                    select: {
                        id: true,
                        name: true,
                    },
                },
                comedianPodcasts: {
                    where: { reviewStatus: "accepted" },
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
                podcastCandidateReviews: {
                    where: { candidateStatus: "pending" },
                    select: {
                        id: true,
                        source: true,
                        sourcePodcastId: true,
                        candidateStatus: true,
                        associationType: true,
                        confidence: true,
                        createdAt: true,
                        updatedAt: true,
                        podcast: {
                            select: {
                                id: true,
                                slug: true,
                                title: true,
                                authorName: true,
                                feedUrl: true,
                                websiteUrl: true,
                                denyListEntries: {
                                    where: { restoredAt: null },
                                    select: {
                                        id: true,
                                        reason: true,
                                        deniedAt: true,
                                        deniedBy: true,
                                    },
                                    take: 1,
                                },
                            },
                        },
                    },
                    orderBy: [
                        { candidateStatus: "asc" },
                        { confidence: "desc" },
                        { updatedAt: "desc" },
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
            const activeImageAsset = comedian.imageAssets[0] ?? null;
            const imageUrls = buildComedianImageUrls({
                name: comedian.name,
                hasImage: comedian.hasImage,
                activeAsset: null,
            });
            return {
                id: comedian.id,
                uuid: comedian.uuid,
                createdAt: comedian.createdAt.toISOString(),
                name: comedian.name,
                website: comedian.website,
                websiteScrapingUrl: comedian.websiteScrapingUrl,
                hasImage: comedian.hasImage,
                activeImageAsset: activeImageAsset
                    ? {
                          ...activeImageAsset,
                          avatarUrl: activeImageAsset.avatarPath
                              ? buildComedianImageAssetUrl(
                                    activeImageAsset.avatarPath,
                                )
                              : null,
                          heroUrl: activeImageAsset.heroPath
                              ? buildComedianImageAssetUrl(
                                    activeImageAsset.heroPath,
                                )
                              : null,
                      }
                    : null,
                legacyImageUrl: imageUrls.imageUrl,
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
                podcastCandidateReviews: comedian.podcastCandidateReviews.map(
                    (review) => ({
                        id: review.id,
                        source: review.source,
                        sourcePodcastId: review.sourcePodcastId,
                        candidateStatus: review.candidateStatus,
                        associationType: review.associationType,
                        confidence: review.confidence,
                        createdAt: review.createdAt.toISOString(),
                        updatedAt: review.updatedAt.toISOString(),
                        podcast: review.podcast
                            ? {
                                  id: review.podcast.id,
                                  slug: review.podcast.slug,
                                  title: review.podcast.title,
                                  authorName: review.podcast.authorName,
                                  feedUrl: review.podcast.feedUrl,
                                  websiteUrl: review.podcast.websiteUrl,
                                  denyListEntry: review.podcast
                                      .denyListEntries?.[0]
                                      ? {
                                            id: review.podcast
                                                .denyListEntries[0].id,
                                            reason: review.podcast
                                                .denyListEntries[0].reason,
                                            deniedAt:
                                                review.podcast.denyListEntries[0].deniedAt.toISOString(),
                                            deniedBy:
                                                review.podcast
                                                    .denyListEntries[0]
                                                    .deniedBy,
                                        }
                                      : null,
                              }
                            : null,
                    }),
                ),
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
