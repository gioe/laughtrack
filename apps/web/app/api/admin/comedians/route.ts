import { writeAdminActionAudit } from "@/lib/admin/audit";
import type { AdminComedianListItem } from "@/lib/admin/comedianManagement";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import {
    buildComedianImageAssetUrl,
    buildComedianImageUrls,
} from "@/lib/data/comedian/imageAssets";
import type { Prisma } from "@prisma/client";
import crypto from "crypto";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { withRequestMetrics } from "@/lib/metrics";

type ComedianSnapshot = {
    id: number;
    uuid: string;
    createdAt: Date;
    name: string;
    website: string | null;
    websiteScrapingUrl: string | null;
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
        hasImage: Boolean(comedian.hasImage),
        activeImageAsset: comedian.imageAssets?.[0] ?? null,
        popularity: comedian.popularity,
        totalShows: comedian.totalShows,
        parentComedianId: comedian.parentComedianId,
        parent: comedian.parentComedian,
        childCount: comedian._count.alternativeNames,
    };
}

function serializeComedian(
    comedian: ComedianSnapshot,
    denyListEntry: DenyListRow | null,
): AdminComedianListItem {
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

                    if (parsed.data.action === "podcast-review-accept-host") {
                        await tx.podcastCandidateReview.update({
                            where: { id: review.id },
                            data: {
                                candidateStatus: "accepted",
                                associationType: "host",
                                reviewedAt,
                                reviewedBy: profileId,
                            },
                        });
                        await tx.comedianPodcast.deleteMany({
                            where: {
                                comedianId: before.id,
                                podcastId: review.podcastId,
                                associationType: "host",
                                source: { not: review.source },
                                reviewStatus: "accepted",
                            },
                        });
                        await tx.comedianPodcast.upsert({
                            where: {
                                comedianId_podcastId_associationType_source: {
                                    comedianId: before.id,
                                    podcastId: review.podcastId,
                                    associationType: "host",
                                    source: review.source,
                                },
                            },
                            create: {
                                comedianId: before.id,
                                podcastId: review.podcastId,
                                associationType: "host",
                                source: review.source,
                                reviewStatus: "accepted",
                                confidence: review.confidence,
                                evidence:
                                    review.evidence === null
                                        ? {}
                                        : review.evidence,
                                reviewedAt,
                                reviewedBy: profileId,
                            },
                            update: {
                                reviewStatus: "accepted",
                                confidence: review.confidence,
                                evidence:
                                    review.evidence === null
                                        ? {}
                                        : review.evidence,
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
                        },
                    });

                    const denyListEntry = await findDenyListEntry(
                        tx,
                        after.name,
                    );
                    return {
                        comedian: serializeComedian(after, denyListEntry),
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

                    const denyListEntry = await findDenyListEntry(
                        tx,
                        after.name,
                    );
                    return {
                        comedian: serializeComedian(after, denyListEntry),
                        name: after.name,
                    };
                }

                const beforeDenyListEntry = await findDenyListEntry(
                    tx,
                    before.name,
                );

                if (parsed.data.action === "blocklist-remove") {
                    if (!beforeDenyListEntry) {
                        return {
                            comedian: serializeComedian(before, null),
                            name: before.name,
                        };
                    }

                    const deletedRows = await tx.$queryRaw<DenyListRow[]>`
                        DELETE FROM comedian_deny_list
                        WHERE lower(btrim(regexp_replace(replace(name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) =
                              lower(btrim(regexp_replace(replace(${before.name}, chr(160), ' '), '[[:space:]]+', ' ', 'g')))
                        RETURNING name, reason, added_by, deleted_at
                    `;
                    const deletedEntry = deletedRows[0] ?? beforeDenyListEntry;

                    await writeAdminActionAudit(tx, {
                        actorProfileId: profileId,
                        action: "comedian_deny_list.delete",
                        entityType: "comedian_deny_list",
                        entityId: deletedEntry.name,
                        reason: parsed.data.reason?.trim() || null,
                        before: {
                            name: deletedEntry.name,
                            reason: deletedEntry.reason,
                            addedBy: deletedEntry.added_by,
                            addedAt: serializeDate(deletedEntry.deleted_at),
                        },
                        after: {},
                    });

                    return {
                        comedian: serializeComedian(before, null),
                        name: before.name,
                    };
                }

                const reason = parsed.data.reason?.trim() ?? "";
                const name = normalizeName(before.name);
                const rows = await tx.$queryRaw<DenyListRow[]>`
                INSERT INTO comedian_deny_list (name, reason, added_by)
                VALUES (${beforeDenyListEntry?.name ?? name}, ${reason}, ${profileId})
                ON CONFLICT (name) DO UPDATE
                SET reason = EXCLUDED.reason,
                    added_by = EXCLUDED.added_by,
                    deleted_at = now()
                RETURNING name, reason, added_by, deleted_at
            `;
                const afterDenyListEntry = rows[0];

                await writeAdminActionAudit(tx, {
                    actorProfileId: profileId,
                    action: beforeDenyListEntry
                        ? "comedian_deny_list.update"
                        : "comedian_deny_list.create",
                    entityType: "comedian_deny_list",
                    entityId: afterDenyListEntry.name,
                    reason,
                    before: beforeDenyListEntry
                        ? {
                              name: beforeDenyListEntry.name,
                              reason: beforeDenyListEntry.reason,
                              addedBy: beforeDenyListEntry.added_by,
                              addedAt: serializeDate(
                                  beforeDenyListEntry.deleted_at,
                              ),
                          }
                        : {},
                    after: {
                        name: afterDenyListEntry.name,
                        reason: afterDenyListEntry.reason,
                        addedBy: afterDenyListEntry.added_by,
                        addedAt: serializeDate(afterDenyListEntry.deleted_at),
                    },
                });

                return {
                    comedian: serializeComedian(before, afterDenyListEntry),
                    name: before.name,
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
        return NextResponse.json({ ok: true, comedian: result.comedian });
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

                const denyListEntry = await findDenyListEntry(tx, created.name);
                return {
                    comedian: serializeComedian(created, denyListEntry),
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

    try {
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

                await tx.comedian.update({
                    where: { id: before.id },
                    data: {
                        name,
                        uuid,
                        ...(website !== undefined ? { website } : {}),
                        ...(websiteScrapingUrl !== undefined
                            ? { websiteScrapingUrl }
                            : {}),
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

                const denyListEntry = await findDenyListEntry(tx, after.name);
                return {
                    comedian: serializeComedian(after, denyListEntry),
                    previousName: before.name,
                    name: after.name,
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
        return NextResponse.json({ ok: true, comedian: result.comedian });
    } catch (error) {
        console.error("Admin comedians PUT failed:", error);
        return NextResponse.json({ error: "Update failed" }, { status: 500 });
    }
});
