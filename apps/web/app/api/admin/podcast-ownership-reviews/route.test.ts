import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const mocks = vi.hoisted(() => ({
    auth: vi.fn(),
    revalidateTag: vi.fn(),
}));

vi.mock("@/auth", () => ({
    auth: mocks.auth,
}));

vi.mock("next/cache", () => ({
    revalidateTag: mocks.revalidateTag,
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: {
            findFirst: vi.fn(),
        },
        podcastCandidateReview: {
            findMany: vi.fn(),
        },
        comedianPodcast: {
            findMany: vi.fn(),
        },
        podcast: {
            findUnique: vi.fn(),
        },
        comedian: {
            findUnique: vi.fn(),
        },
        $transaction: vi.fn(),
    },
}));

import { GET, POST } from "./route";
import { db } from "@/lib/db";

const mockFindProfile = vi.mocked(db.userProfile.findFirst);
const mockFindCandidates = vi.mocked(db.podcastCandidateReview.findMany);
const mockFindOwnerships = vi.mocked(db.comedianPodcast.findMany);
const mockTransaction = vi.mocked(db.$transaction);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest(
        "http://localhost/api/admin/podcast-ownership-reviews",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        },
    );
}

beforeEach(() => {
    vi.clearAllMocks();
    mocks.auth.mockResolvedValue(adminSession);
    mockFindProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
    mockFindCandidates.mockResolvedValue([]);
    mockFindOwnerships.mockResolvedValue([]);
});

describe("GET /api/admin/podcast-ownership-reviews", () => {
    it("requires admin access", async () => {
        mocks.auth.mockResolvedValue(null);

        const res = await GET();

        expect(res.status).toBe(401);
    });

    it("lists pending candidates with context", async () => {
        mockFindCandidates.mockResolvedValue([
            {
                id: 12,
                comedianId: 42,
                podcastId: 99,
                source: "podcast-index",
                sourcePodcastId: "feed-99",
                candidateStatus: "pending",
                associationType: "host",
                confidence: 0.91,
                evidence: { matched_name: "Jane Comic" },
                createdAt: new Date("2026-05-17T12:00:00Z"),
                updatedAt: new Date("2026-05-17T12:30:00Z"),
                comedian: {
                    id: 42,
                    name: "Jane Comic",
                    uuid: "comedian-uuid",
                },
                podcast: {
                    id: 99,
                    slug: "jane-show",
                    title: "The Jane Show",
                    authorName: "Jane Comic",
                    imageUrl: "https://img.example/jane.jpg",
                    websiteUrl: "https://pod.example",
                    feedUrl: "https://pod.example/feed.xml",
                },
            },
        ] as never);
        mockFindOwnerships.mockResolvedValue([
            {
                id: 55,
                comedianId: 42,
                podcastId: 99,
                associationType: "host",
                source: "manual",
                reviewStatus: "accepted",
                confidence: 1,
                reviewedAt: new Date("2026-05-16T12:00:00Z"),
                reviewedBy: "profile-2",
                comedian: {
                    id: 42,
                    name: "Jane Comic",
                    uuid: "comedian-uuid",
                },
            },
        ] as never);

        const res = await GET();
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.candidates).toEqual([
            expect.objectContaining({
                id: 12,
                comedian: {
                    id: 42,
                    name: "Jane Comic",
                    uuid: "comedian-uuid",
                },
                podcast: expect.objectContaining({
                    id: 99,
                    slug: "jane-show",
                    title: "The Jane Show",
                }),
                confidence: 0.91,
                evidence: { matched_name: "Jane Comic" },
                existingOwnerships: [
                    expect.objectContaining({
                        id: 55,
                        reviewStatus: "accepted",
                        comedian: {
                            id: 42,
                            name: "Jane Comic",
                            uuid: "comedian-uuid",
                        },
                    }),
                ],
            }),
        ]);
    });
});

