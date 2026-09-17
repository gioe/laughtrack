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
import { expectOpenApiResponse } from "@/test/openapiResponseValidator";

const mockFindShowById = vi.mocked(findShowById);
const mockFindRelatedShowsForShow = vi.mocked(findRelatedShowsForShow);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);
type FindShowByIdResult = Awaited<ReturnType<typeof findShowById>>;
type RelatedShowsResult = Awaited<ReturnType<typeof findRelatedShowsForShow>>;

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/shows/42");
}

function availabilityShow(
    overrides: Partial<FindShowByIdResult["show"]>,
): FindShowByIdResult {
    return {
        clubId: 7,
        show: {
            id: 42,
            clubId: 7,
            name: "Friday Night Laughs",
            date: new Date("2099-07-04T20:00:00.000Z"),
            address: "117 Macdougal St",
            clubName: "Comedy Cellar",
            imageUrl: "https://cdn.example.com/comedy-cellar.jpg",
            lineup: [],
            tickets: [],
            soldOut: false,
            distanceMiles: null,
            timezone: "America/New_York",
            showPageUrl: "",
            ...overrides,
        },
    };
}

function ticket(purchaseUrl: string, soldOut = false) {
    return { price: 25, purchaseUrl, soldOut, type: "General Admission" };
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
                clubId: 7,
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
                clubId: 7,
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
        expectOpenApiResponse("/shows/{id}", 200, body);
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
        // Pin representative camelCase wire keys on the spread `...show`
        // and on `relatedShows[]` so a future regression
        // (e.g. clubId → club_id, soldOut → sold_out) surfaces here.
        expect(body.data.clubId).toBe(7);
        expect(body.data.imageUrl).toBe(
            "https://cdn.example.com/comedy-cellar.jpg",
        );
        expect(body.data.soldOut).toBe(false);
        expect(body.data.showPageUrl).toBe("https://club.example.com/show/42");
        expect(body.data.tickets[0].purchaseUrl).toBe(
            "https://tickets.example.com/show/42",
        );
        expect(body.data.tickets[0].soldOut).toBe(false);
        expect(body.relatedShows[0].clubId).toBe(7);
        expect(body.relatedShows[0].imageUrl).toBe(
            "https://cdn.example.com/late-show.jpg",
        );
    });

    it("does not report a show as sold out solely because ticket links are unavailable", async () => {
        const showResult: FindShowByIdResult = {
            clubId: 7,
            show: {
                id: 42,
                clubId: 7,
                name: "Friday Night Laughs",
                date: new Date("2099-07-04T20:00:00.000Z"),
                address: "117 Macdougal St",
                clubName: "Comedy Cellar",
                imageUrl: "https://cdn.example.com/comedy-cellar.jpg",
                soldOut: false,
                lineup: [],
                tickets: [
                    {
                        price: 25,
                        purchaseUrl: "",
                        soldOut: false,
                        type: "General Admission",
                    },
                ],
                distanceMiles: null,
                timezone: "America/New_York",
                showPageUrl: "",
            },
        };
        mockFindShowById.mockResolvedValue(showResult);
        mockFindRelatedShowsForShow.mockResolvedValue([]);

        const res = await GET(makeRequest(), {
            params: Promise.resolve({ id: "42" }),
        });
        const body = await res.json();

        expect(res.status).toBe(200);
        expectOpenApiResponse("/shows/{id}", 200, body);
        expect(body.data.cta.url).toBeNull();
        expect(body.data.soldOut).toBe(false);
        expect(body.data.tickets[0].soldOut).toBe(false);
        expect(body.data.cta.isSoldOut).toBe(false);
    });

    it.each([
        {
            name: "empty inventory",
            show: { tickets: [] },
            url: null,
            soldOut: false,
        },
        {
            name: "missing inventory",
            show: { tickets: undefined, soldOut: undefined },
            url: null,
            soldOut: false,
        },
        {
            name: "explicit show sellout without a link",
            show: { soldOut: true },
            url: null,
            soldOut: true,
        },
        {
            name: "explicit show sellout with a live ticket link",
            show: {
                soldOut: true,
                tickets: [ticket("https://tickets.example.com/42")],
            },
            url: "https://tickets.example.com/42",
            soldOut: true,
        },
        {
            name: "all ticket tiers sold out",
            show: {
                tickets: [ticket("https://tickets.example.com/42", true)],
                showPageUrl: "https://club.example.com/42",
            },
            url: "https://club.example.com/42",
            soldOut: true,
        },
        {
            name: "live tier following a sold-out tier",
            show: {
                tickets: [
                    ticket("https://tickets.example.com/sold", true),
                    ticket("https://tickets.example.com/live"),
                ],
            },
            url: "https://tickets.example.com/live",
            soldOut: false,
        },
        {
            name: "missing purchase link with show-page fallback",
            show: {
                tickets: [ticket("")],
                showPageUrl: "https://club.example.com/42",
            },
            url: "https://club.example.com/42",
            soldOut: false,
        },
        {
            name: "malformed purchase link with show-page fallback",
            show: {
                tickets: [ticket("not a URL")],
                showPageUrl: "https://club.example.com/42",
            },
            url: "https://club.example.com/42",
            soldOut: false,
        },
        {
            name: "non-HTTP purchase link with show-page fallback",
            show: {
                tickets: [ticket("javascript:alert(1)")],
                showPageUrl: "https://club.example.com/42",
            },
            url: "https://club.example.com/42",
            soldOut: false,
        },
        {
            name: "invalid purchase link followed by a valid tier",
            show: {
                tickets: [
                    ticket("mailto:boxoffice@example.com"),
                    ticket("https://tickets.example.com/live"),
                ],
            },
            url: "https://tickets.example.com/live",
            soldOut: false,
        },
        {
            name: "malformed destinations",
            show: { tickets: [ticket("https://")], showPageUrl: "not a URL" },
            url: null,
            soldOut: false,
        },
        {
            name: "non-HTTP show-page destination",
            show: { showPageUrl: "ftp://club.example.com/42" },
            url: null,
            soldOut: false,
        },
        {
            name: "whitespace destinations",
            show: { tickets: [ticket("  ")], showPageUrl: "  " },
            url: null,
            soldOut: false,
        },
        {
            name: "HTTP purchase destination",
            show: { tickets: [ticket("http://tickets.example.com/42")] },
            url: "http://tickets.example.com/42",
            soldOut: false,
        },
    ])(
        "keeps inventory and destination availability separate: $name",
        async ({ show, url, soldOut }) => {
            mockFindShowById.mockResolvedValue(availabilityShow(show));
            mockFindRelatedShowsForShow.mockResolvedValue([]);

            const res = await GET(makeRequest(), {
                params: Promise.resolve({ id: "42" }),
            });
            const body = await res.json();

            expect(res.status).toBe(200);
            expectOpenApiResponse("/shows/{id}", 200, body);
            expect(body.data.cta).toEqual({
                url,
                label: "Get tickets for Friday Night Laughs",
                isSoldOut: soldOut,
            });
        },
    );

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
