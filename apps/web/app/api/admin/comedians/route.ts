import { writeAdminActionAudit } from "@/lib/admin/audit";
import type { AdminComedianListItem } from "@/lib/admin/comedianManagement";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import {
    buildComedianImageAssetUrl,
    buildComedianImageUrls,
} from "@/lib/data/comedian/imageAssets";
import {
    preserveCanonicalComedianProvenance,
    resolvePodcastAttributionComedian,
    type ResolvedPodcastAttributionComedian,
} from "@/lib/data/podcast/resolvePodcastAttributionComedian";
import type { Prisma } from "@prisma/client";
import { resolveInstagramFollowerCount } from "@/lib/instagram/instagramFollowerResolver";
import { recalculatePopularityForInstagramFollowers } from "@/lib/popularity/comedianPopularity";
import { resolveYouTubeChannelId } from "@/lib/youtube/youtubeChannelResolver";
import crypto from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

export const runtime = "nodejs";

type ComedianSnapshot = {
    id: number;
    uuid: string;
    createdAt: Date;
    name: string;
    website: string | null;
    websiteScrapingUrl: string | null;
    instagramAccount: string | null;
    instagramFollowers: number | null;
    instagramFollowersRefreshedAt: Date | null;
    tiktokAccount: string | null;
    tiktokFollowers: number | null;
    youtubeAccount: string | null;
    youtubeFollowers: number | null;
    youtubeChannelId: string | null;
    youtubeLiveFeedEnabled?: boolean;
    youtubeLiveNotificationsEnabled?: boolean;
    youtubeWebSubSubscriptions?: Array<{
        status: string;
        leaseExpiresAt: Date | null;
        lastSubscribeError: string | null;
    }>;
    youtubeWebSubEvents?: Array<{
        eventStatus: string;
        receivedAt: Date;
    }>;
    linktree: string | null;
    hasImage: boolean;
    imageAssets: Array<{
        id: number;
        sourceImageUrl: string;
        avatarPath: string | null;
        heroPath: string | null;
        avatarUrl?: string | null;
        heroUrl?: string | null;
        mimeType: string | null;
        width: number | null;
        height: number | null;
    }>;
    popularity: number;
    totalShows: number;
    visible: boolean;
    blockReason: string | null;
    blockAddedBy: string | null;
    blockAddedAt: Date | null;
    parentComedianId: number | null;
    parentComedian: { id: number; name: string } | null;
    comedianPodcasts: Array<{
        associationType: string;
        source: string;
        reviewStatus: string;
        confidence: number;
        podcast: {
            id: number;
            slug: string;
            title: string;
            feedUrl: string | null;
            websiteUrl: string | null;
        };
    }>;
    podcastCandidateReviews: Array<{
        id: number;
        source: string;
        sourcePodcastId: string;
        candidateStatus: string;
        associationType: string | null;
        confidence: number;
        createdAt: Date;
        updatedAt: Date;
        podcast: {
            id: number;
            slug: string;
            title: string;
            authorName: string | null;
            feedUrl: string | null;
            websiteUrl: string | null;
            denyListEntries: Array<{
                id: number;
                reason: string | null;
                deniedAt: Date;
                deniedBy: string | null;
            }>;
        } | null;
    }>;
    lineupItems: Array<{
        show: {
            id: number;
            name: string | null;
            date: Date;
            club: { name: string };
            tickets: Array<{ purchaseUrl: string | null }>;
        };
    }>;
    _count: { alternativeNames: number };
};

type DenyListRow = {
    name: string;
    reason: string;
    added_by: string;
    deleted_at: Date | string;
};

type ComedianAdminWriter = Pick<
    Prisma.TransactionClient,
    | "$queryRaw"
    | "comedian"
    | "comedianPodcast"
    | "podcast"
    | "podcastCandidateReview"
    | "podcastDenyList"
> &
    Parameters<typeof writeAdminActionAudit>[0];

