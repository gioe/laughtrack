import { writeAdminActionAudit } from "@/lib/admin/audit";
import { listPendingPodcastOwnershipReviews } from "@/lib/admin/podcastOwnershipReviews";
import { requireAdminForApi } from "@/lib/auth/requireAdmin";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const decisionSchema = z
    .object({
        podcastId: z.number().int().positive(),
        ownerComedianId: z.number().int().positive().nullable(),
        reason: z.string().trim().max(1000).optional(),
    })
    .strict();

async function readBody(req: NextRequest) {
    try {
        return await req.json();
    } catch {
        return null;
    }
}

function candidateSnapshot(candidate: {
    id: number;
    comedianId: number;
    podcastId: number | null;
    source: string;
    sourcePodcastId: string;
    candidateStatus: string;
    associationType: string | null;
    confidence: number;
    evidence: Prisma.JsonValue;
    reviewedAt: Date | null;
    reviewedBy: string | null;
    comedian: { id: number; name: string; uuid: string };
    podcast: { id: number; slug: string; title: string } | null;
}) {
    return {
        id: candidate.id,
        comedianId: candidate.comedianId,
        podcastId: candidate.podcastId,
        source: candidate.source,
        sourcePodcastId: candidate.sourcePodcastId,
        candidateStatus: candidate.candidateStatus,
        associationType: candidate.associationType,
        confidence: candidate.confidence,
        evidence: jsonForWrite(candidate.evidence),
        reviewedAt: candidate.reviewedAt?.toISOString() ?? null,
        reviewedBy: candidate.reviewedBy,
        comedian: candidate.comedian,
        podcast: candidate.podcast,
    };
}

function ownershipSnapshot(ownership: {
    id: number;
    comedianId: number;
    podcastId: number;
    associationType: string;
    source: string;
    reviewStatus: string;
    confidence: number;
    evidence?: Prisma.JsonValue;
    reviewedAt: Date | null;
    reviewedBy: string | null;
}) {
    return {
        id: ownership.id,
        comedianId: ownership.comedianId,
        podcastId: ownership.podcastId,
        associationType: ownership.associationType,
        source: ownership.source,
        reviewStatus: ownership.reviewStatus,
        confidence: ownership.confidence,
        evidence:
            "evidence" in ownership
                ? jsonForWrite(ownership.evidence ?? {})
                : undefined,
        reviewedAt: ownership.reviewedAt?.toISOString() ?? null,
        reviewedBy: ownership.reviewedBy,
    };
}

function jsonForWrite(value: Prisma.JsonValue): Prisma.InputJsonValue {
    return value === null ? {} : value;
}

function revalidatePodcastReviewSurfaces(slug: string | null | undefined) {
    revalidateTag("podcasts-search-page-data-v2");
    revalidateTag("podcast-detail-data-v2");
    revalidateTag("podcast-metadata");
    if (slug) {
        revalidateTag(slug);
    }
}

export async function GET() {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;

    const candidates = await listPendingPodcastOwnershipReviews();
    return NextResponse.json({ candidates });
}

