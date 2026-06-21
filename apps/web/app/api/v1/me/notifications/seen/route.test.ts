import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));

vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() => ({
        allowed: true,
        limit: 100,
        remaining: 99,
        resetAt: 0,
    })),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { authenticated: {}, authToken: {} },
    rateLimitResponse: vi.fn(
        () => new Response(null, { status: 429 }) as never,
    ),
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: {
            update: vi.fn(),
        },
    },
}));

import { POST } from "./route";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { checkRateLimit } from "@/lib/rateLimit";
import { db } from "@/lib/db";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockCheckRateLimit = vi.mocked(checkRateLimit);
const mockUpdateProfile = vi.mocked(db.userProfile.update);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/me/notifications/seen", {
        method: "POST",
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockCheckRateLimit.mockResolvedValue({
        allowed: true,
        limit: 100,
        remaining: 99,
        resetAt: 0,
    });
});

describe("POST /api/v1/me/notifications/seen", () => {
    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await POST(makeRequest());

        expect(res.status).toBe(401);
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("returns 422 when authenticated user has no UserProfile row", async () => {
        mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

        const res = await POST(makeRequest());

        expect(res.status).toBe(422);
        expect(await res.json()).toEqual({ error: "profile_missing" });
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("returns 429 before auth when the IP rate limit is exceeded", async () => {
        mockCheckRateLimit.mockResolvedValueOnce({
            allowed: false,
            limit: 10,
            remaining: 0,
            resetAt: 0,
        });

        const res = await POST(makeRequest());

        expect(res.status).toBe(429);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("stamps notificationsLastSeenAt to now and returns the new timestamp", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        const stamped = new Date("2026-06-21T18:00:00.000Z");
        mockUpdateProfile.mockResolvedValue({
            notificationsLastSeenAt: stamped,
        } as never);

        const res = await POST(makeRequest());

        expect(res.status).toBe(200);
        expect(mockUpdateProfile).toHaveBeenCalledWith({
            where: { userid: "user-123" },
            data: { notificationsLastSeenAt: expect.any(Date) },
            select: { notificationsLastSeenAt: true },
        });
        expect(await res.json()).toEqual({
            data: { lastSeenAt: "2026-06-21T18:00:00.000Z" },
        });
    });

    it("keys rate limits by IP first, then by userId after auth resolves", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-abc",
            profileId: "profile-abc",
        });
        mockUpdateProfile.mockResolvedValue({
            notificationsLastSeenAt: new Date("2026-06-21T18:00:00.000Z"),
        } as never);

        await POST(makeRequest());

        expect(mockCheckRateLimit).toHaveBeenNthCalledWith(
            1,
            "me-notifications-seen-ip:127.0.0.1",
            expect.any(Object),
        );
        expect(mockCheckRateLimit).toHaveBeenNthCalledWith(
            2,
            "me-notifications-seen:user-abc",
            expect.any(Object),
        );
    });
});
