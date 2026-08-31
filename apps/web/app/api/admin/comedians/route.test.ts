import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        $transaction: vi.fn(),
        comedian: {
            findUnique: vi.fn(),
        },
        userProfile: {
            findFirst: vi.fn(),
        },
    },
}));

vi.mock("next/cache", () => ({
    revalidateTag: vi.fn(),
}));

vi.mock("@/lib/youtube/youtubeChannelResolver", () => ({
    resolveYouTubeChannelId: vi.fn(),
}));

vi.mock("@/lib/instagram/instagramFollowerResolver", () => ({
    resolveInstagramFollowerCount: vi.fn(),
}));

import { PATCH, POST, PUT } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";
import { resolveYouTubeChannelId } from "@/lib/youtube/youtubeChannelResolver";
import { resolveInstagramFollowerCount } from "@/lib/instagram/instagramFollowerResolver";

const mockAuth = vi.mocked(auth);
const mockTransaction = vi.mocked(db.$transaction);
const mockCurrentComedian = vi.mocked(db.comedian.findUnique);
const mockFindUserProfile = vi.mocked(db.userProfile.findFirst);
const mockResolveYouTubeChannelId = vi.mocked(resolveYouTubeChannelId);
const mockResolveInstagramFollowerCount = vi.mocked(
    resolveInstagramFollowerCount,
);

const adminSession = {
    profile: {
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    },
};

