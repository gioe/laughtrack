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
    rateLimitResponse: vi.fn(() => new Response(null, { status: 429 }) as any),
}));

vi.mock("@/lib/db", () => ({
    db: {
        userProfile: {
            update: vi.fn(),
        },
    },
}));

import { PATCH } from "./route";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { checkRateLimit } from "@/lib/rateLimit";
import { db } from "@/lib/db";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockCheckRateLimit = vi.mocked(checkRateLimit);
const mockUpdateProfile = vi.mocked(db.userProfile.update);

function makeRequest(body: unknown): NextRequest {
    return new NextRequest("http://localhost/api/v1/me/notifications", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
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

describe("PATCH /api/v1/me/notifications", () => {
    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await PATCH(makeRequest({ push_show_notifications: true }));

        expect(res.status).toBe(401);
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("returns 422 when authenticated user has no UserProfile row", async () => {
        mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

        const res = await PATCH(makeRequest({ push_show_notifications: true }));

        expect(res.status).toBe(422);
        expect(await res.json()).toEqual({ error: "profile_missing" });
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("rejects requests without a supported notification field", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });

        const res = await PATCH(makeRequest({}));

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({
            error: "At least one notification preference must be provided",
        });
        expect(mockUpdateProfile).not.toHaveBeenCalled();
    });

    it("updates email and push notification preferences for the authenticated profile", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        mockUpdateProfile.mockResolvedValue({
            emailShowNotifications: true,
            pushShowNotifications: false,
        } as any);

        const res = await PATCH(
            makeRequest({
                email_show_notifications: true,
                push_show_notifications: false,
            }),
        );

        expect(res.status).toBe(200);
        expect(mockUpdateProfile).toHaveBeenCalledWith({
            where: { userid: "user-123" },
            data: {
                emailShowNotifications: true,
                pushShowNotifications: false,
            },
            select: {
                emailShowNotifications: true,
                pushShowNotifications: true,
            },
        });
        expect(await res.json()).toEqual({
            data: {
                email_show_notifications: true,
                push_show_notifications: false,
            },
        });
    });

    it("returns 429 before auth when the IP rate limit is exceeded", async () => {
        mockCheckRateLimit.mockResolvedValueOnce({
            allowed: false,
            limit: 10,
            remaining: 0,
            resetAt: 0,
        });

        const res = await PATCH(makeRequest({ push_show_notifications: true }));

        expect(res.status).toBe(429);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });
});
