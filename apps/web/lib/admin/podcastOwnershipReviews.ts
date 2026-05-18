import { db } from "@/lib/db";

const PENDING_LIMIT = 100;

type CandidateRow = {
    id: number;
    comedianId: number;
    podcastId: number | null;
    source: string;
    sourcePodcastId: string;
    candidateStatus: string;
    associationType: string | null;
    confidence: number;
    evidence: unknown;
    createdAt: Date;
    updatedAt: Date;
    comedian: {
        id: number;
        uuid: string;
        name: string;
    };
    podcast: {
        id: number;
        slug: string;
        title: string;
        authorName: string | null;
        imageUrl: string | null;
        websiteUrl: string | null;
        feedUrl: string | null;
    } | null;
};

type OwnershipRow = {
    id: number;
    comedianId: number;
    podcastId: number;
    associationType: string;
    source: string;
    reviewStatus: string;
    confidence: number;
    reviewedAt: Date | null;
    reviewedBy: string | null;
};

export type AdminPodcastOwnershipReviewCandidate = {
    id: number;
    source: string;
    sourcePodcastId: string;
    candidateStatus: string;
    associationType: string | null;
    confidence: number;
    evidence: unknown;
    createdAt: string;
    updatedAt: string;
    comedian: {
        id: number;
        uuid: string;
        name: string;
    };
    podcast: {
        id: number;
        slug: string;
        title: string;
        authorName: string | null;
        imageUrl: string | null;
        websiteUrl: string | null;
        feedUrl: string | null;
    } | null;
    existingOwnerships: Array<{
        id: number;
        associationType: string;
        source: string;
        reviewStatus: string;
        confidence: number;
        reviewedAt: string | null;
        reviewedBy: string | null;
    }>;
};

function toIso(value: Date | null) {
    return value ? value.toISOString() : null;
}

function serializeCandidate(
    candidate: CandidateRow,
    ownerships: OwnershipRow[],
): AdminPodcastOwnershipReviewCandidate {
    return {
        id: candidate.id,
        source: candidate.source,
        sourcePodcastId: candidate.sourcePodcastId,
        candidateStatus: candidate.candidateStatus,
        associationType: candidate.associationType,
        confidence: candidate.confidence,
        evidence: candidate.evidence,
        createdAt: candidate.createdAt.toISOString(),
        updatedAt: candidate.updatedAt.toISOString(),
        comedian: candidate.comedian,
        podcast: candidate.podcast,
        existingOwnerships: ownerships.map((ownership) => ({
            id: ownership.id,
            associationType: ownership.associationType,
            source: ownership.source,
            reviewStatus: ownership.reviewStatus,
            confidence: ownership.confidence,
            reviewedAt: toIso(ownership.reviewedAt),
            reviewedBy: ownership.reviewedBy,
        })),
    };
}

export async function listPendingPodcastOwnershipReviews(): Promise<
    AdminPodcastOwnershipReviewCandidate[]
> {
    const candidates = await db.podcastCandidateReview.findMany({
        where: { candidateStatus: "pending" },
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
            createdAt: true,
            updatedAt: true,
            comedian: {
                select: {
                    id: true,
                    uuid: true,
                    name: true,
                },
            },
            podcast: {
                select: {
                    id: true,
                    slug: true,
                    title: true,
                    authorName: true,
                    imageUrl: true,
                    websiteUrl: true,
                    feedUrl: true,
                },
            },
        },
        orderBy: [{ confidence: "desc" }, { id: "asc" }],
        take: PENDING_LIMIT,
    });

    const pairs = candidates
        .filter((candidate) => candidate.podcastId !== null)
        .map((candidate) => ({
            comedianId: candidate.comedianId,
            podcastId: candidate.podcastId as number,
        }));

    const ownerships = pairs.length
        ? await db.comedianPodcast.findMany({
              where: {
                  OR: pairs,
              },
              select: {
                  id: true,
                  comedianId: true,
                  podcastId: true,
                  associationType: true,
                  source: true,
                  reviewStatus: true,
                  confidence: true,
                  reviewedAt: true,
                  reviewedBy: true,
              },
              orderBy: [{ reviewStatus: "asc" }, { id: "asc" }],
          })
        : [];

    return candidates.map((candidate) =>
        serializeCandidate(
            candidate,
            ownerships.filter(
                (ownership) =>
                    ownership.comedianId === candidate.comedianId &&
                    ownership.podcastId === candidate.podcastId,
            ),
        ),
    );
}