const mutationSchema = z.discriminatedUnion("action", [
    z
        .object({
            action: z.literal("set-parent"),
            comedianId: z.number().int().positive(),
            parentComedianId: z.number().int().positive().nullable(),
            reason: z.string().trim().max(1000).optional(),
        })
        .strict(),
    z
        .object({
            action: z.literal("blocklist-add"),
            comedianId: z.number().int().positive(),
            reason: z.string().trim().min(1).max(1000),
        })
        .strict(),
    z
        .object({
            action: z.literal("blocklist-remove"),
            comedianId: z.number().int().positive(),
            reason: z.string().trim().max(1000).optional(),
        })
        .strict(),
    z
        .object({
            action: z.literal("podcast-review-accept-host"),
            comedianId: z.number().int().positive(),
            candidateReviewId: z.number().int().positive(),
            reason: z.string().trim().max(1000).optional(),
        })
        .strict(),
    z
        .object({
            action: z.literal("podcast-review-reject-host"),
            comedianId: z.number().int().positive(),
            candidateReviewId: z.number().int().positive(),
            reason: z.string().trim().max(1000).optional(),
        })
        .strict(),
    z
        .object({
            action: z.literal("podcast-review-block-podcast"),
            comedianId: z.number().int().positive(),
            candidateReviewId: z.number().int().positive(),
            reason: z.string().trim().max(1000).optional(),
        })
        .strict(),
]);

const putSchema = z
    .object({
        comedianId: z.number().int().positive(),
        name: z.string().trim().min(1).max(255),
        website: z.string().trim().url().max(2000).nullable().optional(),
        websiteScrapingUrl: z
            .string()
            .trim()
            .url()
            .max(2000)
            .nullable()
            .optional(),
        instagramAccount: z.string().trim().max(255).nullable().optional(),
        refreshInstagramFollowers: z.boolean().optional(),
        tiktokAccount: z.string().trim().max(255).nullable().optional(),
        youtubeAccount: z.string().trim().max(255).nullable().optional(),
        youtubeChannelId: z.string().trim().max(255).nullable().optional(),
        linktree: z.string().trim().url().max(2000).nullable().optional(),
        reason: z.string().trim().max(1000).optional(),
    })
    .strict();

const postSchema = z
    .object({
        name: z.string().trim().min(1).max(255),
    })
    .strict();

function serializeDate(value: Date | string | null | undefined) {
    if (!value) return null;
    return value instanceof Date
        ? value.toISOString()
        : new Date(value).toISOString();
}

function normalizeName(name: string) {
    return name.trim().replace(/\s+/g, " ");
}

function normalizeOptionalUrl(value: string | null | undefined) {
    const normalized = value?.trim() ?? "";
    return normalized || null;
}

function generateComedianUuid(name: string) {
    const cleanedName = Array.from(name)
        .filter(
            (char) =>
                /[0-9A-Za-z]/.test(char) ||
                char.toLowerCase() !== char.toUpperCase(),
        )
        .join("");
    return crypto
        .createHash("md5")
        .update(cleanedName.toLowerCase())
        .digest("hex");
}

function snapshotForAudit(comedian: ComedianSnapshot) {
    return {
        id: comedian.id,
        uuid: comedian.uuid,
        createdAt: comedian.createdAt.toISOString(),
        name: comedian.name,
        website: comedian.website,
        websiteScrapingUrl: comedian.websiteScrapingUrl,
        instagramAccount: comedian.instagramAccount,
        instagramFollowers: comedian.instagramFollowers,
        instagramFollowersRefreshedAt: serializeDate(
            comedian.instagramFollowersRefreshedAt,
        ),
        tiktokAccount: comedian.tiktokAccount,
        youtubeAccount: comedian.youtubeAccount,
        youtubeChannelId: comedian.youtubeChannelId,
        youtubeLiveFeedEnabled: comedian.youtubeLiveFeedEnabled,
        youtubeLiveNotificationsEnabled:
            comedian.youtubeLiveNotificationsEnabled,
        subscriptionStatus:
            comedian.youtubeWebSubSubscriptions?.[0]?.status ?? null,
        leaseExpiresAt: serializeDate(
            comedian.youtubeWebSubSubscriptions?.[0]?.leaseExpiresAt,
        ),
        lastSubscribeError:
            comedian.youtubeWebSubSubscriptions?.[0]?.lastSubscribeError ??
            null,
        recentEventStatus:
            comedian.youtubeWebSubEvents?.[0]?.eventStatus ?? null,
        recentEventAt: serializeDate(
            comedian.youtubeWebSubEvents?.[0]?.receivedAt,
        ),
        linktree: comedian.linktree,
        hasImage: Boolean(comedian.hasImage),
        activeImageAsset: comedian.imageAssets?.[0] ?? null,
        popularity: comedian.popularity,
        totalShows: comedian.totalShows,
        visible: comedian.visible,
        blockReason: comedian.blockReason,
        blockAddedBy: comedian.blockAddedBy,
        blockAddedAt: serializeDate(comedian.blockAddedAt),
        parentComedianId: comedian.parentComedianId,
        parent: comedian.parentComedian,
        childCount: comedian._count.alternativeNames,
    };
}

