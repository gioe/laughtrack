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

function comedianRow(name: string) {
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
        parentComedian: null,
        comedianPodcasts: [],
        lineupItems: [],
        _count: { alternativeNames: 0 },
    };
}

describe("listAdminComedians", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("matches deny-list rows when internal whitespace differs", async () => {
        mockFindMany.mockResolvedValueOnce([
            comedianRow("🔥👀\u00a0TEASE ME TUESDAYS…👀🔥"),
        ] as never);
        mockQueryRaw.mockResolvedValueOnce([
            {
                name: "🔥👀 TEASE ME TUESDAYS…👀🔥",
                reason: "not a comic",
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
});
