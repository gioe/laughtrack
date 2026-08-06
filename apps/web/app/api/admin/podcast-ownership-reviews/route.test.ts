import { beforeEach, describe, expect, it, vi } from "vitest";
import { PGlite } from "@electric-sql/pglite";
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
            upsert: vi.fn(),
        },
        comedian: {
            findUnique: vi.fn(),
        },
        podcastEpisode: {
            upsert: vi.fn(),
        },
        podcastDenyList: {
            findFirst: vi.fn(),
            findMany: vi.fn(),
            upsert: vi.fn(),
            updateMany: vi.fn(),
        },
        $transaction: vi.fn(),
    },
}));

import { GET, POST, PUT } from "./route";
import { db } from "@/lib/db";

const mockFindProfile = vi.mocked(db.userProfile.findFirst);
const mockFindCandidates = vi.mocked(db.podcastCandidateReview.findMany);
const mockFindHostships = vi.mocked(db.comedianPodcast.findMany);
const mockTransaction = vi.mocked(db.$transaction);
const mockDenyListFindFirst = vi.mocked(db.podcastDenyList.findFirst);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest(
        "http://localhost/api/admin/podcast-hostship-reviews",
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
    mockDenyListFindFirst.mockResolvedValue(null);
    mockFindHostships.mockResolvedValue([]);
});

describe("GET /api/admin/podcast-hostship-reviews", () => {
    it("requires admin access", async () => {
        mocks.auth.mockResolvedValue(null);

        const res = await GET();

        expect(res.status).toBe(401);
    });

    it("lists all candidate statuses with context", async () => {
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
                    popularity: 74,
                },
                podcast: {
                    id: 99,
                    slug: "jane-show",
                    title: "The Jane Show",
                    authorName: "Jane Comic",
                    _count: { episodes: 8 },
                    imageUrl: "https://img.example/jane.jpg",
                    websiteUrl: "https://pod.example",
                    feedUrl: "https://pod.example/feed.xml",
                    denyListEntries: [],
                },
            },
        ] as never);
        mockFindHostships.mockResolvedValue([
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
                    popularity: 74,
                },
            },
        ] as never);

        const res = await GET();
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockFindCandidates).toHaveBeenCalledWith(
            expect.not.objectContaining({
                where: { candidateStatus: "pending" },
            }),
        );
        expect(body.candidates).toEqual([
            expect.objectContaining({
                id: 12,
                comedian: {
                    id: 42,
                    name: "Jane Comic",
                    uuid: "comedian-uuid",
                    popularity: 74,
                },
                podcast: expect.objectContaining({
                    id: 99,
                    slug: "jane-show",
                    title: "The Jane Show",
                }),
                confidence: 0.91,
                evidence: { matched_name: "Jane Comic" },
                existingHostships: [
                    expect.objectContaining({
                        id: 55,
                        reviewStatus: "accepted",
                        comedian: {
                            id: 42,
                            name: "Jane Comic",
                            uuid: "comedian-uuid",
                            popularity: 74,
                        },
                    }),
                ],
            }),
        ]);
    });
});

