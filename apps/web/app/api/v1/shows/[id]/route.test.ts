import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { NotFoundError } from "@/objects/NotFoundError";

vi.mock("@/lib/data/show/detail/findShowById", () => ({
    findShowById: vi.fn(),
}));
vi.mock("@/lib/data/show/detail/findRelatedShowsForShow", () => ({
    findRelatedShowsForShow: vi.fn(),
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
import { findRelatedShowsForShow } from "@/lib/data/show/detail/findRelatedShowsForShow";
import { findShowById } from "@/lib/data/show/detail/findShowById";
import { rateLimitHeaders } from "@/lib/rateLimit";
import {
    RATE_LIMIT_SENTINEL_HEADER,
    RATE_LIMIT_SENTINEL_HEADERS,
    RATE_LIMIT_SENTINEL_VALUE,
} from "@/test/rateLimitSentinel";

const mockFindShowById = vi.mocked(findShowById);
const mockFindRelatedShowsForShow = vi.mocked(findRelatedShowsForShow);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);
type FindShowByIdResult = Awaited<ReturnType<typeof findShowById>>;
type RelatedShowsResult = Awaited<ReturnType<typeof findRelatedShowsForShow>>;

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/shows/42");
}

beforeEach(() => {
    vi.clearAllMocks();
    mockRateLimitHeaders.mockReturnValue(RATE_LIMIT_SENTINEL_HEADERS);
});

describe("GET /api/v1/shows/[id]", () => {
    it("returns show detail data, related shows, club fields, and CTA fields", async () => {
        const showResult: FindShowByIdResult = {
            clubId: 7,
            show: {
                id: 42,
                name: "Friday Night Laughs",
                date: new Date("2026-07-04T20:00:00.000Z"),
                description: "A stacked lineup.",
                room: "Main Room",
                address: "117 Macdougal St",
                clubName: "Comedy Cellar",
                imageUrl: "https://cdn.example.com/comedy-cellar.jpg",
                soldOut: false,
                lineup: [{ id: 1, name: "Alice", imageUrl: "x", uuid: "u1" }],
                tickets: [
                    {
                        price: 25,
                        purchaseUrl: "https://tickets.example.com/show/42",
                        soldOut: false,
                        type: "General Admission",
                    },
                ],
                distanceMiles: null,
                timezone: "America/New_York",
                showPageUrl: "https://club.example.com/show/42",
            },
        };
        const relatedShows: RelatedShowsResult = [
            {
                id: 44,
                name: "Late Show",
                date: new Date("2026-07-05T22:00:00.000Z"),
                imageUrl: "https://cdn.example.com/late-show.jpg",
            },
        ];

        mockFindShowById.mockResolvedValue(showResult);
        mockFindRelatedShowsForShow.mockResolvedValue(relatedShows);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "42" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(mockFindShowById).toHaveBeenCalledWith(42);
        expect(mockFindRelatedShowsForShow).toHaveBeenCalledWith(42, 7);
        expect(body.data.club).toEqual({
            id: 7,
            name: "Comedy Cellar",
            address: "117 Macdougal St",
            imageUrl: "https://cdn.example.com/comedy-cellar.jpg",
            timezone: "America/New_York",
        });
        expect(body.data.cta).toEqual({
            url: "https://tickets.example.com/show/42",
            label: "Get tickets for Friday Night Laughs",
            isSoldOut: false,
        });
        expect(body.data.lineup).toHaveLength(1);
        expect(body.data.tickets).toHaveLength(1);
        expect(body.relatedShows).toHaveLength(1);
    });

    it("returns 400 for non-numeric ids without coercing partial numbers", async () => {
        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "42abc" }),
        });
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body).toEqual({ error: "Invalid id" });
        expect(mockFindShowById).not.toHaveBeenCalled();
    });

    it("returns 404 when the show is missing or hidden without leaking hidden venue data", async () => {
        mockFindShowById.mockRejectedValue(
            new NotFoundError('Show with id "42" at Hidden Club not found'),
        );

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "42" }),
        });
        const body = await res.json();

        expect(res.status).toBe(404);
        expect(body).toEqual({ error: "Show not found" });
        expect(JSON.stringify(body)).not.toContain("Hidden Club");
    });

    it("returns 500 when the detail lookup fails unexpectedly", async () => {
        mockFindShowById.mockRejectedValue(new Error("DB unavailable"));

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "42" }),
        });
        const body = await res.json();

        expect(res.status).toBe(500);
        expect(body).toEqual({ error: "Failed to fetch show" });
        expect(res.headers.get(RATE_LIMIT_SENTINEL_HEADER)).toBe(
            RATE_LIMIT_SENTINEL_VALUE,
        );
    });
});
