import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/db", () => ({
    db: {
        favoritePodcast: { delete: vi.fn() },
    },
}));
vi.mock("@prisma/client", () => ({
    Prisma: {
        PrismaClientKnownRequestError: class PrismaClientKnownRequestError extends Error {
            code: string;
            constructor(message: string, { code }: { code: string }) {
                super(message);
                this.code = code;
            }
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
    rateLimitHeaders: vi.fn(() => ({ "X-RateLimit-Remaining": "42" })),
}));

import { DELETE } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockDelete = vi.mocked(db.favoritePodcast.delete);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);

function makeRequest(
    podcastId: string = "42",
): [NextRequest, { params: Promise<{ podcastId: string }> }] {
    const req = new NextRequest(
        `http://localhost/api/v1/favorite-podcasts/${podcastId}`,
        { method: "DELETE" },
    );
    return [req, { params: Promise.resolve({ podcastId }) }];
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("DELETE /api/v1/favorite-podcasts/[podcastId]", () => {
    it('invokes applyPublicReadRateLimit with the "favorite-podcasts" route prefix', async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockDelete.mockResolvedValue({} as never);

        const [req, ctx] = makeRequest();
        await DELETE(req, ctx);

        expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
            expect.any(NextRequest),
            "favorite-podcasts",
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

    it("returns 400 when podcastId is not a positive integer", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        const [req, ctx] = makeRequest("not-a-number");
        const res = await DELETE(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body.error).toMatch(/podcastId/i);
    });

    it("returns 404 when the favorite row is not found", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        const { Prisma } = await import("@prisma/client");
        mockDelete.mockRejectedValueOnce(
            new Prisma.PrismaClientKnownRequestError("Not found", {
                code: "P2025",
                clientVersion: "test",
            } as never),
        );

        const [req, ctx] = makeRequest();
        const res = await DELETE(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(404);
        expect(body.error).toMatch(/not found/i);
    });

    it("returns 200 with isFavorited:false on success", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockDelete.mockResolvedValue({} as never);

        const [req, ctx] = makeRequest();
        const res = await DELETE(req, ctx);
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("42");
        expect(body).toEqual({ data: { isFavorited: false } });
        expect(mockDelete).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    profileId_podcastId: {
                        profileId: "profile-1",
                        podcastId: 42,
                    },
                },
            }),
        );
    });
});