function makeRequest(body: unknown) {
    return new NextRequest("http://localhost/api/admin/comedians", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

function makeComedian(overrides: Record<string, unknown> = {}) {
    return {
        id: 2,
        uuid: "uuid-2",
        createdAt: new Date("2026-05-01T12:00:00.000Z"),
        name: "Alias Comic",
        website: null,
        websiteScrapingUrl: null,
        instagramAccount: null,
        instagramFollowers: null,
        instagramFollowersRefreshedAt: null,
        tiktokAccount: null,
        tiktokFollowers: null,
        youtubeAccount: null,
        youtubeFollowers: null,
        youtubeChannelId: null,
        linktree: null,
        hasImage: false,
        imageAssets: [],
        popularity: 12,
        totalShows: 1,
        visible: true,
        blockReason: null,
        blockAddedBy: null,
        blockAddedAt: null,
        parentComedianId: null,
        parentComedian: null,
        comedianPodcasts: [],
        lineupItems: [],
        _count: { alternativeNames: 0 },
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockResolveYouTubeChannelId.mockResolvedValue({
        status: "failed",
        reason: "not_found",
        sourceUrl: "https://www.youtube.com/@missing",
    });
    mockResolveInstagramFollowerCount.mockResolvedValue({
        status: "failed",
        detail: "unavailable",
    });
    mockFindUserProfile.mockResolvedValue({
        id: "profile-1",
        userid: "user-1",
        role: "admin",
    } as never);
    mockCurrentComedian.mockResolvedValue({ instagramAccount: null } as never);
});

describe("PATCH /api/admin/comedians", () => {
    it("requires admin access", async () => {
        mockAuth.mockResolvedValue(null as never);

        const res = await PATCH(
            makeRequest({
                action: "set-parent",
                comedianId: 2,
                parentComedianId: 1,
            }),
        );

        expect(res.status).toBe(401);
    });

    it("saves a parent relationship and writes an audit entry", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce(
                makeComedian({ id: 1, name: "Parent Comic" }),
            )
            .mockResolvedValueOnce({ parentComedianId: null })
            .mockResolvedValueOnce(
                makeComedian({
                    parentComedianId: 1,
                    parentComedian: { id: 1, name: "Parent Comic" },
                }),
            );
        const txQueryRaw = vi.fn().mockResolvedValueOnce([]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PATCH(
            makeRequest({
                action: "set-parent",
                comedianId: 2,
                parentComedianId: 1,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: { parentComedianId: 1 },
        });
        expect(body.comedian.parent).toEqual({ id: 1, name: "Parent Comic" });
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "comedian.parent.update",
                    entityType: "comedian",
                    entityId: "2",
                }),
            }),
        );
    });

    it("blocks an existing comedian through visibility", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const blockAddedAt = new Date("2026-05-19T12:00:00Z");
        const update = vi.fn().mockResolvedValue(
            makeComedian({
                visible: false,
                blockReason: "Not a comedian",
                blockAddedBy: "profile-1",
                blockAddedAt,
            }),
        );
        const findUnique = vi.fn().mockResolvedValueOnce(makeComedian());
        const txQueryRaw = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PATCH(
            makeRequest({
                action: "blocklist-add",
                comedianId: 2,
                reason: "Not a comedian",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.comedian.isBlocked).toBe(true);
        expect(body.comedian.blockReason).toBe("Not a comedian");
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: {
                visible: false,
                blockReason: "Not a comedian",
                blockAddedBy: "profile-1",
                blockAddedAt: expect.any(Date),
            },
            select: expect.any(Object),
        });
        expect(txQueryRaw).not.toHaveBeenCalled();
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "comedian.visibility.block",
                    entityType: "comedian",
                    entityId: "2",
                }),
            }),
        );
    });

    it("unblocks an existing comedian through visibility", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const blocked = makeComedian({
            visible: false,
            blockReason: "Not a comedian",
            blockAddedBy: "profile-1",
            blockAddedAt: new Date("2026-05-19T12:00:00Z"),
        });
        const update = vi.fn().mockResolvedValue(
            makeComedian({
                visible: true,
                blockReason: "Not a comedian",
                blockAddedBy: "profile-1",
                blockAddedAt: new Date("2026-05-19T12:00:00Z"),
            }),
        );
        const findUnique = vi.fn().mockResolvedValueOnce(blocked);
        const txQueryRaw = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PATCH(
            makeRequest({
                action: "blocklist-remove",
                comedianId: 2,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.comedian.isBlocked).toBe(false);
        expect(body.comedian.blockReason).toBeNull();
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: { visible: true },
            select: expect.any(Object),
        });
        expect(txQueryRaw).not.toHaveBeenCalled();
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "comedian.visibility.unblock",
                    entityType: "comedian",
                    entityId: "2",
                }),
            }),
        );
    });

    it("accepts one podcast host source and rejects existing accepted duplicates", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const candidateUpdate = vi.fn();
        const hostshipDeleteMany = vi.fn();
        const hostshipUpsert = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce({
                id: 2,
                name: "Alias Comic",
                uuid: "uuid-2",
                visible: true,
                parentComedianId: null,
            })
            .mockResolvedValueOnce(
                makeComedian({
                    comedianPodcasts: [
                        {
                            associationType: "host",
                            source: "itunes",
                            reviewStatus: "accepted",
                            confidence: 0.97,
                            podcast: {
                                id: 99,
                                slug: "wild-ride-with-steve-o",
                                title: "Wild Ride! with Steve-O",
                                feedUrl: null,
                                websiteUrl: null,
                            },
                        },
                    ],
                }),
            );
        const reviewFindUnique = vi.fn().mockResolvedValueOnce({
            id: 1001,
            comedianId: 2,
            podcastId: 99,
            source: "itunes",
            sourcePodcastId: "1503236243",
            candidateStatus: "pending",
            associationType: "host",
            confidence: 0.97,
            evidence: { matched_name: "Steve-O" },
            podcast: {
                id: 99,
                slug: "wild-ride-with-steve-o",
                title: "Wild Ride! with Steve-O",
                source: "itunes",
                sourcePodcastId: "1503236243",
                feedUrl: null,
            },
        });
        const txQueryRaw = vi.fn().mockResolvedValue([]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique },
                comedianPodcast: {
                    deleteMany: hostshipDeleteMany,
                    upsert: hostshipUpsert,
                },
                podcastCandidateReview: {
                    findUnique: reviewFindUnique,
                    update: candidateUpdate,
                },
                podcastDenyList: { upsert: vi.fn() },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PATCH(
            makeRequest({
                action: "podcast-review-accept-host",
                comedianId: 2,
                candidateReviewId: 1001,
            }),
        );

        expect(res.status).toBe(200);
        expect(hostshipDeleteMany).toHaveBeenCalledWith({
            where: {
                comedianId: 2,
                podcastId: 99,
                associationType: "host",
                source: { not: "itunes" },
                reviewStatus: "accepted",
            },
        });
        expect(hostshipUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    comedianId_podcastId_associationType_source: {
                        comedianId: 2,
                        podcastId: 99,
                        associationType: "host",
                        source: "itunes",
                    },
                },
                create: expect.objectContaining({
                    reviewStatus: "accepted",
                }),
                update: expect.objectContaining({
                    reviewStatus: "accepted",
                }),
            }),
        );
    });

    it("accepts an alias review on the canonical comedian and reports both identities", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const before = makeComedian({
            id: 2,
            name: "Stage Name",
            uuid: "alias-2",
            parentComedianId: 1,
            parentComedian: { id: 1, name: "Canonical Comic" },
        });
        const after = makeComedian({
            id: 2,
            name: "Stage Name",
            uuid: "alias-2",
            parentComedianId: 1,
            parentComedian: { id: 1, name: "Canonical Comic" },
        });
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(before)
            .mockResolvedValueOnce({
                id: 2,
                name: "Stage Name",
                uuid: "alias-2",
                visible: true,
                parentComedianId: 1,
            })
            .mockResolvedValueOnce({
                id: 1,
                name: "Canonical Comic",
                uuid: "canonical-1",
                visible: true,
                parentComedianId: null,
            })
            .mockResolvedValueOnce(after);
        const reviewFindUnique = vi.fn().mockResolvedValue({
            id: 1001,
            comedianId: 2,
            podcastId: 99,
            source: "itunes",
            sourcePodcastId: "1503236243",
            candidateStatus: "pending",
            associationType: "host",
            confidence: 0.97,
            evidence: { matched_name: "Stage Name" },
            podcast: {
                id: 99,
                slug: "canonical-show",
                title: "Canonical Show",
                source: "itunes",
                sourcePodcastId: "1503236243",
                feedUrl: null,
            },
        });
        const candidateUpdate = vi.fn();
        const hostshipDeleteMany = vi.fn();
        const hostshipUpsert = vi.fn();
        const auditCreate = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique },
                comedianPodcast: {
                    deleteMany: hostshipDeleteMany,
                    upsert: hostshipUpsert,
                },
                podcastCandidateReview: {
                    findUnique: reviewFindUnique,
                    update: candidateUpdate,
                },
                podcastDenyList: { upsert: vi.fn() },
                $queryRaw: vi.fn().mockResolvedValue([]),
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PATCH(
            makeRequest({
                action: "podcast-review-accept-host",
                comedianId: 2,
                candidateReviewId: 1001,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.comedian.id).toBe(2);
        expect(body.attributionComedian).toEqual({
            id: 1,
            name: "Canonical Comic",
            uuid: "canonical-1",
        });
        expect(hostshipDeleteMany).toHaveBeenCalledWith({
            where: {
                podcastId: 99,
                associationType: "host",
                reviewStatus: "accepted",
                OR: [
                    {
                        comedianId: 1,
                        source: { not: "itunes" },
                    },
                    { comedianId: { in: [2] } },
                ],
            },
        });
        expect(hostshipUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                create: expect.objectContaining({
                    comedianId: 1,
                    evidence: {
                        matched_name: "Stage Name",
                        canonicalComedianResolution: {
                            canonicalComedianId: 1,
                            requests: [
                                {
                                    requestedComedianId: 2,
                                    aliasPath: [2, 1],
                                },
                            ],
                        },
                    },
                }),
            }),
        );
        expect(auditCreate).toHaveBeenCalledWith({
            data: expect.objectContaining({
                after: expect.objectContaining({
                    attributionComedian: {
                        id: 1,
                        name: "Canonical Comic",
                        uuid: "canonical-1",
                    },
                    attributionAliasPath: [2, 1],
                }),
            }),
        });
    });

    it("rejects a deny-listed canonical comedian before accepting its review", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce({
                id: 2,
                name: "Denied Comic",
                uuid: "uuid-2",
                visible: true,
                parentComedianId: null,
            });
        const candidateUpdate = vi.fn();
        const hostshipUpsert = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique },
                comedianPodcast: {
                    deleteMany: vi.fn(),
                    upsert: hostshipUpsert,
                },
                podcastCandidateReview: {
                    findUnique: vi.fn().mockResolvedValue({
                        id: 1001,
                        comedianId: 2,
                        podcastId: 99,
                        source: "itunes",
                        sourcePodcastId: "1503236243",
                        candidateStatus: "pending",
                        associationType: "host",
                        confidence: 0.97,
                        evidence: {},
                        podcast: {
                            id: 99,
                            slug: "denied-show",
                            title: "Denied Show",
                            source: "itunes",
                            sourcePodcastId: "1503236243",
                            feedUrl: null,
                        },
                    }),
                    update: candidateUpdate,
                },
                $queryRaw: vi.fn().mockResolvedValue([{ denied: true }]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PATCH(
            makeRequest({
                action: "podcast-review-accept-host",
                comedianId: 2,
                candidateReviewId: 1001,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.reason).toBe("deny_listed");
        expect(candidateUpdate).not.toHaveBeenCalled();
        expect(hostshipUpsert).not.toHaveBeenCalled();
    });
});

