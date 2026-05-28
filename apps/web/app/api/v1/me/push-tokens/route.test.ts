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
        userPushToken: {
            upsert: vi.fn(),
            updateMany: vi.fn(),
        },
    },
}));

import { DELETE, POST } from "./route";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { db } from "@/lib/db";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockUpsertPushToken = vi.mocked(db.userPushToken.upsert);
const mockUpdateManyPushTokens = vi.mocked(db.userPushToken.updateMany);

function makeRequest(body: unknown): NextRequest {
    return new NextRequest("http://localhost/api/v1/me/push-tokens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("POST /api/v1/me/push-tokens", () => {
    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await POST(makeRequest({ token: "abc123" }));

        expect(res.status).toBe(401);
        expect(mockUpsertPushToken).not.toHaveBeenCalled();
    });

    it("returns 422 when authenticated user has no UserProfile row", async () => {
        mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

        const res = await POST(makeRequest({ token: "abc123" }));

        expect(res.status).toBe(422);
        expect(await res.json()).toEqual({ error: "profile_missing" });
        expect(mockUpsertPushToken).not.toHaveBeenCalled();
    });

    it("registers or refreshes an APNs token for the authenticated caller", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        mockUpsertPushToken.mockResolvedValue({
            id: "token-row-1",
            platform: "ios",
            isActive: true,
        } as never);

        const res = await POST(makeRequest({ token: "ABCDEF1234567890", platform: "ios" }));

        expect(res.status).toBe(200);
        expect(mockUpsertPushToken).toHaveBeenCalledWith({
            where: { token: "abcdef1234567890" },
            create: {
                token: "abcdef1234567890",
                platform: "ios",
                userId: "user-123",
                profileId: "profile-123",
                isActive: true,
                revokedAt: null,
            },
            update: {
                platform: "ios",
                userId: "user-123",
                profileId: "profile-123",
                isActive: true,
                revokedAt: null,
                lastRegisteredAt: expect.any(Date),
            },
            select: {
                id: true,
                platform: true,
                isActive: true,
            },
        });
        expect(await res.json()).toEqual({
            data: { id: "token-row-1", platform: "ios", isActive: true },
        });
    });
});

describe("DELETE /api/v1/me/push-tokens", () => {
    it("deactivates only the caller-owned APNs token", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        mockUpdateManyPushTokens.mockResolvedValue({ count: 1 } as never);

        const res = await DELETE(makeRequest({ token: "ABCDEF1234567890" }));

        expect(res.status).toBe(200);
        expect(mockUpdateManyPushTokens).toHaveBeenCalledWith({
            where: {
                token: "abcdef1234567890",
                userId: "user-123",
                profileId: "profile-123",
                isActive: true,
            },
            data: {
                isActive: false,
                revokedAt: expect.any(Date),
            },
        });
        expect(await res.json()).toEqual({ data: { deactivated: true } });
    });
});