function serializeComedian(comedian: ComedianSnapshot): AdminComedianListItem {
    const activeImageAsset = comedian.imageAssets?.[0] ?? null;
    const nameImageUrl = buildComedianImageUrls({
        name: comedian.name,
        hasImage: Boolean(comedian.hasImage),
        activeAsset: null,
    }).imageUrl;

    return {
        id: comedian.id,
        uuid: comedian.uuid,
        createdAt: comedian.createdAt.toISOString(),
        name: comedian.name,
        website: comedian.website,
        websiteScrapingUrl: comedian.websiteScrapingUrl,
        instagramAccount: comedian.instagramAccount,
        instagramFollowers: comedian.instagramFollowers,
        instagramFollowersRefreshedAt: serializeDate(
            comedian.instagramFollowersRefreshedAt,
        ),
        tiktokAccount: comedian.tiktokAccount,
        youtubeAccount: comedian.youtubeAccount,
        youtubeChannelId: comedian.youtubeChannelId,
        linktree: comedian.linktree,
        hasImage: Boolean(comedian.hasImage),
        activeImageAsset: activeImageAsset
            ? {
                  ...activeImageAsset,
                  avatarUrl:
                      activeImageAsset.avatarUrl ??
                      (activeImageAsset.avatarPath
                          ? buildComedianImageAssetUrl(
                                activeImageAsset.avatarPath,
                            )
                          : null),
                  heroUrl:
                      activeImageAsset.heroUrl ??
                      (activeImageAsset.heroPath
                          ? buildComedianImageAssetUrl(
                                activeImageAsset.heroPath,
                            )
                          : null),
              }
            : null,
        nameImageUrl,
        popularity: comedian.popularity,
        totalShows: comedian.totalShows,
        parent: comedian.parentComedian,
        childCount: comedian._count.alternativeNames,
        isBlocked: !comedian.visible,
        blockReason: comedian.visible ? null : comedian.blockReason,
        blockAddedBy: comedian.visible ? null : comedian.blockAddedBy,
        blockAddedAt: comedian.visible
            ? null
            : serializeDate(comedian.blockAddedAt),
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
        podcastCandidateReviews: (comedian.podcastCandidateReviews ?? []).map(
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
                          denyListEntry: review.podcast.denyListEntries?.[0]
                              ? {
                                    id: review.podcast.denyListEntries[0].id,
                                    reason: review.podcast.denyListEntries[0]
                                        .reason,
                                    deniedAt:
                                        review.podcast.denyListEntries[0].deniedAt.toISOString(),
                                    deniedBy:
                                        review.podcast.denyListEntries[0]
                                            .deniedBy,
                                }
                              : null,
                      }
                    : null,
            }),
        ),
        latestTicketPurchase: (() => {
            const show = comedian.lineupItems[0]?.show ?? null;
            const url = show?.tickets[0]?.purchaseUrl ?? null;
            if (!show || !url) return null;
            return {
                url,
                showId: show.id,
                showName: show.name,
                showDate: show.date.toISOString(),
                clubName: show.club.name,
            };
        })(),
    };
}