describe("POST /api/admin/comedians", () => {
    it("creates a comedian with the required name and writes an audit entry", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const create = vi.fn().mockResolvedValue(
            makeComedian({
                id: 7,
                name: "New Comic",
                uuid: "a9c922c2baff2c5e9ac9b607ddb34c65",
            }),
        );
        const findUnique = vi.fn().mockResolvedValueOnce(null);
        const txQueryRaw = vi.fn().mockResolvedValueOnce([]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { create, findUnique },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await POST(makeRequest({ name: " New   Comic " }));
        const body = await res.json();

        expect(res.status).toBe(201);
        expect(create).toHaveBeenCalledWith({
            data: {
                name: "New Comic",
                uuid: "a9c922c2baff2c5e9ac9b607ddb34c65",
            },
            select: expect.any(Object),
        });
        expect(body.comedian.name).toBe("New Comic");
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "comedian.create",
                    entityType: "comedian",
                    entityId: "7",
                }),
            }),
        );
    });

    it("rejects comedian creation when the generated uuid already exists", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const create = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce({ id: 4, name: "New Comic" });
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { create, findUnique },
                $queryRaw: vi.fn(),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await POST(makeRequest({ name: "New Comic" }));
        const body = await res.json();

        expect(res.status).toBe(409);
        expect(body.error).toContain("Generated UUID already belongs to");
        expect(create).not.toHaveBeenCalled();
    });

    it("rejects creation while the name has an orphan block", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const create = vi.fn();
        const findUnique = vi.fn().mockResolvedValueOnce(null);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { create, findUnique },
                $queryRaw: vi.fn().mockResolvedValueOnce([
                    {
                        name: "Open Mic",
                        reason: "event title",
                        added_by: "profile-1",
                        deleted_at: new Date(),
                    },
                ]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await POST(makeRequest({ name: "Open Mic" }));

        expect(res.status).toBe(409);
        expect(create).not.toHaveBeenCalled();
    });
});

