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
        club: {
            findUnique: vi.fn(),
        },
    },
}));
vi.mock("@/lib/data/club/detail/findSiblingClubs", () => ({
    findSiblingClubs: vi.fn(),
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubHeroImageUrl: vi.fn((path?: string | null) =>
        path ? `https://cdn.example.com/${path}` : "",
    ),
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));

import { GET } from "./route";
import { db } from "@/lib/db";
import { findSiblingClubs } from "@/lib/data/club/detail/findSiblingClubs";
import { rateLimitHeaders } from "@/lib/rateLimit";
import { buildClubHeroImageUrl } from "@/util/imageUtil";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";
import { expectOpenApiResponse } from "@/test/openapiResponseValidator";

const mockFindUnique = vi.mocked(db.club.findUnique);
const mockFindSiblingClubs = vi.mocked(findSiblingClubs);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);
const mockBuildClubHeroImageUrl = vi.mocked(buildClubHeroImageUrl);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/clubs/7");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
    mockFindSiblingClubs.mockResolvedValue([]);
});

describe("GET /api/v1/clubs/[id]", () => {
    it("returns club detail data matching the iOS OpenAPI contract", async () => {
        mockFindUnique.mockResolvedValue({
            id: 7,
            name: "Comedy Cellar",
            website: "https://www.comedycellar.com/",
            address: "117 Macdougal St",
            zipCode: "10012",
            phoneNumber: "212-254-3480",
            chainId: 2,
            hasImage: true,
            imageAssets: [{ heroPath: "clubs/Comedy%20Cellar-hero.jpg" }],
        } as never);
        mockFindSiblingClubs.mockResolvedValue([
            {
                id: 8,
                name: "Village Underground",
                city: "New York",
                state: "NY",
                imageUrl: "https://cdn.example.com/Village Underground.jpg",
            },
        ]);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockFindUnique).toHaveBeenCalledWith(
            expect.objectContaining({
                select: expect.objectContaining({
                    imageAssets: {
                        where: { isActive: true },
                        orderBy: { publishedAt: "desc" },
                        take: 1,
                        select: { heroPath: true },
                    },
                }),
            }),
        );
        expect(mockBuildClubHeroImageUrl).toHaveBeenCalledWith(
            "clubs/Comedy%20Cellar-hero.jpg",
        );
        expect(body.data.heroImageUrl).toBe(
            "https://cdn.example.com/clubs/Comedy%20Cellar-hero.jpg",
        );
        expect(body.data.relatedVenues).toEqual([
            {
                id: 8,
                name: "Village Underground",
                city: "New York",
                state: "NY",
                imageUrl: "https://cdn.example.com/Village Underground.jpg",
            },
        ]);
        expect(mockFindSiblingClubs).toHaveBeenCalledWith(2, 7);
        expectOpenApiResponse("/clubs/{id}", 200, body);
    });

    it("returns an empty heroImageUrl when the club has no active hero asset", async () => {
        mockFindUnique.mockResolvedValue({
            id: 7,
            name: "Comedy Cellar",
            website: "https://www.comedycellar.com/",
            address: "117 Macdougal St",
            zipCode: "10012",
            phoneNumber: "212-254-3480",
            chainId: null,
            hasImage: true,
            imageAssets: [{ heroPath: null }],
        } as never);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockBuildClubHeroImageUrl).toHaveBeenCalledWith(null);
        expect(body.data.heroImageUrl).toBe("");
        expectOpenApiResponse("/clubs/{id}", 200, body);
    });

    it("marks the public 200 response shared-cacheable (public + s-maxage) alongside rate-limit headers", async () => {
        mockFindUnique.mockResolvedValue({
            id: 7,
            name: "Comedy Cellar",
            website: "https://www.comedycellar.com/",
            address: "117 Macdougal St",
            zipCode: "10012",
            phoneNumber: "212-254-3480",
            chainId: null,
            hasImage: true,
            imageAssets: [],
        } as never);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });

        expect(res.status).toBe(200);
        const cacheControl = res.headers.get("Cache-Control");
        expect(cacheControl).toContain("public");
        expect(cacheControl).toContain("s-maxage=3600");
        expect(cacheControl).toContain("stale-while-revalidate");
        // Public reads must not be marked private, and rate-limit headers survive the merge.
        expect(cacheControl).not.toContain("private");
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });

    it("does NOT cache the 500 error response", async () => {
        mockFindUnique.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });

        expect(res.status).toBe(500);
        // Error responses carry rate-limit headers but no cache directive at all,
        // so a transient failure is never stored and re-served by the CDN.
        expect(res.headers.get("Cache-Control")).toBeNull();
    });

    it("returns 500 with rate-limit headers when the detail lookup fails unexpectedly", async () => {
        mockFindUnique.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch club" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