const comedianSnapshotSelect = {
    id: true,
    uuid: true,
    createdAt: true,
    name: true,
    website: true,
    websiteScrapingUrl: true,
    instagramAccount: true,
    instagramFollowers: true,
    instagramFollowersRefreshedAt: true,
    tiktokAccount: true,
    tiktokFollowers: true,
    youtubeAccount: true,
    youtubeFollowers: true,
    youtubeChannelId: true,
    youtubeLiveFeedEnabled: true,
    youtubeLiveNotificationsEnabled: true,
    youtubeWebSubSubscriptions: {
        select: {
            status: true,
            leaseExpiresAt: true,
            lastSubscribeError: true,
        },
        orderBy: { updatedAt: "desc" },
        take: 1,
    },
    youtubeWebSubEvents: {
        select: { eventStatus: true, receivedAt: true },
        orderBy: { receivedAt: "desc" },
        take: 1,
    },
    linktree: true,
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
    visible: true,
    blockReason: true,
    blockAddedBy: true,
    blockAddedAt: true,
    parentComedianId: true,
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
                        orderBy: [{ soldOut: "asc" }, { id: "asc" }],
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
} as const satisfies Prisma.ComedianSelect;

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

async function findComedianSnapshot(
    tx: Pick<Prisma.TransactionClient, "comedian">,
    comedianId: number,
) {
    return tx.comedian.findUnique({
        where: { id: comedianId },
        select: comedianSnapshotSelect,
    });
}

async function findDenyListEntry(
    tx: Pick<Prisma.TransactionClient, "$queryRaw">,
    name: string,
) {
    const rows = await tx.$queryRaw<DenyListRow[]>`
        SELECT name, reason, added_by, deleted_at
        FROM comedian_deny_list
        WHERE lower(btrim(regexp_replace(replace(name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) =
              lower(btrim(regexp_replace(replace(${name}, chr(160), ' '), '[[:space:]]+', ' ', 'g')))
        LIMIT 1
    `;
    return rows[0] ?? null;
}

async function createsParentCycle(
    tx: Pick<Prisma.TransactionClient, "comedian">,
    comedianId: number,
    parentComedianId: number,
) {
    let nextParentId: number | null = parentComedianId;
    const seen = new Set<number>();

    while (nextParentId) {
        if (nextParentId === comedianId) return true;
        if (seen.has(nextParentId)) return true;
        seen.add(nextParentId);

        const parent: { parentComedianId: number | null } | null =
            await tx.comedian.findUnique({
                where: { id: nextParentId },
                select: { parentComedianId: true },
            });
        nextParentId = parent?.parentComedianId ?? null;
    }

    return false;
}

function revalidateComedianSurfaces(name: string) {
    revalidateTag("comedian-search-data");
    revalidateTag("comedian-detail-data");
    revalidateTag("comedian-metadata");
    revalidateTag(name);
}

