import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
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
    rateLimitHeaders: vi.fn(() => ({ "X-RateLimit-Remaining": "42" })),
}));
vi.mock("@/lib/data/favorites/toggleFavoriteClub", () => ({
    toggleFavoriteClub: vi.fn(() => Promise.resolve(false)),
}));

import { DELETE } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { toggleFavoriteClub } from "@/lib/data/favorites/toggleFavoriteClub";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);
const mockToggleFavoriteClub = vi.mocked(toggleFavoriteClub);

function makeRequest(
    clubId: string = "42",
): [NextRequest, { params: Promise<{ clubId: string }> }] {
    const req = new NextRequest(
        `http://localhost/api/v1/favorite-clubs/${clubId}`,
        { method: "DELETE" },
    );
    return [req, { params: Promise.resolve({ clubId }) }];
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("DELETE /api/v1/favorite-clubs/[clubId]", () => {
    it('invokes applyPublicReadRateLimit with the "favorite-clubs" route prefix', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        const [req, ctx] = makeRequest();
        await DELETE(req, ctx);

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "favorite-clubs",
        );
    });

    it("returns the helper's NextResponse when the rate limit is exceeded", async () => {
        const fakeResponse = NextResponse.json(
            { error: "Too Many Requests" },
            { status: 429 },
        );
        mockApplyPublicReadRateLimit.mockResolvedValueOnce(fakeResponse);

        const [req, ctx] = makeRequest();
        const res = await DELETE(req, ctx);

        expect(res).toBe(fakeResponse);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("returns 422 when resolveAuth returns PROFILE_MISSING", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING");

        const [req, ctx] = makeRequest();
        const res = await DELETE(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(422);
        expect(body.error).toMatch(/profile not found/i);
        expect(mockRateLimitHeaders).toHaveBeenCalled();
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
    });

    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const [req, ctx] = makeRequest();
        const res = await DELETE(req, ctx);

        expect(res.status).toBe(401);
    });

    it("returns 400 when clubId is not a positive integer", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        const [req, ctx] = makeRequest("not-a-number");
        const res = await DELETE(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toMatch(/clubId/i);
        expect(mockToggleFavoriteClub).not.toHaveBeenCalled();
    });

    it("returns 200 with isFavorited:false on success and delegates to toggleFavoriteClub", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        const [req, ctx] = makeRequest();
        const res = await DELETE(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(body).toEqual({ data: { isFavorited: false } });
        expect(mockToggleFavoriteClub).toHaveBeenCalledWith(
            42,
            "profile-1",
            false,
        );
    });

    it("is idempotent — returns 200 even when no favorite row existed", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        // toggleFavoriteClub uses deleteMany under the hood; 0 rows is a non-event.
        mockToggleFavoriteClub.mockResolvedValueOnce(false);

        const [req, ctx] = makeRequest("999");
        const res = await DELETE(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ data: { isFavorited: false } });
    });
});
