import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

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
vi.mock("@/lib/data/club/detail/findClubHighlights", () => ({
    findClubHighlights: vi.fn(),
}));

import { GET } from "./route";
import { findClubHighlights } from "@/lib/data/club/detail/findClubHighlights";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { expectOpenApiResponse } from "@/test/openapiResponseValidator";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockFindClubHighlights = vi.mocked(findClubHighlights);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest() {
    return new NextRequest("http://localhost/api/v1/clubs/7/highlights");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockApplyPublicReadRateLimit.mockResolvedValue({
        allowed: true,
        limit: 60,
        remaining: 59,
        resetAt: 0,
    });
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
    mockFindClubHighlights.mockResolvedValue({
        tonightShows: [],
        nextShow: null,
        frequentPerformers: [],
    });
});

describe("GET /api/v1/clubs/[id]/highlights", () => {
    it("returns tonight, next-show, and frequent-performer data matching the shared OpenAPI contract", async () => {
        const tonightShow = {
            id: 11,
            clubId: 7,
            date: new Date("2026-07-30T00:00:00.000Z"),
            imageUrl: "https://cdn.example.com/show.jpg",
        };
        const nextShow = {
            id: 12,
            clubId: 7,
            date: new Date("2026-07-31T00:00:00.000Z"),
            imageUrl: "https://cdn.example.com/next.jpg",
        };
        mockFindClubHighlights.mockResolvedValue({
            tonightShows: [tonightShow],
            nextShow,
            frequentPerformers: [
                {
                    id: 3,
                    uuid: "performer-3",
                    name: "Performer Three",
                    imageUrl: "https://cdn.example.com/performer.jpg",
                    socialData: { id: 3 },
                    showCount: 6,
                },
            ],
        } as never);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body.data).toMatchObject({
            tonightShows: [{ id: 11 }],
            nextShow: { id: 12 },
            frequentPerformers: [{ id: 3, showCount: 6 }],
        });
        expectOpenApiResponse("/clubs/{id}/highlights", 200, body);
    });

    it("returns sparse highlights matching the shared OpenAPI contract", async () => {
        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "clubs-id-highlights",
        );
        expect(mockFindClubHighlights).toHaveBeenCalledWith(7);
        expect(body).toEqual({
            data: {
                tonightShows: [],
                nextShow: null,
                frequentPerformers: [],
            },
        });
        expectOpenApiResponse("/clubs/{id}/highlights", 200, body);
    });

    it("returns 400 for a non-numeric id", async () => {
        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "abc" }),
        });

        expect(res.status).toBe(400);
        await expect(res.json()).resolves.toEqual({ error: "Invalid id" });
        expect(mockFindClubHighlights).not.toHaveBeenCalled();
    });

    it("returns 404 when the active club does not exist", async () => {
        mockFindClubHighlights.mockResolvedValue(null);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });

        expect(res.status).toBe(404);
        await expect(res.json()).resolves.toEqual({
            error: "Club not found",
        });
    });

    it("passes through the public-read rate-limit response", async () => {
        mockApplyPublicReadRateLimit.mockResolvedValue(
            NextResponse.json({ error: "Too Many Requests" }, { status: 429 }),
        );

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });

        expect(res.status).toBe(429);
        expect(mockFindClubHighlights).not.toHaveBeenCalled();
    });

    it("applies a short shared-cache policy and preserves rate-limit headers", async () => {
        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });

        expect(res.status).toBe(200);
        expect(res.headers.get("Cache-Control")).toBe(
            "public, max-age=60, s-maxage=300, stale-while-revalidate=300",
        );
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });

    it("returns an uncached 500 with rate-limit headers on lookup failure", async () => {
        mockFindClubHighlights.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });

        expect(res.status).toBe(500);
        await expect(res.json()).resolves.toEqual({
            error: "Failed to fetch club highlights",
        });
        expect(res.headers.get("Cache-Control")).toBeNull();
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