describe("POST /api/admin/podcast-ownership-reviews", () => {
    it("rejects invalid payloads", async () => {
        const res = await POST(
            makeRequest({ podcastId: 99, ownerComedianId: "hold" }),
        );

        expect(res.status).toBe(400);
    });

    it("approves a podcast owner, rejects competing candidates, audits, and revalidates", async () => {
        const podcast = { id: 99, slug: "jane-show", title: "The Jane Show" };
        const owner = { id: 42, name: "Jane Comic", uuid: "comedian-uuid" };
        const candidate = {
            id: 12,
            comedianId: 42,
            podcastId: 99,
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            candidateStatus: "pending",
            associationType: "host",
            confidence: 0.91,
            evidence: { matched_name: "Jane Comic" },
            reviewedAt: null,
            reviewedBy: null,
            comedian: { id: 42, name: "Jane Comic", uuid: "comedian-uuid" },
            podcast,
        };
        const upsertedOwnership = {
            id: 88,
            comedianId: 42,
            podcastId: 99,
            associationType: "host",
            source: "podcast-index",
            reviewStatus: "accepted",
            confidence: 0.91,
            evidence: { matched_name: "Jane Comic" },
            reviewedAt: new Date("2026-05-18T12:00:00Z"),
            reviewedBy: "profile-1",
        };
        const auditCreate = vi.fn();
        const podcastFindUnique = vi.fn().mockResolvedValue(podcast);
        const comedianFindUnique = vi.fn().mockResolvedValue(owner);
        const candidateFindMany = vi.fn().mockResolvedValue([candidate]);
        const candidateUpdateMany = vi.fn();
        const ownershipFindMany = vi.fn().mockResolvedValue([]);
        const ownershipUpdateMany = vi.fn();
        const upsert = vi.fn().mockResolvedValue(upsertedOwnership);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: { findUnique: podcastFindUnique },
                comedian: { findUnique: comedianFindUnique },
                podcastCandidateReview: {
                    findMany: candidateFindMany,
                    updateMany: candidateUpdateMany,
                },
                comedianPodcast: {
                    findMany: ownershipFindMany,
                    updateMany: ownershipUpdateMany,
                    upsert,
                },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(
            makeRequest({
                podcastId: 99,
                ownerComedianId: 42,
                reason: "Matches host feed",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.owner).toEqual(owner);
        expect(candidateUpdateMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    podcastId: 99,
                    comedianId: 42,
                }),
                data: expect.objectContaining({
                    candidateStatus: "accepted",
                    reviewedBy: "profile-1",
                }),
            }),
        );
        expect(candidateUpdateMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    podcastId: 99,
                    comedianId: { not: 42 },
                }),
                data: expect.objectContaining({
                    candidateStatus: "rejected",
                    reviewedBy: "profile-1",
                }),
            }),
        );
        expect(ownershipUpdateMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    podcastId: 99,
                    reviewStatus: "accepted",
                    comedianId: { not: 42 },
                },
                data: expect.objectContaining({
                    reviewStatus: "rejected",
                    reviewedBy: "profile-1",
                }),
            }),
        );
        expect(upsert).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    comedianId_podcastId_associationType_source: {
                        comedianId: 42,
                        podcastId: 99,
                        associationType: "host",
                        source: "podcast-index",
                    },
                },
                create: expect.objectContaining({
                    reviewStatus: "accepted",
                    reviewedBy: "profile-1",
                }),
                update: expect.objectContaining({
                    reviewStatus: "accepted",
                    reviewedBy: "profile-1",
                }),
            }),
        );
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                actorProfileId: "profile-1",
                action: "podcast_ownership_review.approve",
                entityType: "podcast",
                entityId: "99",
                reason: "Matches host feed",
            }),
        });
        expect(mocks.revalidateTag).toHaveBeenCalledWith(
            "podcasts-search-page-data-v2",
        );
        expect(mocks.revalidateTag).toHaveBeenCalledWith(
            "podcast-detail-data-v2",
        );
        expect(mocks.revalidateTag).toHaveBeenCalledWith("jane-show");
    });

    it("blocks a podcast by rejecting pending candidates and accepted ownerships", async () => {
        const podcast = { id: 99, slug: "jane-show", title: "The Jane Show" };
        const candidate = {
            id: 12,
            comedianId: 42,
            podcastId: 99,
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            candidateStatus: "pending",
            associationType: "host",
            confidence: 0.42,
            evidence: {},
            reviewedAt: null,
            reviewedBy: null,
            comedian: { id: 42, name: "Jane Comic", uuid: "comedian-uuid" },
            podcast,
        };
        const auditCreate = vi.fn();
        const podcastFindUnique = vi.fn().mockResolvedValue(podcast);
        const candidateFindMany = vi.fn().mockResolvedValue([candidate]);
        const candidateUpdateMany = vi.fn();
        const ownershipFindMany = vi.fn().mockResolvedValue([]);
        const ownershipUpdateMany = vi.fn();
        const upsert = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: { findUnique: podcastFindUnique },
                comedian: { findUnique: vi.fn() },
                podcastCandidateReview: {
                    findMany: candidateFindMany,
                    updateMany: candidateUpdateMany,
                },
                comedianPodcast: {
                    findMany: ownershipFindMany,
                    updateMany: ownershipUpdateMany,
                    upsert,
                },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(
            makeRequest({
                podcastId: 99,
                ownerComedianId: null,
                reason: "Different person",
            }),
        );

        expect(res.status).toBe(200);
        expect(candidateUpdateMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { podcastId: 99, candidateStatus: "pending" },
                data: expect.objectContaining({
                    candidateStatus: "rejected",
                    reviewedBy: "profile-1",
                }),
            }),
        );
        expect(ownershipUpdateMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { podcastId: 99, reviewStatus: "accepted" },
                data: expect.objectContaining({
                    reviewStatus: "rejected",
                    reviewedBy: "profile-1",
                }),
            }),
        );
        expect(upsert).not.toHaveBeenCalled();
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                action: "podcast_ownership_review.block",
                reason: "Different person",
            }),
        });
    });
});
