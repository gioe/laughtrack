import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/rateLimit", () => ({
    applyPublicReadRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 60,
            remaining: 59,
            resetAt: 0,
        }),
    ),
    rateLimitHeaders: vi.fn(() => ({})),
}));
vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            findUnique: vi.fn(),
        },
    },
}));
vi.mock("@/util/imageUtil", () => ({
    buildComedianImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));

import { GET } from "./route";
import { db } from "@/lib/db";

const mockFindUnique = vi.mocked(db.comedian.findUnique);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/comedians/226475");
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("GET /api/v1/comedians/[id]", () => {
    it("returns comedian detail social data with id for the iOS OpenAPI contract", async () => {
        mockFindUnique.mockResolvedValue({
            id: 226475,
            uuid: "comedian-uuid",
            name: "Marcus D. Wiley",
            linktree: null,
            instagramAccount: null,
            instagramFollowers: null,
            tiktokAccount: null,
            tiktokFollowers: null,
            youtubeAccount: null,
            youtubeFollowers: null,
            website: "https://marcusdwiley.com/",
            popularity: 0.6,
            hasImage: false,
        });

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "226475" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.data.social_data).toMatchObject({
            id: 226475,
            website: "https://marcusdwiley.com/",
            popularity: 0.6,
        });
    });
});
