import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            findMany: vi.fn(),
        },
        $queryRaw: vi.fn(),
    },
}));

vi.mock("@/lib/data/comedian/imageAssets", () => ({
    buildComedianImageAssetUrl: vi.fn(
        (path: string) => `https://cdn.test/${path}`,
    ),
    buildComedianImageUrls: vi.fn(() => ({
        imageUrl: "",
        avatarUrl: "",
        heroUrl: "",
    })),
}));

import { listAdminComedians } from "./comedianManagement";
import { db } from "@/lib/db";

const mockFindMany = vi.mocked(db.comedian.findMany);
const mockQueryRaw = vi.mocked(db.$queryRaw);

function comedianRow(name: string, overrides: Record<string, unknown> = {}) {
    return {
        id: 1,
        uuid: "uuid-1",
        createdAt: new Date("2026-05-01T12:00:00.000Z"),
        name,
        website: null,
        websiteScrapingUrl: null,
        hasImage: false,
        imageAssets: [],
        popularity: 0,
        totalShows: 0,
        visible: true,
        blockReason: null,
        blockAddedBy: null,
        blockAddedAt: null,
        instagramAccount: null,
        instagramFollowers: null,
        instagramFollowersRefreshedAt: null,
        tiktokAccount: null,
        youtubeAccount: null,
        youtubeChannelId: null,
        youtubeLiveFeedEnabled: true,
        youtubeLiveNotificationsEnabled: false,
        youtubeWebSubSubscriptions: [
            {
                status: "subscribed",
                leaseExpiresAt: new Date("2026-07-05T00:00:00.000Z"),
                lastSubscribeError: null,
            },
        ],
        youtubeWebSubEvents: [
            {
                eventStatus: "received",
                receivedAt: new Date("2026-06-29T00:00:00.000Z"),
            },
        ],
        linktree: null,
        parentComedian: null,
        comedianPodcasts: [],
        podcastCandidateReviews: [],
        lineupItems: [],
        _count: { alternativeNames: 0 },
        ...overrides,
    };
}

describe("listAdminComedians", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("derives block state from comedian visibility metadata", async () => {
        mockFindMany.mockResolvedValueOnce([
            comedianRow("🔥👀\u00a0TEASE ME TUESDAYS…👀🔥", {
                visible: false,
                blockReason: "not a comic",
                blockAddedBy: "admin",
                blockAddedAt: new Date("2026-05-24T13:56:11.706Z"),
            }),
        ] as never);
        mockQueryRaw.mockResolvedValueOnce([
            {
                name: "Unrelated Open Mic",
                reason: "orphan title",
                added_by: "admin",
                deleted_at: new Date("2026-05-24T13:56:11.706Z"),
            },
        ] as never);

        const result = await listAdminComedians();

        expect(result.comedians[0]).toMatchObject({
            name: "🔥👀\u00a0TEASE ME TUESDAYS…👀🔥",
            createdAt: "2026-05-01T12:00:00.000Z",
            isBlocked: true,
            blockReason: "not a comic",
        });
    });

    it("only requests pending podcast candidate reviews", async () => {
        mockFindMany.mockResolvedValueOnce([
            comedianRow("Pending Comic"),
        ] as never);
        mockQueryRaw.mockResolvedValueOnce([] as never);

        await listAdminComedians();

        expect(mockFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                select: expect.objectContaining({
                    instagramFollowers: true,
                    instagramFollowersRefreshedAt: true,
                    youtubeLiveFeedEnabled: true,
                    youtubeLiveNotificationsEnabled: true,
                    youtubeWebSubSubscriptions: expect.objectContaining({
                        take: 1,
                    }),
                    youtubeWebSubEvents: expect.objectContaining({
                        take: 1,
                    }),
                    podcastCandidateReviews: expect.objectContaining({
                        where: { candidateStatus: "pending" },
                    }),
                    comedianPodcasts: expect.objectContaining({
                        where: { reviewStatus: "accepted" },
                    }),
                }),
            }),
        );
    });

    it("maps YouTube WebSub state onto comedian rows", async () => {
        mockFindMany.mockResolvedValueOnce([
            comedianRow("WebSub Comic"),
        ] as never);
        mockQueryRaw.mockResolvedValueOnce([] as never);

        const result = await listAdminComedians();

        expect(result.comedians[0]).toMatchObject({
            youtubeLiveFeedEnabled: true,
            youtubeLiveNotificationsEnabled: false,
            subscriptionStatus: "subscribed",
            leaseExpiresAt: "2026-07-05T00:00:00.000Z",
            lastSubscribeError: null,
            recentEventStatus: "received",
            recentEventAt: "2026-06-29T00:00:00.000Z",
        });
    });
});
