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
            popularity: 74,
        };
        const cohost = {
            id: 77,
            name: "Co Host",
            uuid: "comedian-uuid-77",
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
        const hostshipUpdateMany = vi.fn();
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
                    updateMany: hostshipUpdateMany,
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
        expect(hostshipUpdateMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    podcastId: 99,
                    reviewStatus: "accepted",
                    associationType: { in: ["host", "cohost"] },
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
        const hostshipUpdateMany = vi.fn();
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
                    updateMany: hostshipUpdateMany,
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
        expect(hostshipUpdateMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    podcastId: 99,
                    reviewStatus: "accepted",
                    associationType: { in: ["host", "cohost"] },
                },
                data: expect.objectContaining({
                    reviewStatus: "rejected",
                    reviewedBy: "profile-1",
                }),
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
        };
        const podcast = {
            id: 99,
            slug: "manual-jane-feed-manual-rss-abc",
            title: "Manual Jane Feed",
            feedUrl: "https://feeds.example.com/jane.xml",
        };
        const auditCreate = vi.fn();
        const podcastUpsert = vi.fn().mockResolvedValue(podcast);
        const comedianFindUnique = vi.fn().mockResolvedValue(comedian);
        const comedianPodcastUpsert = vi.fn();
        const episodeUpsert = vi.fn();
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: { upsert: podcastUpsert },
                comedian: { findUnique: comedianFindUnique },
                comedianPodcast: { upsert: comedianPodcastUpsert },
                podcastEpisode: { upsert: episodeUpsert },
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
        expect(episodeUpsert).toHaveBeenCalledWith(
            expect.objectContaining({
                create: expect.objectContaining({
                    title: "First Episode",
                    audioUrl: "https://cdn.example/1.mp3",
                }),
            }),
        );
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
        };
        const podcast = {
            id: 99,
            slug: "restored-feed-manual-rss-abc",
            title: "Restored Feed",
            feedUrl: "https://feeds.example.com/restored.xml",
        };
        const podcastUpsert = vi.fn().mockResolvedValue(podcast);
        const comedianPodcastUpsert = vi.fn();
        const episodeUpsert = vi.fn();
        const auditCreate = vi.fn();
        mockDenyListFindFirst.mockResolvedValue(null);
        mockTransaction.mockImplementation(async (callback) =>
            callback({
                podcast: { upsert: podcastUpsert },
                comedian: { findUnique: vi.fn().mockResolvedValue(comedian) },
                comedianPodcast: { upsert: comedianPodcastUpsert },
                podcastEpisode: { upsert: episodeUpsert },
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