export async function POST(req: NextRequest) {
    const gate = await requireAdminForApi();
    if (!gate.ok) return gate.response;
    const { profileId } = gate.context;

    const parsed = decisionSchema.safeParse(await readBody(req));
    if (!parsed.success) {
        return NextResponse.json(
            { error: "Invalid payload", issues: parsed.error.issues },
            { status: 400 },
        );
    }

    const { podcastId, ownerComedianId } = parsed.data;
    const reason = parsed.data.reason?.trim() || null;

    try {
        const result = await db.$transaction(async (tx) => {
            const podcast = await tx.podcast.findUnique({
                where: { id: podcastId },
                select: {
                    id: true,
                    slug: true,
                    title: true,
                },
            });
            if (!podcast) return null;

            const owner = ownerComedianId
                ? await tx.comedian.findUnique({
                      where: { id: ownerComedianId },
                      select: { id: true, name: true, uuid: true },
                  })
                : null;
            if (ownerComedianId && !owner) {
                return { missingOwner: true, podcast };
            }

            const beforeCandidates = await tx.podcastCandidateReview.findMany({
                where: {
                    podcastId,
                    candidateStatus: "pending",
                },
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
                    reviewedAt: true,
                    reviewedBy: true,
                    comedian: {
                        select: {
                            id: true,
                            name: true,
                            uuid: true,
                        },
                    },
                    podcast: {
                        select: {
                            id: true,
                            slug: true,
                            title: true,
                        },
                    },
                },
                orderBy: [{ confidence: "desc" }, { id: "asc" }],
            });

            const beforeOwnerships = await tx.comedianPodcast.findMany({
                where: { podcastId },
                select: {
                    id: true,
                    comedianId: true,
                    podcastId: true,
                    source: true,
                    associationType: true,
                    reviewStatus: true,
                    confidence: true,
                    evidence: true,
                    reviewedAt: true,
                    reviewedBy: true,
                },
            });

            const reviewedAt = new Date();
            const ownerCandidate = ownerComedianId
                ? (beforeCandidates.find(
                      (candidate) => candidate.comedianId === ownerComedianId,
                  ) ?? null)
                : null;
            const associationType = ownerCandidate?.associationType ?? "host";
            const ownerSource = ownerCandidate?.source ?? "manual";
            const ownerConfidence = ownerCandidate?.confidence ?? 1;
            const ownerEvidence = ownerCandidate
                ? jsonForWrite(ownerCandidate.evidence)
                : {
                      adminAdded: true,
                      reason,
                  };

            if (ownerComedianId) {
                await tx.podcastCandidateReview.updateMany({
                    where: {
                        podcastId,
                        candidateStatus: "pending",
                        comedianId: ownerComedianId,
                    },
                    data: {
                        candidateStatus: "accepted",
                        associationType,
                        reviewedAt,
                        reviewedBy: profileId,
                    },
                });
                await tx.podcastCandidateReview.updateMany({
                    where: {
                        podcastId,
                        candidateStatus: "pending",
                        comedianId: { not: ownerComedianId },
                    },
                    data: {
                        candidateStatus: "rejected",
                        reviewedAt,
                        reviewedBy: profileId,
                    },
                });
                await tx.comedianPodcast.updateMany({
                    where: {
                        podcastId,
                        reviewStatus: "accepted",
                        comedianId: { not: ownerComedianId },
                    },
                    data: {
                        reviewStatus: "rejected",
                        reviewedAt,
                        reviewedBy: profileId,
                    },
                });
            } else {
                await tx.podcastCandidateReview.updateMany({
                    where: {
                        podcastId,
                        candidateStatus: "pending",
                    },
                    data: {
                        candidateStatus: "rejected",
                        reviewedAt,
                        reviewedBy: profileId,
                    },
                });
                await tx.comedianPodcast.updateMany({
                    where: {
                        podcastId,
                        reviewStatus: "accepted",
                    },
                    data: {
                        reviewStatus: "rejected",
                        reviewedAt,
                        reviewedBy: profileId,
                    },
                });
            }

            const ownership = ownerComedianId
                ? await tx.comedianPodcast.upsert({
                      where: {
                          comedianId_podcastId_associationType_source: {
                              comedianId: ownerComedianId,
                              podcastId,
                              associationType,
                              source: ownerSource,
                          },
                      },
                      create: {
                          comedianId: ownerComedianId,
                          podcastId,
                          associationType,
                          source: ownerSource,
                          reviewStatus: "accepted",
                          confidence: ownerConfidence,
                          evidence: ownerEvidence,
                          reviewedAt,
                          reviewedBy: profileId,
                      },
                      update: {
                          reviewStatus: "accepted",
                          confidence: ownerConfidence,
                          evidence: ownerEvidence,
                          reviewedAt,
                          reviewedBy: profileId,
                      },
                  })
                : null;

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: ownerComedianId
                    ? "podcast_ownership_review.approve"
                    : "podcast_ownership_review.block",
                entityType: "podcast",
                entityId: podcastId,
                reason,
                before: {
                    podcast,
                    candidates: beforeCandidates.map(candidateSnapshot),
                    ownerships: beforeOwnerships.map(ownershipSnapshot),
                },
                after: {
                    podcast,
                    owner,
                    ownership: ownership ? ownershipSnapshot(ownership) : null,
                },
            });

            return { podcast, owner, ownership };
        });

        if (!result) {
            return NextResponse.json(
                { error: "Podcast not found" },
                { status: 404 },
            );
        }
        if ("missingOwner" in result) {
            return NextResponse.json(
                { error: "Owner comedian not found" },
                { status: 422 },
            );
        }

        revalidatePodcastReviewSurfaces(result.podcast.slug);

        return NextResponse.json({
            ok: true,
            podcast: result.podcast,
            owner: result.owner,
            ownership: result.ownership,
        });
    } catch (error) {
        console.error("Admin podcast ownership review failed:", error);
        return NextResponse.json({ error: "Review failed" }, { status: 500 });
    }
}