describe("PUT /api/admin/comedians", () => {
    it("updates a comedian name and regenerates the MD5 uuid", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(
                makeComedian({
                    name: "tig notaro",
                    uuid: "old-uuid",
                }),
            )
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    name: "Tig Notaro",
                    uuid: "08ab8a743efbbf7f64a6bc0b8b0c3eaf",
                }),
            );
        const txQueryRaw = vi.fn().mockResolvedValueOnce([]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: " Tig   Notaro ",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: {
                name: "Tig Notaro",
                uuid: "08ab8a743efbbf7f64a6bc0b8b0c3eaf",
            },
        });
        expect(body.comedian.name).toBe("Tig Notaro");
        expect(body.comedian.uuid).toBe("08ab8a743efbbf7f64a6bc0b8b0c3eaf");
        expect(auditCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    action: "comedian.update",
                    entityType: "comedian",
                    entityId: "2",
                }),
            }),
        );
    });

    it("updates comedian website fields", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const auditCreate = vi.fn();
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    website: "https://alias.example.com",
                    websiteScrapingUrl: "https://alias.example.com/tour",
                }),
            );
        const txQueryRaw = vi.fn().mockResolvedValueOnce([]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                website: " https://alias.example.com ",
                websiteScrapingUrl: " https://alias.example.com/tour ",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: {
                name: "Alias Comic",
                uuid: "3e19dd3064b1dc0cf4e7d69d7f5cb762",
                website: "https://alias.example.com",
                websiteScrapingUrl: "https://alias.example.com/tour",
            },
        });
        expect(body.comedian.website).toBe("https://alias.example.com");
        expect(body.comedian.websiteScrapingUrl).toBe(
            "https://alias.example.com/tour",
        );
    });

    it("refreshes and persists Instagram followers when the handle changes", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockResolveInstagramFollowerCount.mockResolvedValueOnce({
            status: "resolved",
            followerCount: 123_456,
        });
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    instagramAccount: "aliascomic",
                    instagramFollowers: 123_456,
                    instagramFollowersRefreshedAt: new Date(
                        "2026-07-21T12:00:00.000Z",
                    ),
                }),
            );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn().mockResolvedValueOnce([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                instagramAccount: "@aliascomic",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockResolveInstagramFollowerCount).toHaveBeenCalledWith(
            "aliascomic",
        );
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: expect.objectContaining({
                instagramAccount: "aliascomic",
                instagramFollowers: 123_456,
                instagramFollowersRefreshedAt: expect.any(Date),
            }),
        });
        expect(body.comedian.instagramFollowers).toBe(123_456);
        expect(body.instagramFollowerRefresh).toEqual({
            status: "resolved",
            followerCount: 123_456,
        });
    });

    it("proactively refreshes an unchanged Instagram handle and updates popularity", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockCurrentComedian.mockResolvedValueOnce({
            instagramAccount: "aliascomic",
        } as never);
        mockResolveInstagramFollowerCount.mockResolvedValueOnce({
            status: "resolved",
            followerCount: 5_000_000,
        });
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(
                makeComedian({
                    instagramAccount: "aliascomic",
                    popularity: 0.2,
                }),
            )
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    instagramAccount: "aliascomic",
                    instagramFollowers: 5_000_000,
                    instagramFollowersRefreshedAt: new Date(
                        "2026-07-22T12:00:00.000Z",
                    ),
                    popularity: 0.4,
                }),
            );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn().mockResolvedValueOnce([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                instagramAccount: "aliascomic",
                refreshInstagramFollowers: true,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockResolveInstagramFollowerCount).toHaveBeenCalledWith(
            "aliascomic",
        );
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: expect.objectContaining({
                instagramAccount: "aliascomic",
                instagramFollowers: 5_000_000,
                instagramFollowersRefreshedAt: expect.any(Date),
                popularity: 0.4,
            }),
        });
        expect(body.comedian.popularity).toBe(0.4);
        expect(body.instagramFollowerRefresh).toEqual({
            status: "resolved",
            followerCount: 5_000_000,
        });
    });

    it("preserves follower data and popularity when an unchanged proactive refresh fails", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockCurrentComedian.mockResolvedValueOnce({
            instagramAccount: "aliascomic",
        } as never);
        const refreshedAt = new Date("2026-07-20T12:00:00.000Z");
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(
                makeComedian({
                    website: null,
                    instagramAccount: "aliascomic",
                    instagramFollowers: 500,
                    instagramFollowersRefreshedAt: refreshedAt,
                    popularity: 0.3,
                }),
            )
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    website: "https://alias.example.com",
                    instagramAccount: "aliascomic",
                    instagramFollowers: 500,
                    instagramFollowersRefreshedAt: refreshedAt,
                    popularity: 0.3,
                }),
            );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn().mockResolvedValueOnce([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                website: "https://alias.example.com",
                instagramAccount: "aliascomic",
                refreshInstagramFollowers: true,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        const updateData = update.mock.calls[0]?.[0]?.data;
        expect(updateData).toEqual(
            expect.objectContaining({
                website: "https://alias.example.com",
                instagramAccount: "aliascomic",
            }),
        );
        expect(updateData).not.toHaveProperty("instagramFollowers");
        expect(updateData).not.toHaveProperty("instagramFollowersRefreshedAt");
        expect(updateData).not.toHaveProperty("popularity");
        expect(body.comedian.instagramFollowers).toBe(500);
        expect(body.comedian.popularity).toBe(0.3);
        expect(body.instagramFollowerRefresh).toEqual({
            status: "failed",
            detail: "unavailable",
        });
    });

    it("skips proactive refresh when no Instagram handle is present", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(makeComedian());
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn().mockResolvedValueOnce([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                instagramAccount: null,
                refreshInstagramFollowers: true,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockResolveInstagramFollowerCount).not.toHaveBeenCalled();
        expect(body.instagramFollowerRefresh).toBeNull();
    });

    it("clears stale Instagram followers when a changed handle cannot be refreshed", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockCurrentComedian.mockResolvedValueOnce({
            instagramAccount: "oldhandle",
        } as never);
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(
                makeComedian({
                    instagramAccount: "oldhandle",
                    instagramFollowers: 500,
                    instagramFollowersRefreshedAt: new Date(),
                }),
            )
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({ instagramAccount: "newhandle" }),
            );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn().mockResolvedValueOnce([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                instagramAccount: "newhandle",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: expect.objectContaining({
                instagramAccount: "newhandle",
                instagramFollowers: null,
                instagramFollowersRefreshedAt: null,
            }),
        });
        expect(body.instagramFollowerRefresh.status).toBe("failed");
    });

    it("resolves a YouTube channel ID when a YouTube account is saved without one", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockResolveYouTubeChannelId.mockResolvedValueOnce({
            status: "resolved",
            channelId: "UC-resolved-channel",
            sourceUrl: "https://www.youtube.com/@AliasComic",
        });
        const auditCreate = vi.fn();
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    youtubeAccount: "AliasComic",
                    youtubeChannelId: "UC-resolved-channel",
                }),
            );
        const txQueryRaw = vi.fn().mockResolvedValueOnce([]);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: txQueryRaw,
                adminActionAudit: { create: auditCreate },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                youtubeAccount: "@AliasComic",
                youtubeChannelId: null,
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockResolveYouTubeChannelId).toHaveBeenCalledWith("AliasComic");
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: expect.objectContaining({
                youtubeAccount: "AliasComic",
                youtubeChannelId: "UC-resolved-channel",
            }),
        });
        expect(body.comedian.youtubeChannelId).toBe("UC-resolved-channel");
    });

    it("preserves an explicit YouTube channel ID instead of resolving over it", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(
                makeComedian({
                    youtubeAccount: "old-account",
                    youtubeChannelId: "UC-manual-channel",
                }),
            )
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    youtubeAccount: "AliasComic",
                    youtubeChannelId: "UC-manual-channel",
                }),
            );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn().mockResolvedValueOnce([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                youtubeAccount: "@AliasComic",
                youtubeChannelId: "UC-manual-channel",
            }),
        );

        expect(res.status).toBe(200);
        expect(mockResolveYouTubeChannelId).not.toHaveBeenCalled();
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: expect.objectContaining({
                youtubeAccount: "AliasComic",
                youtubeChannelId: "UC-manual-channel",
            }),
        });
    });

    it("clears an existing YouTube channel ID when the admin empties it", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(
                makeComedian({
                    youtubeAccount: "AliasComic",
                    youtubeChannelId: "UC-manual-channel",
                }),
            )
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({
                    youtubeAccount: "AliasComic",
                    youtubeChannelId: null,
                }),
            );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn().mockResolvedValueOnce([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                youtubeAccount: "@AliasComic",
                youtubeChannelId: null,
            }),
        );

        expect(res.status).toBe(200);
        expect(mockResolveYouTubeChannelId).not.toHaveBeenCalled();
        expect(update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: expect.objectContaining({
                youtubeAccount: "AliasComic",
                youtubeChannelId: null,
            }),
        });
    });

    it("does not write a channel ID when YouTube account resolution fails", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        mockResolveYouTubeChannelId.mockResolvedValueOnce({
            status: "failed",
            reason: "not_found",
            sourceUrl: "https://www.youtube.com/@AliasComic",
        });
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce(null)
            .mockResolvedValueOnce(
                makeComedian({ youtubeAccount: "AliasComic" }),
            );
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn().mockResolvedValueOnce([]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Alias Comic",
                youtubeAccount: "@AliasComic",
                youtubeChannelId: null,
            }),
        );

        expect(res.status).toBe(200);
        const updateArgs = update.mock.calls[0]?.[0];
        expect(updateArgs).toMatchObject({ where: { id: 2 } });
        expect(updateArgs.data).not.toHaveProperty("youtubeChannelId");
    });

    it("rejects updates that would collide with another comedian uuid", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce({ id: 9, name: "Tig Notaro" });
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn(),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(
            makeRequest({
                comedianId: 2,
                name: "Tig Notaro",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(409);
        expect(body.error).toContain("Generated UUID already belongs to");
        expect(update).not.toHaveBeenCalled();
    });

    it("rejects a rename while the destination name has an orphan block", async () => {
        mockAuth.mockResolvedValue(adminSession as never);
        const update = vi.fn();
        const findUnique = vi
            .fn()
            .mockResolvedValueOnce(makeComedian())
            .mockResolvedValueOnce(null);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                comedian: { findUnique, update },
                $queryRaw: vi.fn().mockResolvedValueOnce([
                    {
                        name: "Open Mic",
                        reason: "event title",
                        added_by: "profile-1",
                        deleted_at: new Date(),
                    },
                ]),
                adminActionAudit: { create: vi.fn() },
            } as never),
        );

        const res = await PUT(makeRequest({ comedianId: 2, name: "Open Mic" }));

        expect(res.status).toBe(409);
        expect(update).not.toHaveBeenCalled();
    });
});
