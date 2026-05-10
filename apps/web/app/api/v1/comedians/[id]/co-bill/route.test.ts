import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/data/comedian/detail/findCoBilledComediansForComedian", () => ({
    findCoBilledComediansForComedian: vi.fn(),
}));
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

import { GET } from "./route";
import { findCoBilledComediansForComedian } from "@/lib/data/comedian/detail/findCoBilledComediansForComedian";
import { rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";
import { expectOpenApiResponse } from "@/test/openapiResponseValidator";

const mockFindCoBilledComedians = vi.mocked(findCoBilledComediansForComedian);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/comedians/123/co-bill");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/comedians/[id]/co-bill", () => {
    it("returns historical co-billed comedians using the ComedianLineup response shape", async () => {
        mockFindCoBilledComedians.mockResolvedValue([
            {
                id: 10,
                uuid: "comic-uuid",
                name: "Frequent Comic",
                imageUrl: "https://cdn.example.com/frequent.jpg",
                hasImage: true,
                show_count: 8,
                isFavorite: false,
                isAlias: false,
            },
        ]);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "123" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expectOpenApiResponse("/comedians/{id}/co-bill", 200, body);
        expect(body.data).toHaveLength(1);
        expect(mockFindCoBilledComedians).toHaveBeenCalledWith({
            comedianId: 123,
        });
    });

    it("returns 400 for a non-numeric id", async () => {
        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "not-a-number" }),
        });
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body).toEqual({ error: "Invalid id" });
        expect(mockFindCoBilledComedians).not.toHaveBeenCalled();
    });

    it("returns 500 with rate-limit headers when lookup fails unexpectedly", async () => {
        mockFindCoBilledComedians.mockRejectedValue(
            new Error("DB unavailable"),
        );

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "123" }),
        });
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch co-billed comedians" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
