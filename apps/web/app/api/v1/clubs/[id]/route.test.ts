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
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
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
import { expectOpenApiResponse } from "@/test/openapiResponseValidator";

const mockFindUnique = vi.mocked(db.club.findUnique);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/clubs/7");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
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
            hasImage: true,
        } as any);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "7" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expectOpenApiResponse("/clubs/{id}", 200, body);
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