describe("POST /api/admin/podcast-hostship-reviews", () => {
    it("rejects invalid payloads", async () => {
        const res = await POST(
            makeRequest({ podcastId: 99, hostComedianId: "hold" }),
        );

        expect(res.status).toBe(400);
    });

    it("rejects legacy owner payload fields", async () => {
        const res = await POST(
            makeRequest({ podcastId: 99, ownerComedianId: 42 }),
        );

        expect(res.status).toBe(400);
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("rejects conflicting approve and deny-list decisions", async () => {
        const res = await POST(
            makeRequest({
                podcastId: 99,
                hostComedianIds: [42],
                denyListed: true,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toBe("A deny-listed podcast cannot also have hosts");
        expect(mockTransaction).not.toHaveBeenCalled();
    });

    it("approves podcast hosts and co-hosts, rejects competing candidates, audits, and revalidates", async () => {
        const podcast = {
            id: 99,
            slug: "jane-show",
            title: "The Jane Show",
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            feedUrl: "https://pod.example/feed.xml",
        };
        const host = {
            id: 42,
            name: "Jane Comic",
            uuid: "comedian-uuid",
            visible: true,
            parentComedianId: null,
            popularity: 74,
        };
        const cohost = {
            id: 77,
            name: "Co Host",
            uuid: "comedian-uuid-77",
            visible: true,
            parentComedianId: null,
            popularity: 31,
        };
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
            comedian: {
                id: 42,
                name: "Jane Comic",
                uuid: "comedian-uuid",
                popularity: 74,
            },
            podcast,
        };
        const upsertedHostship = {
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
        const upsertedCohostship = {
            ...upsertedHostship,
            id: 89,
            comedianId: 77,
            associationType: "cohost",
        };
        const auditCreate = vi.fn();
        const podcastFindUnique = vi.fn().mockResolvedValue(podcast);
        const comedianFindUnique = vi
            .fn()
            .mockResolvedValueOnce(host)
            .mockResolvedValueOnce(cohost);
        const candidateFindMany = vi.fn().mockResolvedValue([
            candidate,
            {
                ...candidate,
                id: 13,
                comedianId: 77,
                associationType: "cohost",
                confidence: 0.72,
                comedian: cohost,
            },
        ]);
        const candidateUpdateMany = vi.fn();
        const hostshipFindMany = vi.fn().mockResolvedValue([]);
        const hostshipDeleteMany = vi.fn();
        const upsert = vi
            .fn()
            .mockResolvedValueOnce(upsertedHostship)
            .mockResolvedValueOnce(upsertedCohostship);
        const denyListFindMany = vi.fn().mockResolvedValue([]);
        const denyListUpsert = vi.fn();
        const denyListUpdateMany = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: { findUnique: podcastFindUnique },
                comedian: { findUnique: comedianFindUnique },
                podcastCandidateReview: {
                    findMany: candidateFindMany,
                    updateMany: candidateUpdateMany,
                },
                comedianPodcast: {
                    findMany: hostshipFindMany,
                    deleteMany: hostshipDeleteMany,
                    upsert,
                },
                podcastDenyList: {
                    findMany: denyListFindMany,
                    upsert: denyListUpsert,
                    updateMany: denyListUpdateMany,
                },
                $queryRaw: vi.fn().mockResolvedValue([]),
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(
            makeRequest({
                podcastId: 99,
                hostComedianIds: [42],
                cohostComedianIds: [77],
                reason: "Matches host feed",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.hostships).toEqual([
            {
                ...upsertedHostship,
                reviewedAt: "2026-05-18T12:00:00.000Z",
            },
            {
                ...upsertedCohostship,
                reviewedAt: "2026-05-18T12:00:00.000Z",
            },
        ]);
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
                    comedianId: { notIn: [42, 77] },
                }),
                data: expect.objectContaining({
                    candidateStatus: "rejected",
                    reviewedBy: "profile-1",
                }),
            }),
        );
        expect(hostshipDeleteMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    podcastId: 99,
                    reviewStatus: "accepted",
                    associationType: { in: ["host", "cohost"] },
                },
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
        expect(upsert).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    comedianId_podcastId_associationType_source: {
                        comedianId: 77,
                        podcastId: 99,
                        associationType: "cohost",
                        source: "podcast-index",
                    },
                },
            }),
        );
        expect(denyListUpsert).not.toHaveBeenCalled();
        expect(denyListUpdateMany).toHaveBeenCalledWith({
            where: { podcastId: 99, restoredAt: null },
            data: expect.objectContaining({ restoredBy: "profile-1" }),
        });
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                actorProfileId: "profile-1",
                action: "podcast_hostship_review.approve",
                entityType: "podcast",
                entityId: "99",
                reason: "Matches host feed",
            }),
        });
        expect(mocks.revalidateTag).toHaveBeenCalledWith(
            "podcasts-search-page-data-v3",
        );
        expect(mocks.revalidateTag).toHaveBeenCalledWith(
            "podcast-detail-data-v2",
        );
        expect(mocks.revalidateTag).toHaveBeenCalledWith("jane-show");
    });

    it("collapses alias and canonical selections into one canonical host with complete provenance", async () => {
        const podcast = {
            id: 99,
            slug: "canonical-show",
            title: "Canonical Show",
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            feedUrl: "https://pod.example/feed.xml",
        };
        const alias = {
            id: 42,
            name: "Stage Name",
            uuid: "alias-42",
            visible: true,
            parentComedianId: 43,
        };
        const canonical = {
            id: 43,
            name: "Canonical Comic",
            uuid: "canonical-43",
            visible: true,
            parentComedianId: null,
        };
        const candidate = {
            id: 12,
            comedianId: 42,
            podcastId: 99,
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            candidateStatus: "pending",
            associationType: "host",
            confidence: 0.91,
            evidence: { matched_name: "Stage Name" },
            reviewedAt: null,
            reviewedBy: null,
            comedian: alias,
            podcast,
        };
        const comedianFindUnique = vi
            .fn()
            .mockResolvedValueOnce(alias)
            .mockResolvedValueOnce(canonical)
            .mockResolvedValueOnce(canonical);
        const candidateUpdateMany = vi.fn();
        const hostshipDeleteMany = vi.fn();
        const hostshipUpsert = vi.fn().mockResolvedValue({
            id: 88,
            comedianId: 43,
            podcastId: 99,
            associationType: "host",
            source: "podcast-index",
            reviewStatus: "accepted",
            confidence: 0.91,
            evidence: {},
            reviewedAt: new Date("2026-05-18T12:00:00Z"),
            reviewedBy: "profile-1",
        });
        const auditCreate = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: { findUnique: vi.fn().mockResolvedValue(podcast) },
                comedian: { findUnique: comedianFindUnique },
                podcastCandidateReview: {
                    findMany: vi.fn().mockResolvedValue([candidate]),
                    updateMany: candidateUpdateMany,
                },
                comedianPodcast: {
                    findMany: vi.fn().mockResolvedValue([]),
                    deleteMany: hostshipDeleteMany,
                    upsert: hostshipUpsert,
                },
                podcastDenyList: {
                    findMany: vi.fn().mockResolvedValue([]),
                    upsert: vi.fn(),
                    updateMany: vi.fn(),
                },
                $queryRaw: vi.fn().mockResolvedValue([]),
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(
            makeRequest({
                podcastId: 99,
                hostComedianIds: [42, 43],
                cohostComedianIds: [],
            }),
        );

        expect(res.status).toBe(200);
        expect(hostshipUpsert).toHaveBeenCalledTimes(1);
        expect(hostshipUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                create: expect.objectContaining({
                    comedianId: 43,
                    evidence: {
                        matched_name: "Stage Name",
                        canonicalComedianResolution: {
                            canonicalComedianId: 43,
                            requests: [
                                {
                                    requestedComedianId: 42,
                                    aliasPath: [42, 43],
                                },
                                {
                                    requestedComedianId: 43,
                                    aliasPath: [43],
                                },
                            ],
                        },
                    },
                }),
            }),
        );
        expect(candidateUpdateMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({ comedianId: 42 }),
            }),
        );
        expect(candidateUpdateMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({ comedianId: 43 }),
            }),
        );
        expect(hostshipDeleteMany).toHaveBeenCalledWith({
            where: {
                podcastId: 99,
                reviewStatus: "accepted",
                associationType: { in: ["host", "cohost"] },
            },
        });
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                after: expect.objectContaining({
                    attributionResolutions: [
                        {
                            associationType: "host",
                            canonicalComedianId: 43,
                            requestedComedianIds: [42, 43],
                            aliasPaths: [[42, 43], [43]],
                        },
                    ],
                }),
            }),
        });
    });

    it("rejects a hidden canonical host before mutating review state", async () => {
        const candidateUpdateMany = vi.fn();
        const hostshipUpsert = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: {
                    findUnique: vi.fn().mockResolvedValue({
                        id: 99,
                        slug: "hidden-show",
                        title: "Hidden Show",
                        source: "manual",
                        sourcePodcastId: "99",
                        feedUrl: null,
                    }),
                },
                comedian: {
                    findUnique: vi.fn().mockResolvedValue({
                        id: 42,
                        name: "Hidden Comic",
                        uuid: "hidden-42",
                        visible: false,
                        parentComedianId: null,
                    }),
                },
                podcastCandidateReview: {
                    updateMany: candidateUpdateMany,
                },
                comedianPodcast: { upsert: hostshipUpsert },
                $queryRaw: vi.fn(),
            } as never),
        );

        const res = await POST(
            makeRequest({ podcastId: 99, hostComedianIds: [42] }),
        );
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.reason).toBe("hidden");
        expect(candidateUpdateMany).not.toHaveBeenCalled();
        expect(hostshipUpsert).not.toHaveBeenCalled();
    });

    it("deny-lists a podcast by rejecting pending candidates and accepted hostships", async () => {
        const podcast = {
            id: 99,
            slug: "jane-show",
            title: "The Jane Show",
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            feedUrl: "https://pod.example/feed.xml",
        };
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
            comedian: {
                id: 42,
                name: "Jane Comic",
                uuid: "comedian-uuid",
                popularity: 74,
            },
            podcast,
        };
        const auditCreate = vi.fn();
        const podcastFindUnique = vi.fn().mockResolvedValue(podcast);
        const candidateFindMany = vi.fn().mockResolvedValue([candidate]);
        const candidateUpdateMany = vi.fn();
        const hostshipFindMany = vi.fn().mockResolvedValue([]);
        const hostshipDeleteMany = vi.fn();
        const upsert = vi.fn();
        const denyListFindMany = vi.fn().mockResolvedValue([]);
        const denyListUpsert = vi.fn().mockResolvedValue({
            id: 5,
            podcastId: 99,
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            feedUrl: "https://pod.example/feed.xml",
            reason: "Not comedy",
            deniedAt: new Date("2026-05-18T12:00:00Z"),
            deniedBy: "profile-1",
        });
        const denyListUpdateMany = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: { findUnique: podcastFindUnique },
                comedian: { findUnique: vi.fn() },
                podcastCandidateReview: {
                    findMany: candidateFindMany,
                    updateMany: candidateUpdateMany,
                },
                comedianPodcast: {
                    findMany: hostshipFindMany,
                    deleteMany: hostshipDeleteMany,
                    upsert,
                },
                podcastDenyList: {
                    findMany: denyListFindMany,
                    upsert: denyListUpsert,
                    updateMany: denyListUpdateMany,
                },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(
            makeRequest({
                podcastId: 99,
                hostComedianIds: [],
                cohostComedianIds: [],
                denyListed: true,
                reason: "Not comedy",
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
        expect(hostshipDeleteMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    podcastId: 99,
                    reviewStatus: "accepted",
                    associationType: { in: ["host", "cohost"] },
                },
            }),
        );
        expect(upsert).not.toHaveBeenCalled();
        expect(denyListUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { podcastId: 99 },
                create: expect.objectContaining({
                    podcastId: 99,
                    source: "podcast-index",
                    sourcePodcastId: "feed-99",
                    deniedBy: "profile-1",
                    reason: "Not comedy",
                }),
                update: expect.objectContaining({
                    restoredAt: null,
                    restoredBy: null,
                    reason: "Not comedy",
                }),
            }),
        );
        expect(denyListUpdateMany).not.toHaveBeenCalled();
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                action: "podcast_hostship_review.deny_list",
                reason: "Not comedy",
            }),
        });
    });

    it("restores a deny-listed podcast without assigning hosts", async () => {
        const podcast = {
            id: 99,
            slug: "jane-show",
            title: "The Jane Show",
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            feedUrl: "https://pod.example/feed.xml",
        };
        const activeDenyListEntry = {
            id: 5,
            podcastId: 99,
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            feedUrl: "https://pod.example/feed.xml",
            reason: "Not comedy",
            deniedAt: new Date("2026-05-18T12:00:00Z"),
            deniedBy: "profile-2",
            restoredAt: null,
            restoredBy: null,
        };
        const auditCreate = vi.fn();
        const candidateUpdateMany = vi.fn();
        const hostshipDeleteMany = vi.fn();
        const denyListUpsert = vi.fn();
        const denyListUpdateMany = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: {
                    findUnique: vi.fn().mockResolvedValue(podcast),
                },
                comedian: { findUnique: vi.fn() },
                podcastCandidateReview: {
                    findMany: vi.fn().mockResolvedValue([]),
                    updateMany: candidateUpdateMany,
                },
                comedianPodcast: {
                    findMany: vi.fn().mockResolvedValue([]),
                    deleteMany: hostshipDeleteMany,
                    upsert: vi.fn(),
                },
                podcastDenyList: {
                    findMany: vi.fn().mockResolvedValue([activeDenyListEntry]),
                    upsert: denyListUpsert,
                    updateMany: denyListUpdateMany,
                },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(
            makeRequest({
                podcastId: 99,
                hostComedianIds: [],
                cohostComedianIds: [],
                denyListed: false,
                reason: "Restore without assigning a host",
            }),
        );

        expect(res.status).toBe(200);
        expect(denyListUpsert).not.toHaveBeenCalled();
        expect(denyListUpdateMany).toHaveBeenCalledWith({
            where: { podcastId: 99, restoredAt: null },
            data: {
                restoredAt: expect.any(Date),
                restoredBy: "profile-1",
            },
        });
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                actorProfileId: "profile-1",
                action: "podcast_hostship_review.restore",
                entityType: "podcast",
                entityId: "99",
                reason: "Restore without assigning a host",
            }),
        });
        expect(mocks.revalidateTag).toHaveBeenCalledWith(
            "podcasts-search-page-data-v3",
        );
        expect(mocks.revalidateTag).toHaveBeenCalledWith(
            "podcast-detail-data-v2",
        );
        expect(mocks.revalidateTag).toHaveBeenCalledWith("podcast-metadata");
        expect(mocks.revalidateTag).toHaveBeenCalledWith("jane-show");
    });

    it("treats an implicit no-host review as a rejected deny-list decision", async () => {
        const podcast = {
            id: 99,
            slug: "jane-show",
            title: "The Jane Show",
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            feedUrl: "https://pod.example/feed.xml",
        };
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
            comedian: {
                id: 42,
                name: "Jane Comic",
                uuid: "comedian-uuid",
                popularity: 74,
            },
            podcast,
        };
        const auditCreate = vi.fn();
        const podcastFindUnique = vi.fn().mockResolvedValue(podcast);
        const candidateFindMany = vi.fn().mockResolvedValue([candidate]);
        const candidateUpdateMany = vi.fn();
        const hostshipFindMany = vi.fn().mockResolvedValue([]);
        const hostshipDeleteMany = vi.fn();
        const denyListFindMany = vi.fn().mockResolvedValue([]);
        const denyListUpsert = vi.fn().mockResolvedValue({
            id: 5,
            podcastId: 99,
            source: "podcast-index",
            sourcePodcastId: "feed-99",
            feedUrl: "https://pod.example/feed.xml",
            reason: "No accepted host after review",
            deniedAt: new Date("2026-05-18T12:00:00Z"),
            deniedBy: "profile-1",
        });
        const denyListUpdateMany = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: { findUnique: podcastFindUnique },
                comedian: { findUnique: vi.fn() },
                podcastCandidateReview: {
                    findMany: candidateFindMany,
                    updateMany: candidateUpdateMany,
                },
                comedianPodcast: {
                    findMany: hostshipFindMany,
                    deleteMany: hostshipDeleteMany,
                    upsert: vi.fn(),
                },
                podcastDenyList: {
                    findMany: denyListFindMany,
                    upsert: denyListUpsert,
                    updateMany: denyListUpdateMany,
                },
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(
            makeRequest({
                podcastId: 99,
                hostComedianIds: [],
                cohostComedianIds: [],
                reason: "",
            }),
        );

        expect(res.status).toBe(200);
        expect(denyListUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { podcastId: 99 },
                create: expect.objectContaining({
                    podcastId: 99,
                    reason: "No accepted host after review",
                    deniedBy: "profile-1",
                }),
                update: expect.objectContaining({
                    reason: "No accepted host after review",
                    restoredAt: null,
                    restoredBy: null,
                }),
            }),
        );
        expect(denyListUpdateMany).not.toHaveBeenCalled();
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                action: "podcast_hostship_review.deny_list",
                reason: "No accepted host after review",
            }),
        });
    });
});

