vi.mock("@/lib/admin/curation/podcastIntake", () => ({
    lockPodcastIntake: vi.fn().mockResolvedValue(undefined),
    resolvePodcastIntake: vi.fn().mockResolvedValue(null),
    podcastEpisodesAllowed: vi.fn().mockResolvedValue(true),
}));
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

import {
    podcastEpisodesAllowed,
    lockPodcastIntake,
} from "@/lib/admin/curation/podcastIntake";
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
    it("rejects malformed bulk decisions", async () => {
        expect((await POST(makeRequest({}))).status).toBe(400);
    });
    it.each([
        { podcastId: 99, hostComedianIds: [42] },
        { podcastId: 99, hostComedianIds: [] },
        { podcastId: 99, cohostComedianIds: [42] },
    ])(
        "requires a versioned relationship review instead of replacing hosts (%j)",
        async (payload) => {
            const response = await POST(makeRequest(payload));
            expect(response.status).toBe(409);
            expect(mockTransaction).not.toHaveBeenCalled();
        },
    );
    it.each([true, false])(
        "keeps explicit entity block/restore separate from host decisions (%s)",
        async (denyListed) => {
            const upsert = vi.fn(),
                updateMany = vi.fn(),
                deleteMany = vi.fn();
            mockTransaction.mockImplementation(async (fn) =>
                fn({
                    podcast: {
                        findUnique: vi
                            .fn()
                            .mockResolvedValue({
                                id: 99,
                                slug: "pod",
                                title: "Podcast",
                                source: "itunes",
                                sourcePodcastId: "99",
                                feedUrl: null,
                            }),
                    },
                    podcastDenyList: { upsert, updateMany },
                    comedianPodcast: { deleteMany },
                    podcastCandidateReview: { updateMany: vi.fn() },
                } as never),
            );
            expect(
                (
                    await POST(
                        makeRequest({
                            podcastId: 99,
                            denyListed,
                            reason: "Explicit entity decision",
                        }),
                    )
                ).status,
            ).toBe(200);
            expect(denyListed ? upsert : updateMany).toHaveBeenCalled();
            expect(deleteMany).not.toHaveBeenCalled();
        },
    );
});

describe("PUT /api/admin/podcast-hostship-reviews", () => {
    it.each([true, false])(
        "ingests manual metadata and honors episode approval=%s",
        async (approved) => {
            vi.mocked(podcastEpisodesAllowed).mockResolvedValueOnce(approved);
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
            expect(body.episodeCount).toBe(approved ? 1 : 0);
            expect(body.episodeIntakeHeld).toBe(!approved);
            expect(podcastUpsert).toHaveBeenCalledWith(
                expect.objectContaining({
                    create: expect.objectContaining({
                        source: "manual_rss",
                        feedUrl: "https://feeds.example.com/jane.xml",
                        title: "Manual Jane Feed",
                    }),
                }),
            );
            expect(comedianPodcastUpsert).not.toHaveBeenCalled();
            expect(comedianPodcastDeleteMany).not.toHaveBeenCalled();
            expect(mocks.revalidateTag).toHaveBeenCalledWith(
                "manual-jane-feed-manual-rss-abc",
            );
        },
    );

    it("preserves the canonical identity and stages a manual RSS alias without deleting host links", async () => {
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
        expect(hostshipDeleteMany).not.toHaveBeenCalled();
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

    it("retains a host proposal when refreshing an existing feed fails", async () => {
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
        expect(comedianPodcastUpsert).not.toHaveBeenCalled();
        expect(mockTransaction).toHaveBeenCalledTimes(2);
        expect(errorSpy).toHaveBeenCalledWith(
            "Manual RSS host proposal saved, but episode refresh failed:",
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
        expect(comedianPodcastUpsert).not.toHaveBeenCalled();
        expect(auditCreate).toHaveBeenCalled();
    });
});
