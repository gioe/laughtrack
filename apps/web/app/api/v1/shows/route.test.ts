import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

// Use factory functions so real modules (and their DB deps) are never loaded
vi.mock("@/lib/auth/resolveAuth", () => ({ resolveAuth: vi.fn() }));
vi.mock("@/lib/data/show/search/getSearchedShows", () => ({
    getSearchedShows: vi.fn(),
}));

import { GET } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { getSearchedShows } from "@/lib/data/show/search/getSearchedShows";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockGetSearchedShows = vi.mocked(getSearchedShows);

function makeRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/v1/shows");
    url.searchParams.set("zip", "10001");
    for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
    }
    return new NextRequest(url.toString());
}

const mockShowResult = {
    total: 1,
    data: [
        {
            id: "show-1",
            lineup: [{ comedianId: "c1", isFavorite: true }],
        },
    ],
    filters: [],
};

beforeEach(() => {
    vi.clearAllMocks();
});

describe("GET /api/v1/shows", () => {
    describe("authenticated request", () => {
        it("passes profileId and userId to getSearchedShows and returns lineup with isFavorite", async () => {
            const authCtx = { profileId: "profile-abc", userId: "user-abc" };
            mockResolveAuth.mockResolvedValue(authCtx);
            mockGetSearchedShows.mockResolvedValue(mockShowResult as any);

            const req = makeRequest();
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(200);
            expect(mockGetSearchedShows).toHaveBeenCalledWith(
                expect.objectContaining({
                    profileId: "profile-abc",
                    userId: "user-abc",
                }),
            );
            expect(body.data[0].lineup[0].isFavorite).toBe(true);
        });
    });

    describe("resolveAuth throws", () => {
        it("returns 500 JSON with error key", async () => {
            mockResolveAuth.mockRejectedValue(
                new Error("Token verification failed"),
            );

            const req = makeRequest();
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(500);
            expect(body).toEqual({ error: "Failed to fetch shows" });
        });
    });

    describe("unauthenticated request", () => {
        it("does not pass profileId/userId and returns results without isFavorite enforced", async () => {
            mockResolveAuth.mockResolvedValue(null);
            const unauthResult = {
                total: 1,
                data: [{ id: "show-1", lineup: [{ comedianId: "c1" }] }],
                filters: [],
            };
            mockGetSearchedShows.mockResolvedValue(unauthResult as any);

            const req = makeRequest();
            const res = await GET(req);
            const body = await res.json();

            expect(res.status).toBe(200);
            // profileId and userId should NOT be passed when unauthenticated
            expect(mockGetSearchedShows).toHaveBeenCalledWith(
                expect.not.objectContaining({
                    profileId: expect.anything(),
                    userId: expect.anything(),
                }),
            );
            expect(body.data[0].lineup[0].isFavorite).toBeUndefined();
        });
    });
});