describe("PUT /api/admin/podcast-hostship-reviews", () => {
    it("ingests a manual RSS feed, links it to the comedian, audits, and revalidates", async () => {
        const rss = `<?xml version="1.0"?>
            <rss><channel>
                <title>Manual Jane Feed</title>
                <link>https://pod.example</link>
                <description>Jane's show</description>
                <item>
                    <title>First Episode</title>
                    <guid>episode-1</guid>
                    <link>https://pod.example/1</link>
                    <pubDate>Mon, 18 May 2026 12:00:00 GMT</pubDate>
                    <enclosure url="https://cdn.example/1.mp3" />
                </item>
            </channel></rss>`;
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                text: async () => rss,
            }),
        );

        const comedian = {
            id: 42,
            name: "Jane Comic",
            uuid: "comedian-uuid",
            visible: true,
            parentComedianId: null,
        };
        const podcast = {
            id: 99,
            slug: "manual-jane-feed-manual-rss-abc",
            title: "Manual Jane Feed",
            feedUrl: "https://feeds.example.com/jane.xml",
        };
        const auditCreate = vi.fn();
        const podcastUpsert = vi.fn().mockResolvedValue(podcast);
        const podcastUpdate = vi.fn();
        const comedianFindUnique = vi.fn().mockResolvedValue(comedian);
        const comedianPodcastDeleteMany = vi.fn();
        const comedianPodcastUpsert = vi.fn();
        const episodeQueryRaw = vi
            .fn()
            .mockResolvedValueOnce([])
            .mockResolvedValue([{ id: 123 }]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: {
                    upsert: podcastUpsert,
                    update: podcastUpdate,
                },
                comedian: { findUnique: comedianFindUnique },
                comedianPodcast: {
                    deleteMany: comedianPodcastDeleteMany,
                    upsert: comedianPodcastUpsert,
                },
                $queryRaw: episodeQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 42,
                feedUrl: "https://feeds.example.com/jane.xml",
                reason: "Confirmed manually",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.episodeCount).toBe(1);
        expect(podcastUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                create: expect.objectContaining({
                    source: "manual_rss",
                    feedUrl: "https://feeds.example.com/jane.xml",
                    title: "Manual Jane Feed",
                }),
            }),
        );
        expect(comedianPodcastUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                create: expect.objectContaining({
                    comedianId: 42,
                    podcastId: 99,
                    reviewStatus: "accepted",
                    source: "manual_rss",
                }),
            }),
        );
        expect(comedianPodcastDeleteMany).toHaveBeenCalledWith({
            where: {
                comedianId: 42,
                podcastId: 99,
                associationType: "host",
                source: { not: "manual_rss" },
                reviewStatus: "accepted",
            },
        });
        expect(episodeQueryRaw).toHaveBeenCalledTimes(2);
        const episodeQuery = episodeQueryRaw.mock.calls[1]?.[0] as {
            strings: string[];
            values: unknown[];
        };
        expect(episodeQuery.strings.join(" ")).toContain(
            "ON CONFLICT DO NOTHING",
        );
        expect(episodeQuery.strings.join(" ")).toContain("REGEXP_REPLACE");
        expect(episodeQuery.values).toContain("guid:episode-1");
        expect(episodeQuery.values).toContain("episode-1");
        expect(podcastUpdate).toHaveBeenCalledWith({
            where: { id: 99 },
            data: { lastSyncedAt: expect.any(Date) },
        });
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                action: "podcast_manual_rss.ingest",
                entityType: "podcast",
                entityId: "99",
                reason: "Confirmed manually",
            }),
        });
        expect(mocks.revalidateTag).toHaveBeenCalledWith(
            "podcasts-search-page-data-v3",
        );
        expect(mocks.revalidateTag).toHaveBeenCalledWith(
            "manual-jane-feed-manual-rss-abc",
        );
    });

    it("canonicalizes a manual RSS alias and removes accepted links across its full alias path", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                text: async () =>
                    "<rss><channel><title>Alias Feed</title></channel></rss>",
            }),
        );
        const alias = {
            id: 42,
            name: "Stage Name",
            uuid: "alias-42",
            visible: true,
            parentComedianId: 41,
        };
        const middleAlias = {
            id: 41,
            name: "Middle Name",
            uuid: "alias-41",
            visible: false,
            parentComedianId: 40,
        };
        const canonical = {
            id: 40,
            name: "Canonical Comic",
            uuid: "canonical-40",
            visible: true,
            parentComedianId: null,
        };
        const comedianFindUnique = vi
            .fn()
            .mockResolvedValueOnce(alias)
            .mockResolvedValueOnce(middleAlias)
            .mockResolvedValueOnce(canonical);
        const podcast = {
            id: 99,
            slug: "alias-feed-manual-rss-abc",
            title: "Alias Feed",
            feedUrl: "https://feeds.example.com/alias.xml",
        };
        const podcastUpsert = vi.fn().mockResolvedValue(podcast);
        const podcastUpdate = vi.fn();
        const hostshipDeleteMany = vi.fn();
        const hostshipUpsert = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: {
                    upsert: podcastUpsert,
                    update: podcastUpdate,
                },
                comedian: { findUnique: comedianFindUnique },
                comedianPodcast: {
                    deleteMany: hostshipDeleteMany,
                    upsert: hostshipUpsert,
                },
                $queryRaw: vi.fn().mockResolvedValue([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 42,
                feedUrl: "https://feeds.example.com/alias.xml",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.comedian).toEqual({
            id: 40,
            name: "Canonical Comic",
            uuid: "canonical-40",
        });
        expect(hostshipDeleteMany).toHaveBeenCalledWith({
            where: {
                podcastId: 99,
                associationType: "host",
                reviewStatus: "accepted",
                OR: [
                    {
                        comedianId: 40,
                        source: { not: "manual_rss" },
                    },
                    { comedianId: { in: [42, 41] } },
                ],
            },
        });
        expect(hostshipUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                create: expect.objectContaining({
                    comedianId: 40,
                    evidence: expect.objectContaining({
                        canonicalComedianResolution: {
                            canonicalComedianId: 40,
                            requests: [
                                {
                                    requestedComedianId: 42,
                                    aliasPath: [42, 41, 40],
                                },
                            ],
                        },
                    }),
                }),
            }),
        );
        expect(podcastUpdate).toHaveBeenCalledWith({
            where: { id: 99 },
            data: { lastSyncedAt: expect.any(Date) },
        });
    });

    it("rejects a deny-listed canonical comedian during manual RSS acceptance", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                text: async () =>
                    "<rss><channel><title>Denied Feed</title></channel></rss>",
            }),
        );
        const podcastUpsert = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: {
                    findUnique: vi.fn().mockResolvedValue({
                        id: 42,
                        name: "Denied Comic",
                        uuid: "denied-42",
                        visible: true,
                        parentComedianId: null,
                    }),
                },
                podcast: { upsert: podcastUpsert },
                $queryRaw: vi.fn().mockResolvedValue([{ denied: true }]),
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 42,
                feedUrl: "https://feeds.example.com/denied.xml",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.reason).toBe("deny_listed");
        expect(podcastUpsert).not.toHaveBeenCalled();
    });

    it("keeps a second host association when refreshing an existing feed fails", async () => {
        const rss = `<?xml version="1.0"?>
            <rss><channel>
                <title>The Shared Show</title>
                <item>
                    <title>Shared Episode</title>
                    <guid>shared-episode</guid>
                    <pubDate>Tue, 21 Jul 2026 16:00:00 GMT</pubDate>
                </item>
            </channel></rss>`;
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                text: async () => rss,
            }),
        );

        const comedianPodcastUpsert = vi.fn();
        const firstTransaction = {
            podcast: {
                upsert: vi.fn().mockResolvedValue({
                    id: 99,
                    slug: "the-shared-show-manual-rss-abc",
                    title: "The Shared Show",
                    feedUrl: "https://feeds.example.com/shared.xml",
                }),
            },
            comedian: {
                findUnique: vi.fn().mockResolvedValue({
                    id: 84,
                    name: "Second Host",
                    uuid: "second-host-uuid",
                    visible: true,
                    parentComedianId: null,
                }),
            },
            comedianPodcast: {
                deleteMany: vi.fn(),
                upsert: comedianPodcastUpsert,
            },
            $queryRaw: vi.fn().mockResolvedValue([]),
            adminActionAudit: { create: vi.fn() },
        };
        mockTransaction
            .mockImplementationOnce(async (callback) =>
                callback(firstTransaction as never),
            )
            .mockRejectedValueOnce(
                new Error(
                    "Unique constraint failed on podcast release and title",
                ),
            );
        const errorSpy = vi
            .spyOn(console, "error")
            .mockImplementation(() => undefined);

        const res = await PUT(
            makeRequest({
                comedianId: 84,
                feedUrl: "https://feeds.example.com/shared.xml",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual(
            expect.objectContaining({
                ok: true,
                episodeCount: 0,
                episodeRefreshFailed: true,
            }),
        );
        expect(comedianPodcastUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                create: expect.objectContaining({
                    comedianId: 84,
                    podcastId: 99,
                    reviewStatus: "accepted",
                }),
            }),
        );
        expect(mockTransaction).toHaveBeenCalledTimes(2);
        expect(errorSpy).toHaveBeenCalledWith(
            "Manual RSS host association saved, but episode refresh failed:",
            expect.objectContaining({
                podcastId: 99,
                comedianId: 84,
            }),
        );
        expect(mocks.revalidateTag).toHaveBeenCalledWith(
            "the-shared-show-manual-rss-abc",
        );
    });

    it("reconciles an undated legacy raw GUID without duplicating the episode", async () => {
        const pg = new PGlite();
        try {
            await pg.exec(`
                CREATE TABLE podcast_episodes (
                    id SERIAL PRIMARY KEY,
                    podcast_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    source_episode_id TEXT NOT NULL,
                    guid TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    release_date TIMESTAMPTZ,
                    episode_url TEXT,
                    audio_url TEXT,
                    external_ids JSONB NOT NULL DEFAULT '{}',
                    evidence JSONB NOT NULL DEFAULT '{}',
                    source_payload JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                CREATE UNIQUE INDEX podcast_episodes_source_episode_id_key
                    ON podcast_episodes(source, source_episode_id);
                CREATE UNIQUE INDEX podcast_episodes_unique_podcast_release_title
                    ON podcast_episodes (
                        podcast_id,
                        release_date,
                        LOWER(REGEXP_REPLACE(BTRIM(title), '^\\s*(?:(?:ep(?:isode)?|#)\\s*[0-9]+(?:\\s*[:.\\-\\)\\]]|\\s+)\\s*|[0-9]+\\s*[:.\\-\\)\\]]\\s*)', '', 'i'))
                    )
                    WHERE release_date IS NOT NULL
                      AND created_at >= TIMESTAMPTZ '2026-06-08 16:00:00+00';
                INSERT INTO podcast_episodes (
                    podcast_id,
                    source,
                    source_episode_id,
                    guid,
                    title
                )
                VALUES (
                    99,
                    'manual_rss',
                    'shared-episode',
                    'shared-episode',
                    'Shared Episode'
                );
            `);

            const rss = `<?xml version="1.0"?>
                <rss><channel>
                    <title>The Shared Show</title>
                    <item>
                        <title>Shared Episode</title>
                        <guid>shared-episode</guid>
                    </item>
                </channel></rss>`;
            vi.stubGlobal(
                "fetch",
                vi.fn().mockResolvedValue({
                    ok: true,
                    text: async () => rss,
                }),
            );

            const firstTransaction = {
                podcast: {
                    upsert: vi.fn().mockResolvedValue({
                        id: 99,
                        slug: "the-shared-show-manual-rss-abc",
                        title: "The Shared Show",
                        feedUrl: "https://feeds.example.com/shared.xml",
                    }),
                },
                comedian: {
                    findUnique: vi.fn().mockResolvedValue({
                        id: 84,
                        name: "Second Host",
                        uuid: "second-host-uuid",
                        visible: true,
                        parentComedianId: null,
                    }),
                },
                comedianPodcast: {
                    deleteMany: vi.fn(),
                    upsert: vi.fn(),
                },
                $queryRaw: vi.fn().mockResolvedValue([]),
                adminActionAudit: { create: vi.fn() },
            };
            const secondTransaction = {
                $queryRaw: async (query: { text: string; values: unknown[] }) =>
                    (await pg.query(query.text, query.values)).rows,
                podcast: { update: vi.fn() },
            };
            mockTransaction
                .mockImplementationOnce(async (callback) =>
                    callback(firstTransaction as never),
                )
                .mockImplementationOnce(async (callback) =>
                    callback(secondTransaction as never),
                );

            const res = await PUT(
                makeRequest({
                    comedianId: 84,
                    feedUrl: "https://feeds.example.com/shared.xml",
                }),
            );
            const body = await res.json();
            const episodes = await pg.query<{
                source_episode_id: string;
            }>("SELECT source_episode_id FROM podcast_episodes ORDER BY id");

            expect(res.status).toBe(200);
            expect(body).toEqual(
                expect.objectContaining({
                    ok: true,
                    episodeCount: 1,
                    episodeRefreshFailed: false,
                }),
            );
            expect(episodes.rows).toEqual([
                { source_episode_id: "shared-episode" },
            ]);
        } finally {
            await pg.close();
        }
    });

    it("rejects deny-listed feed URLs before fetching the RSS feed", async () => {
        const fetchSpy = vi.fn();
        vi.stubGlobal("fetch", fetchSpy);

        mockDenyListFindFirst.mockResolvedValue({
            id: 7,
            reason: "Not comedy",
        } as never);

        const res = await PUT(
            makeRequest({
                comedianId: 42,
                feedUrl: "https://feeds.example.com/blocked.xml",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(409);
        expect(body.error).toBe("Feed is deny-listed");
        expect(body.reason).toBe("Not comedy");
        expect(mockDenyListFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expect.objectContaining({
                    restoredAt: null,
                    OR: expect.arrayContaining([
                        { feedUrl: "https://feeds.example.com/blocked.xml" },
                        expect.objectContaining({ source: "manual_rss" }),
                    ]),
                }),
            }),
        );
        // Pre-check short-circuits before any network call or DB transaction.
        expect(fetchSpy).not.toHaveBeenCalled();
        expect(mockTransaction).not.toHaveBeenCalled();
        expect(mocks.revalidateTag).not.toHaveBeenCalled();
    });

    it("includes the manual_rss source pair in the deny-list OR clause", async () => {
        vi.stubGlobal("fetch", vi.fn());
        mockDenyListFindFirst.mockResolvedValue({
            id: 8,
            reason: null,
        } as never);

        const res = await PUT(
            makeRequest({
                comedianId: 42,
                feedUrl: "https://feeds.example.com/different.xml",
            }),
        );

        expect(res.status).toBe(409);
        const call = mockDenyListFindFirst.mock.calls[0]?.[0];
        const orClause = (call?.where as { OR: unknown[] })?.OR;
        expect(orClause).toEqual(
            expect.arrayContaining([
                {
                    source: "manual_rss",
                    sourcePodcastId: expect.any(String),
                },
            ]),
        );
        const sourcePair = orClause?.find(
            (entry): entry is { source: string; sourcePodcastId: string } =>
                typeof entry === "object" &&
                entry !== null &&
                "sourcePodcastId" in entry,
        );
        expect(sourcePair?.sourcePodcastId).toMatch(/^[0-9a-f]{40}$/);
    });

    it("proceeds when deny-list entry is restored (findFirst returns null)", async () => {
        const rss = `<?xml version="1.0"?>
            <rss><channel>
                <title>Restored Feed</title>
                <item><title>Ep</title><guid>e1</guid></item>
            </channel></rss>`;
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                text: async () => rss,
            }),
        );

        const comedian = {
            id: 42,
            name: "Jane Comic",
            uuid: "comedian-uuid",
            visible: true,
            parentComedianId: null,
        };
        const podcast = {
            id: 99,
            slug: "restored-feed-manual-rss-abc",
            title: "Restored Feed",
            feedUrl: "https://feeds.example.com/restored.xml",
        };
        const podcastUpsert = vi.fn().mockResolvedValue(podcast);
        const comedianPodcastDeleteMany = vi.fn();
        const comedianPodcastUpsert = vi.fn();
        const episodeUpsert = vi.fn();
        const auditCreate = vi.fn();
        mockDenyListFindFirst.mockResolvedValue(null);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: { upsert: podcastUpsert },
                comedian: { findUnique: vi.fn().mockResolvedValue(comedian) },
                comedianPodcast: {
                    deleteMany: comedianPodcastDeleteMany,
                    upsert: comedianPodcastUpsert,
                },
                podcastEpisode: { upsert: episodeUpsert },
                $queryRaw: vi.fn().mockResolvedValue([]),
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 42,
                feedUrl: "https://feeds.example.com/restored.xml",
            }),
        );

        expect(res.status).toBe(200);
        expect(podcastUpsert).toHaveBeenCalled();
        expect(comedianPodcastUpsert).toHaveBeenCalled();
        expect(auditCreate).toHaveBeenCalled();
    });
});