export const PATCH = withRequestMetrics(async function PATCH(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = mutationSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    try {
        const result = await db.$transaction(
            async (tx: ComedianAdminWriter) => {
                const before = await findComedianSnapshot(
                    tx,
                    parsed.data.comedianId,
                );
                if (!before)
                    return { error: "Comedian not found", status: 404 };

                if (
                    parsed.data.action === "podcast-review-accept-host" ||
                    parsed.data.action === "podcast-review-reject-host" ||
                    parsed.data.action === "podcast-review-block-podcast"
                ) {
                    const review = await tx.podcastCandidateReview.findUnique({
                        where: { id: parsed.data.candidateReviewId },
                        select: {
                            id: true,
                            comedianId: true,
                            podcastId: true,
                            source: true,
                            sourcePodcastId: true,
                            candidateStatus: true,
                            associationType: true,
                            confidence: true,
                            evidence: true,
                            podcast: {
                                select: {
                                    id: true,
                                    slug: true,
                                    title: true,
                                    source: true,
                                    sourcePodcastId: true,
                                    feedUrl: true,
                                },
                            },
                        },
                    });
                    if (!review || review.comedianId !== before.id) {
                        return {
                            error: "Podcast review not found",
                            status: 404,
                        };
                    }
                    if (!review.podcastId || !review.podcast) {
                        return {
                            error: "Podcast review is missing a podcast",
                            status: 422,
                        };
                    }

                    const reviewedAt = new Date();
                    const reason =
                        "reason" in parsed.data
                            ? parsed.data.reason?.trim() || null
                            : null;
                    let attributionResolution: ResolvedPodcastAttributionComedian | null =
                        null;

                    if (parsed.data.action === "podcast-review-accept-host") {
                        const resolution =
                            await resolvePodcastAttributionComedian(
                                tx,
                                before.id,
                            );
                        if (!resolution.ok) {
                            return {
                                error: "Comedian is not eligible for podcast attribution",
                                status: 422,
                                reason: resolution.reason,
                            };
                        }
                        attributionResolution = resolution;
                        const canonicalComedianId = resolution.comedian.id;
                        const ownershipEvidence =
                            preserveCanonicalComedianProvenance(
                                review.evidence === null ? {} : review.evidence,
                                resolution,
                            );
                        await tx.podcastCandidateReview.update({
                            where: { id: review.id },
                            data: {
                                candidateStatus: "accepted",
                                associationType: "host",
                                reviewedAt,
                                reviewedBy: profileId,
                            },
                        });
                        const aliasComedianIds = resolution.aliasPath.filter(
                            (comedianId) => comedianId !== canonicalComedianId,
                        );
                        await tx.comedianPodcast.deleteMany({
                            where:
                                aliasComedianIds.length > 0
                                    ? {
                                          podcastId: review.podcastId,
                                          associationType: "host",
                                          reviewStatus: "accepted",
                                          OR: [
                                              {
                                                  comedianId:
                                                      canonicalComedianId,
                                                  source: {
                                                      not: review.source,
                                                  },
                                              },
                                              {
                                                  comedianId: {
                                                      in: aliasComedianIds,
                                                  },
                                              },
                                          ],
                                      }
                                    : {
                                          comedianId: canonicalComedianId,
                                          podcastId: review.podcastId,
                                          associationType: "host",
                                          source: { not: review.source },
                                          reviewStatus: "accepted",
                                      },
                        });
                        await tx.comedianPodcast.upsert({
                            where: {
                                comedianId_podcastId_associationType_source: {
                                    comedianId: canonicalComedianId,
                                    podcastId: review.podcastId,
                                    associationType: "host",
                                    source: review.source,
                                },
                            },
                            create: {
                                comedianId: canonicalComedianId,
                                podcastId: review.podcastId,
                                associationType: "host",
                                source: review.source,
                                reviewStatus: "accepted",
                                confidence: review.confidence,
                                evidence: ownershipEvidence,
                                reviewedAt,
                                reviewedBy: profileId,
                            },
                            update: {
                                reviewStatus: "accepted",
                                confidence: review.confidence,
                                evidence: ownershipEvidence,
                                reviewedAt,
                                reviewedBy: profileId,
                            },
                        });
                    } else if (
                        parsed.data.action === "podcast-review-reject-host"
                    ) {
                        await tx.podcastCandidateReview.update({
                            where: { id: review.id },
                            data: {
                                candidateStatus: "rejected",
                                associationType: "host",
                                reviewedAt,
                                reviewedBy: profileId,
                            },
                        });
                    } else {
                        if (review.candidateStatus !== "rejected") {
                            return {
                                error: "Reject this host review before blocking the podcast",
                                status: 409,
                            };
                        }
                        await tx.podcastDenyList.upsert({
                            where: { podcastId: review.podcastId },
                            create: {
                                podcastId: review.podcastId,
                                source: review.podcast.source,
                                sourcePodcastId: review.podcast.sourcePodcastId,
                                feedUrl: review.podcast.feedUrl,
                                reason,
                                deniedAt: reviewedAt,
                                deniedBy: profileId,
                            },
                            update: {
                                source: review.podcast.source,
                                sourcePodcastId: review.podcast.sourcePodcastId,
                                feedUrl: review.podcast.feedUrl,
                                reason,
                                deniedAt: reviewedAt,
                                deniedBy: profileId,
                                restoredAt: null,
                                restoredBy: null,
                            },
                        });
                        await tx.podcastCandidateReview.updateMany({
                            where: {
                                podcastId: review.podcastId,
                                candidateStatus: "pending",
                            },
                            data: {
                                candidateStatus: "rejected",
                                reviewedAt,
                                reviewedBy: profileId,
                            },
                        });
                    }

                    const after = await findComedianSnapshot(tx, before.id);
                    if (!after) {
                        return { error: "Comedian not found", status: 404 };
                    }

                    await writeAdminActionAudit(tx, {
                        actorProfileId: profileId,
                        action:
                            parsed.data.action === "podcast-review-accept-host"
                                ? "podcast_candidate_review.accept_host"
                                : parsed.data.action ===
                                    "podcast-review-reject-host"
                                  ? "podcast_candidate_review.reject_host"
                                  : "podcast_candidate_review.block_podcast",
                        entityType: "podcast_candidate_review",
                        entityId: review.id,
                        reason,
                        before: {
                            review,
                            comedian: snapshotForAudit(before),
                        },
                        after: {
                            comedian: snapshotForAudit(after),
                            podcastId: review.podcastId,
                            attributionComedian:
                                attributionResolution?.comedian ?? null,
                            attributionAliasPath:
                                attributionResolution?.aliasPath ?? null,
                        },
                    });

                    return {
                        comedian: serializeComedian(after),
                        attributionComedian:
                            attributionResolution?.comedian ?? null,
                        name: after.name,
                    };
                }

                if (parsed.data.action === "set-parent") {
                    const parentComedianId = parsed.data.parentComedianId;

                    if (parentComedianId === before.id) {
                        return {
                            error: "A comedian cannot be their own parent",
                            status: 400,
                        };
                    }

                    if (parentComedianId) {
                        const parent = await findComedianSnapshot(
                            tx,
                            parentComedianId,
                        );
                        if (!parent) {
                            return {
                                error: "Parent comedian not found",
                                status: 404,
                            };
                        }
                        if (
                            await createsParentCycle(
                                tx,
                                before.id,
                                parentComedianId,
                            )
                        ) {
                            return {
                                error: "That parent relationship would create a cycle",
                                status: 400,
                            };
                        }
                    }

                    await tx.comedian.update({
                        where: { id: before.id },
                        data: { parentComedianId },
                    });

                    const after = await findComedianSnapshot(tx, before.id);
                    if (!after) {
                        return { error: "Comedian not found", status: 404 };
                    }

                    await writeAdminActionAudit(tx, {
                        actorProfileId: profileId,
                        action: "comedian.parent.update",
                        entityType: "comedian",
                        entityId: before.id,
                        reason: parsed.data.reason?.trim() || null,
                        before: snapshotForAudit(before),
                        after: snapshotForAudit(after),
                    });

                    return {
                        comedian: serializeComedian(after),
                        name: after.name,
                    };
                }

                if (parsed.data.action === "blocklist-remove") {
                    if (before.visible) {
                        return {
                            comedian: serializeComedian(before),
                            name: before.name,
                        };
                    }

                    const after = await tx.comedian.update({
                        where: { id: before.id },
                        data: { visible: true },
                        select: comedianSnapshotSelect,
                    });

                    await writeAdminActionAudit(tx, {
                        actorProfileId: profileId,
                        action: "comedian.visibility.unblock",
                        entityType: "comedian",
                        entityId: before.id,
                        reason: parsed.data.reason?.trim() || null,
                        before: snapshotForAudit(before),
                        after: snapshotForAudit(after),
                    });

                    return {
                        comedian: serializeComedian(after),
                        name: before.name,
                    };
                }

                const reason = parsed.data.reason?.trim() ?? "";
                const after = await tx.comedian.update({
                    where: { id: before.id },
                    data: {
                        visible: false,
                        blockReason: reason,
                        blockAddedBy: profileId,
                        blockAddedAt: new Date(),
                    },
                    select: comedianSnapshotSelect,
                });

                await writeAdminActionAudit(tx, {
                    actorProfileId: profileId,
                    action: "comedian.visibility.block",
                    entityType: "comedian",
                    entityId: before.id,
                    reason,
                    before: snapshotForAudit(before),
                    after: snapshotForAudit(after),
                });

                return {
                    comedian: serializeComedian(after),
                    name: before.name,
                };
            },
        );

        if ("error" in result) {
            return NextResponse.json(
                {
                    error: result.error,
                    ...("reason" in result && result.reason
                        ? { reason: result.reason }
                        : {}),
                },
                { status: result.status },
            );
        }

        revalidateComedianSurfaces(result.name);
        return NextResponse.json({
            ok: true,
            comedian: result.comedian,
            ...("attributionComedian" in result && result.attributionComedian
                ? { attributionComedian: result.attributionComedian }
                : {}),
        });
    } catch (error) {
        console.error("Admin comedians PATCH failed:", error);
        return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }
});

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = postSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const name = normalizeName(parsed.data.name);
    const uuid = generateComedianUuid(name);

    try {
        const result = await db.$transaction(
            async (tx: ComedianAdminWriter) => {
                const conflictingComedian = await tx.comedian.findUnique({
                    where: { uuid },
                    select: { id: true, name: true },
                });
                if (conflictingComedian) {
                    return {
                        error: `Generated UUID already belongs to ${conflictingComedian.name}`,
                        status: 409,
                    };
                }

                if (await findDenyListEntry(tx, name)) {
                    return {
                        error: "That name is blocked as an orphan identity",
                        status: 409,
                    };
                }

                const created = await tx.comedian.create({
                    data: {
                        name,
                        uuid,
                    },
                    select: comedianSnapshotSelect,
                });

                await writeAdminActionAudit(tx, {
                    actorProfileId: profileId,
                    action: "comedian.create",
                    entityType: "comedian",
                    entityId: created.id,
                    reason: null,
                    before: {},
                    after: snapshotForAudit(created),
                });

                return {
                    comedian: serializeComedian(created),
                    name: created.name,
                };
            },
        );

        if ("error" in result) {
            return NextResponse.json(
                { error: result.error },
                { status: result.status },
            );
        }

        revalidateComedianSurfaces(result.name);
        return NextResponse.json(
            { ok: true, comedian: result.comedian },
            { status: 201 },
        );
    } catch (error) {
        console.error("Admin comedians POST failed:", error);
        return NextResponse.json({ error: "Create failed" }, { status: 500 });
    }
});

