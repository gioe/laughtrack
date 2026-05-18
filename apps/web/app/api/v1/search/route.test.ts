import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/db", () => ({
    db: {
        podcast: {
            count: vi.fn(),
            findMany: vi.fn(),
        },
        show: {
            count: vi.fn(),
            findMany: vi.fn(),
        },
        comedian: {
            count: vi.fn(),
            findMany: vi.fn(),
        },
        club: {
            count: vi.fn(),
            findMany: vi.fn(),
        },
    },
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
    rateLimitHeaders: vi.fn(() => ({})),
}));

import { GET } from "./route";
import { db } from "@/lib/db";

const mockDb = db as unknown as {
    podcast: {
        count: ReturnType<typeof vi.fn>;
        findMany: ReturnType<typeof vi.fn>;
    };
    show: {
        count: ReturnType<typeof vi.fn>;
        findMany: ReturnType<typeof vi.fn>;
    };
    comedian: {
        count: ReturnType<typeof vi.fn>;
        findMany: ReturnType<typeof vi.fn>;
    };
    club: {
        count: ReturnType<typeof vi.fn>;
        findMany: ReturnType<typeof vi.fn>;
    };
};

function makeRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/v1/search");
    for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
    }
    return new NextRequest(url.toString());
}

beforeEach(() => {
    vi.clearAllMocks();
    mockDb.podcast.count.mockResolvedValue(1);
    mockDb.podcast.findMany.mockResolvedValue([
        {
            id: 10,
            slug: "good-one",
            title: "Good One",
            authorName: "Vulture",
            imageUrl: "https://cdn.example.com/good-one.jpg",
            websiteUrl: "https://www.vulture.com/good-one",
        },
    ]);
    mockDb.show.count.mockResolvedValue(0);
    mockDb.show.findMany.mockResolvedValue([]);
    mockDb.comedian.count.mockResolvedValue(0);
    mockDb.comedian.findMany.mockResolvedValue([]);
    mockDb.club.count.mockResolvedValue(0);
    mockDb.club.findMany.mockResolvedValue([]);
});

describe("GET /api/v1/search", () => {
    it("queries podcasts by title and author for global search", async () => {
        const res = await GET(makeRequest({ q: "good", type: "podcast" }));
        const body = await res.json();

        expect(res.status).toBe(200);
        const expectedPodcastWhere = {
            AND: [
                {
                    comedianPodcasts: {
                        some: {
                            reviewStatus: "accepted",
                            associationType: { in: ["host", "owner"] },
                        },
                    },
                },
                {
                    OR: [
                        {
                            title: {
                                contains: "good",
                                mode: "insensitive",
                            },
                        },
                        {
                            authorName: {
                                contains: "good",
                                mode: "insensitive",
                            },
                        },
                    ],
                },
            ],
        };
        expect(mockDb.podcast.count).toHaveBeenCalledWith({
            where: expectedPodcastWhere,
        });
        expect(mockDb.podcast.findMany).toHaveBeenCalledWith(
            expect.objectContaining({
                where: expectedPodcastWhere,
            }),
        );
        expect(body).toEqual({
            data: [
                {
                    id: "podcast-10",
                    entityType: "podcast",
                    title: "Good One",
                    subtitle: "Vulture",
                    href: "https://www.vulture.com/good-one",
                    imageUrl: "https://cdn.example.com/good-one.jpg",
                },
            ],
            total: 1,
            totals: {
                all: 1,
                show: 0,
                comedian: 0,
                club: 0,
                podcast: 1,
            },
        });
    });

    it("does not query geo-scoped show data for podcast-only searches", async () => {
        await GET(makeRequest({ q: "good", type: "podcast" }));

        expect(mockDb.show.findMany).not.toHaveBeenCalled();
        expect(mockDb.club.findMany).not.toHaveBeenCalled();
        expect(mockDb.comedian.findMany).not.toHaveBeenCalled();
    });
});
