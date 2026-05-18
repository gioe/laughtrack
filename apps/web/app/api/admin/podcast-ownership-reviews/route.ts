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
        candidateId: z.number().int().positive(),
        action: z.enum(["accept", "reject"]),
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

    const { candidateId, action } = parsed.data;
    const reason = parsed.data.reason?.trim() || null;

    try {
        const result = await db.$transaction(async (tx) => {
            const before = await tx.podcastCandidateReview.findUnique({
                where: { id: candidateId },
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
            });

            if (!before) return null;
            if (before.candidateStatus !== "pending") {
                return { conflict: true, candidate: before };
            }
            if (action === "accept" && !before.podcastId) {
                return { missingPodcast: true, candidate: before };
            }

            const reviewedAt = new Date();
            const associationType = before.associationType ?? "host";
            const after = await tx.podcastCandidateReview.update({
                where: { id: candidateId },
                data: {
                    candidateStatus:
                        action === "accept" ? "accepted" : "rejected",
                    associationType,
                    reviewedAt,
                    reviewedBy: profileId,
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
            });

            const ownership =
                action === "accept" && before.podcastId
                    ? await tx.comedianPodcast.upsert({
                          where: {
                              comedianId_podcastId_associationType_source: {
                                  comedianId: before.comedianId,
                                  podcastId: before.podcastId,
                                  associationType,
                                  source: before.source,
                              },
                          },
                          create: {
                              comedianId: before.comedianId,
                              podcastId: before.podcastId,
                              associationType,
                              source: before.source,
                              reviewStatus: "accepted",
                              confidence: before.confidence,
                              evidence: jsonForWrite(before.evidence),
                              reviewedAt,
                              reviewedBy: profileId,
                          },
                          update: {
                              reviewStatus: "accepted",
                              confidence: before.confidence,
                              evidence: jsonForWrite(before.evidence),
                              reviewedAt,
                              reviewedBy: profileId,
                          },
                      })
                    : null;

            await writeAdminActionAudit(tx, {
                actorProfileId: profileId,
                action: `podcast_candidate_review.${action}`,
                entityType: "podcast_candidate_review",
                entityId: candidateId,
                reason,
                before: candidateSnapshot(before),
                after: {
                    candidate: candidateSnapshot(after),
                    ownership,
                },
            });

            return { candidate: after, ownership };
        });

        if (!result) {
            return NextResponse.json(
                { error: "Candidate not found" },
                { status: 404 },
            );
        }
        if ("conflict" in result) {
            return NextResponse.json(
                { error: "Candidate has already been reviewed" },
                { status: 409 },
            );
        }
        if ("missingPodcast" in result) {
            return NextResponse.json(
                { error: "Candidate is not linked to a podcast" },
                { status: 422 },
            );
        }

        revalidatePodcastReviewSurfaces(result.candidate.podcast?.slug);

        return NextResponse.json({
            ok: true,
            candidate: candidateSnapshot(result.candidate),
            ownership: result.ownership,
        });
    } catch (error) {
        console.error("Admin podcast ownership review failed:", error);
        return NextResponse.json({ error: "Review failed" }, { status: 500 });
    }
}