export const PUT = withRequestMetrics(async function PUT(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = putSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const name = normalizeName(parsed.data.name);
    const uuid = generateComedianUuid(name);
    const website =
        "website" in parsed.data
            ? normalizeOptionalUrl(parsed.data.website)
            : undefined;
    const websiteScrapingUrl =
        "websiteScrapingUrl" in parsed.data
            ? normalizeOptionalUrl(parsed.data.websiteScrapingUrl)
            : undefined;
    const normalizeOptionalHandle = (value: string | null | undefined) => {
        const trimmed = value?.trim() ?? "";
        if (!trimmed) return null;
        // Strip a single leading "@" so we store the bare handle.
        return trimmed.startsWith("@") ? trimmed.slice(1) : trimmed;
    };
    const instagramAccount =
        "instagramAccount" in parsed.data
            ? normalizeOptionalHandle(parsed.data.instagramAccount)
            : undefined;
    const tiktokAccount =
        "tiktokAccount" in parsed.data
            ? normalizeOptionalHandle(parsed.data.tiktokAccount)
            : undefined;
    const youtubeAccount =
        "youtubeAccount" in parsed.data
            ? normalizeOptionalHandle(parsed.data.youtubeAccount)
            : undefined;
    const youtubeChannelId =
        "youtubeChannelId" in parsed.data
            ? normalizeOptionalUrl(parsed.data.youtubeChannelId)
            : undefined;
    const linktree =
        "linktree" in parsed.data
            ? normalizeOptionalUrl(parsed.data.linktree)
            : undefined;

    try {
        const currentInstagram =
            instagramAccount !== undefined
                ? await db.comedian.findUnique({
                      where: { id: parsed.data.comedianId },
                      select: { instagramAccount: true },
                  })
                : null;
        const shouldRefreshInstagram =
            Boolean(currentInstagram) &&
            Boolean(instagramAccount) &&
            (Boolean(parsed.data.refreshInstagramFollowers) ||
                instagramAccount !== currentInstagram?.instagramAccount);
        const instagramFollowerResolution = shouldRefreshInstagram
            ? await resolveInstagramFollowerCount(instagramAccount)
            : null;

        const result = await db.$transaction(
            async (tx: ComedianAdminWriter) => {
                const before = await findComedianSnapshot(
                    tx,
                    parsed.data.comedianId,
                );
                if (!before)
                    return { error: "Comedian not found", status: 404 };

                const conflictingComedian = await tx.comedian.findUnique({
                    where: { uuid },
                    select: { id: true, name: true },
                });
                if (
                    conflictingComedian &&
                    conflictingComedian.id !== before.id
                ) {
                    return {
                        error: `Generated UUID already belongs to ${conflictingComedian.name}`,
                        status: 409,
                    };
                }

                if (
                    name !== before.name &&
                    (await findDenyListEntry(tx, name))
                ) {
                    return {
                        error: "That name is blocked as an orphan identity",
                        status: 409,
                    };
                }

                const shouldResolveYoutubeChannelId =
                    Boolean(youtubeAccount) &&
                    (youtubeChannelId === undefined ||
                        (youtubeChannelId === null &&
                            !before.youtubeChannelId));
                const youtubeChannelResolution = shouldResolveYoutubeChannelId
                    ? await resolveYouTubeChannelId(youtubeAccount)
                    : null;
                const nextYoutubeChannelId =
                    youtubeChannelId ??
                    (youtubeChannelId === null && before.youtubeChannelId
                        ? null
                        : youtubeChannelResolution?.status === "resolved"
                          ? youtubeChannelResolution.channelId
                          : youtubeChannelId === null && youtubeAccount === null
                            ? null
                            : undefined);

                const instagramAccountChanged =
                    instagramAccount !== undefined &&
                    instagramAccount !== before.instagramAccount;
                const instagramRefreshAttempted =
                    instagramFollowerResolution !== null;
                const resolvedInstagramFollowers =
                    instagramFollowerResolution?.status === "resolved"
                        ? instagramFollowerResolution.followerCount
                        : null;
                const shouldClearInstagramFollowers =
                    instagramAccountChanged ||
                    instagramFollowerResolution?.status === "not_found";
                const shouldWriteInstagramFollowers =
                    instagramFollowerResolution?.status === "resolved" ||
                    shouldClearInstagramFollowers;
                const instagramFollowerData = shouldWriteInstagramFollowers
                    ? {
                          instagramFollowers: resolvedInstagramFollowers,
                          instagramFollowersRefreshedAt:
                              resolvedInstagramFollowers === null
                                  ? null
                                  : new Date(),
                          popularity:
                              recalculatePopularityForInstagramFollowers({
                                  popularity: before.popularity,
                                  previousInstagramFollowers:
                                      before.instagramFollowers,
                                  nextInstagramFollowers:
                                      resolvedInstagramFollowers,
                                  tiktokFollowers: before.tiktokFollowers,
                                  youtubeFollowers: before.youtubeFollowers,
                              }),
                      }
                    : {};

                await tx.comedian.update({
                    where: { id: before.id },
                    data: {
                        name,
                        uuid,
                        ...(website !== undefined ? { website } : {}),
                        ...(websiteScrapingUrl !== undefined
                            ? { websiteScrapingUrl }
                            : {}),
                        ...(instagramAccount !== undefined
                            ? { instagramAccount }
                            : {}),
                        ...instagramFollowerData,
                        ...(tiktokAccount !== undefined
                            ? { tiktokAccount }
                            : {}),
                        ...(youtubeAccount !== undefined
                            ? { youtubeAccount }
                            : {}),
                        ...(nextYoutubeChannelId !== undefined
                            ? { youtubeChannelId: nextYoutubeChannelId }
                            : {}),
                        ...(linktree !== undefined ? { linktree } : {}),
                    },
                });

                const after = await findComedianSnapshot(tx, before.id);
                if (!after) {
                    return { error: "Comedian not found", status: 404 };
                }

                await writeAdminActionAudit(tx, {
                    actorProfileId: profileId,
                    action: "comedian.update",
                    entityType: "comedian",
                    entityId: before.id,
                    reason: parsed.data.reason?.trim() || null,
                    before: snapshotForAudit(before),
                    after: snapshotForAudit(after),
                });

                return {
                    comedian: serializeComedian(after),
                    previousName: before.name,
                    name: after.name,
                    instagramFollowerRefresh:
                        instagramAccountChanged && instagramAccount === null
                            ? { status: "cleared" as const }
                            : instagramRefreshAttempted
                              ? instagramFollowerResolution
                              : null,
                };
            },
        );

        if ("error" in result) {
            return NextResponse.json(
                { error: result.error },
                { status: result.status },
            );
        }

        revalidateComedianSurfaces(result.previousName);
        revalidateComedianSurfaces(result.name);
        return NextResponse.json({
            ok: true,
            comedian: result.comedian,
            instagramFollowerRefresh: result.instagramFollowerRefresh,
        });
    } catch (error) {
        console.error("Admin comedians PUT failed:", error);
        return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }
});
