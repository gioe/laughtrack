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
    rateLimitHeaders: vi.fn(),
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
import { rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockFindUnique = vi.mocked(db.comedian.findUnique);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/comedians/226475");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/comedians/[id]", () => {
    it("returns comedian detail social data with id for the iOS OpenAPI contract", async () => {
        mockFindUnique.mockResolvedValue({
            id: 226475,
            uuid: "comedian-uuid",
            name: "Marcus D. Wiley",
            totalShows: 0,
            soldOutShows: 0,
            linktree: null,
            songkickId: null,
            bandsintownId: null,
            instagramAccount: null,
            instagramFollowers: null,
            tiktokAccount: null,
            tiktokFollowers: null,
            youtubeAccount: null,
            youtubeFollowers: null,
            website: "https://marcusdwiley.com/",
            websiteDiscoverySource: null,
            websiteLastScraped: null,
            websiteScrapeStrategy: null,
            websiteScrapingUrl: null,
            websiteConfidence: null,
            websiteScrapingUrlConfidence: null,
            popularity: 0.6,
            hasImage: false,
            bio: null,
            parentComedianId: null,
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

    it("returns 500 with rate-limit headers when the detail lookup fails unexpectedly", async () => {
        mockFindUnique.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "226475" }),
        });
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch comedian" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
