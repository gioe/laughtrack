import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() => ({
        allowed: true,
        limit: 100,
        remaining: 99,
        resetAt: 0,
    })),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { authenticated: {}, unauthenticated: {} },
    rateLimitHeaders: vi.fn(() => ({})),
    rateLimitResponse: vi.fn(),
}));
vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));
vi.mock("@/lib/db", () => ({
    db: {
        favoriteComedian: {
            findMany: vi.fn(),
            count: vi.fn(),
        },
    },
}));
vi.mock("@/util/imageUtil", () => ({
    buildComedianImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));

import { GET } from "./route";
import { auth } from "@/auth";
import { db } from "@/lib/db";

const mockAuth = vi.mocked(auth);
const mockFindMany = vi.mocked(db.favoriteComedian.findMany);
const mockCount = vi.mocked(db.favoriteComedian.count);

const TEST_USER_ID = "user-123";
const SESSION = {
    profile: { userid: TEST_USER_ID },
};

function makeComedian(id: number) {
    return {
        id,
        uuid: `uuid-${id}`,
        name: `Comedian ${id}`,
        instagramAccount: null,
        instagramFollowers: null,
        tiktokAccount: null,
        tiktokFollowers: null,
        youtubeAccount: null,
        youtubeFollowers: null,
        website: null,
        popularity: 0,
        linktree: null,
    };
}

function makeRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/favorites");
    for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
    }
    return new NextRequest(url.toString());
}

beforeEach(() => {
    vi.clearAllMocks();
    mockAuth.mockResolvedValue(SESSION as any);
});

describe("GET /api/favorites", () => {
    describe("pagination", () => {
        it("no params returns { comedians, total } with first 100 results", async () => {
            const comedians = Array.from({ length: 3 }, (_, i) =>
                makeComedian(i + 1),
            );
            mockFindMany.mockResolvedValue(
                comedians.map((c) => ({ comedian: c })) as any,
            );
            mockCount.mockResolvedValue(3);

            const res = await GET(makeRequest({ userId: TEST_USER_ID }));
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body.total).toBe(3);
            expect(body.comedians).toHaveLength(3);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ skip: 0, take: 100 }),
            );
        });

        it("?page=1 queries with offset 100", async () => {
            mockFindMany.mockResolvedValue([]);
            mockCount.mockResolvedValue(50);

            const res = await GET(
                makeRequest({ userId: TEST_USER_ID, page: "1" }),
            );
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockFindMany).toHaveBeenCalledWith(
                expect.objectContaining({ skip: 100, take: 100 }),
            );
            expect(body).toEqual({ comedians: [], total: 50 });
        });

        it("page beyond total returns { comedians: [], total } without 500", async () => {
            mockFindMany.mockResolvedValue([]);
            mockCount.mockResolvedValue(10);

            const res = await GET(
                makeRequest({ userId: TEST_USER_ID, page: "99" }),
            );
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(body).toEqual({ comedians: [], total: 10 });
        });
    });

    describe("validation", () => {
        it("page=-1 returns 400", async () => {
            const res = await GET(
                makeRequest({ userId: TEST_USER_ID, page: "-1" }),
            );
            expect(res.status).toBe(400);
        });

        it("page=abc returns 400", async () => {
            const res = await GET(
                makeRequest({ userId: TEST_USER_ID, page: "abc" }),
            );
            expect(res.status).toBe(400);
        });

        it("missing userId returns 400", async () => {
            const res = await GET(makeRequest());
            expect(res.status).toBe(400);
        });
    });
});
