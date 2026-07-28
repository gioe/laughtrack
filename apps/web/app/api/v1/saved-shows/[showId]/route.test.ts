import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));
vi.mock("@/lib/db", () => ({
    db: {
        show: { findFirst: vi.fn() },
        savedShow: {
            findUnique: vi.fn(),
            upsert: vi.fn(),
            deleteMany: vi.fn(),
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

import { DELETE, GET, POST } from "./route";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";
import { applyPublicReadRateLimit } from "@/lib/rateLimit";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockFindShow = vi.mocked(db.show.findFirst);
const mockFindSavedShow = vi.mocked(db.savedShow.findUnique);
const mockUpsert = vi.mocked(db.savedShow.upsert);
const mockDeleteMany = vi.mocked(db.savedShow.deleteMany);
const mockApplyPublicReadRateLimit = vi.mocked(applyPublicReadRateLimit);

type Handler = typeof GET;

function makeCall(handler: Handler, showId = "42"): ReturnType<Handler> {
    const method =
        handler === POST ? "POST" : handler === DELETE ? "DELETE" : "GET";
    const request = new NextRequest(
        `http://localhost/api/v1/saved-shows/${showId}`,
        { method },
    );
    return handler(request, {
        params: Promise.resolve({ showId }),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindSavedShow.mockResolvedValue(null);
});

describe("/api/v1/saved-shows/[showId]", () => {
    it.each([
        ["GET", GET],
        ["POST", POST],
        ["DELETE", DELETE],
    ] as const)(
        "%s returns 401 without authentication",
        async (_name, handler) => {
            mockResolveAuth.mockResolvedValue(null);

            const response = await makeCall(handler);

            expect(response.status).toBe(401);
        },
    );

    it.each([
        ["GET", GET],
        ["POST", POST],
        ["DELETE", DELETE],
    ] as const)(
        "%s returns 422 when the authenticated user has no profile",
        async (_name, handler) => {
            mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

            const response = await makeCall(handler);

            expect(response.status).toBe(422);
            expect((await response.json()).error).toMatch(/profile not found/i);
        },
    );

    it("returns a rate-limit response before resolving auth", async () => {
        const limited = NextResponse.json(
            { error: "Too Many Requests" },
            { status: 429 },
        );
        mockApplyPublicReadRateLimit.mockResolvedValueOnce(limited);

        const response = await makeCall(GET);

        expect(response).toBe(limited);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it.each([
        ["0", GET],
        ["1.5", POST],
        ["42junk", DELETE],
    ] as const)("rejects invalid show id %s", async (showId, handler) => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });

        const response = await makeCall(handler, showId);

        expect(response.status).toBe(400);
    });

    it("returns 404 state for a missing or hidden show", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindShow.mockResolvedValue(null);

        const response = await makeCall(GET);

        expect(response.status).toBe(404);
        expect(mockFindShow).toHaveBeenCalledWith({
            where: { id: 42, club: { visible: true } },
            select: { id: true },
        });
        expect(mockFindSavedShow).not.toHaveBeenCalled();
    });

    it.each([
        ["saved", { showId: 42 }, true],
        ["unsaved", null, false],
    ] as const)(
        "returns %s state for a visible show, including past shows",
        async (_name, savedShow, isSaved) => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockFindShow.mockResolvedValue({ id: 42 } as never);
            mockFindSavedShow.mockResolvedValue(savedShow as never);

            const response = await makeCall(GET);

            expect(response.status).toBe(200);
            expect(response.headers.get("Cache-Control")).toBe(
                "private, no-store",
            );
            expect(await response.json()).toEqual({ data: { isSaved } });
            expect(mockFindSavedShow).toHaveBeenCalledWith({
                where: {
                    profileId_showId: {
                        profileId: "profile-1",
                        showId: 42,
                    },
                },
                select: { showId: true },
            });
        },
    );

    it("returns 404 when saving a missing or hidden show", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindShow.mockResolvedValue(null);

        const response = await makeCall(POST);

        expect(response.status).toBe(404);
        expect(mockUpsert).not.toHaveBeenCalled();
    });

    it("returns 409 when saving an already-past show", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindShow.mockResolvedValue({
            id: 42,
            date: new Date("2000-01-01T00:00:00.000Z"),
        } as never);

        const response = await makeCall(POST);

        expect(response.status).toBe(409);
        expect((await response.json()).error).toMatch(/upcoming/i);
        expect(mockUpsert).not.toHaveBeenCalled();
    });

    it("keeps save retries idempotent after an already-saved show passes", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindSavedShow.mockResolvedValue({ showId: 42 } as never);

        const response = await makeCall(POST);

        expect(response.status).toBe(200);
        expect(await response.json()).toEqual({ data: { isSaved: true } });
        expect(mockFindShow).not.toHaveBeenCalled();
        expect(mockUpsert).not.toHaveBeenCalled();
    });

    it("idempotently saves an upcoming visible show", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "profile-1",
            userId: "user-1",
        });
        mockFindShow.mockResolvedValue({
            id: 42,
            date: new Date("2100-01-01T00:00:00.000Z"),
        } as never);
        mockUpsert.mockResolvedValue({} as never);

        const response = await makeCall(POST);

        expect(response.status).toBe(200);
        expect(response.headers.get("Cache-Control")).toBe("private, no-store");
        expect(await response.json()).toEqual({ data: { isSaved: true } });
        expect(mockUpsert).toHaveBeenCalledWith({
            where: {
                profileId_showId: {
                    profileId: "profile-1",
                    showId: 42,
                },
            },
            create: { profileId: "profile-1", showId: 42 },
            update: {},
        });
    });

    it.each([0, 1])(
        "idempotently unsaves when deleteMany removes %s rows",
        async (count) => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockDeleteMany.mockResolvedValue({ count });

            const response = await makeCall(DELETE);

            expect(response.status).toBe(200);
            expect(await response.json()).toEqual({
                data: { isSaved: false },
            });
            expect(mockDeleteMany).toHaveBeenCalledWith({
                where: { profileId: "profile-1", showId: 42 },
            });
            expect(mockFindShow).not.toHaveBeenCalled();
        },
    );

    it.each([
        ["GET", GET],
        ["POST", POST],
        ["DELETE", DELETE],
    ] as const)(
        "rate limits %s with the saved-shows prefix",
        async (_name, handler) => {
            mockResolveAuth.mockResolvedValue({
                profileId: "profile-1",
                userId: "user-1",
            });
            mockFindShow.mockResolvedValue({
                id: 42,
                date: new Date("2100-01-01T00:00:00.000Z"),
            } as never);
            mockFindSavedShow.mockResolvedValue(null);
            mockUpsert.mockResolvedValue({} as never);
            mockDeleteMany.mockResolvedValue({ count: 0 });

            await makeCall(handler);

            expect(mockApplyPublicReadRateLimit).toHaveBeenCalledWith(
                expect.any(NextRequest),
                "saved-shows",
            );
        },
    );
});
