import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() => ({
        allowed: true,
        limit: 10,
        remaining: 9,
        resetAt: 0,
    })),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { authToken: {} },
    rateLimitHeaders: vi.fn(() => ({})),
    rateLimitResponse: vi.fn(),
}));

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));

vi.mock("@/lib/auth/refreshTokens", () => ({
    revokeAllRefreshTokens: vi.fn(),
}));

import { POST } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import { revokeAllRefreshTokens } from "@/lib/auth/refreshTokens";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockRevokeAll = vi.mocked(revokeAllRefreshTokens);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/auth/signout", {
        method: "POST",
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("POST /api/v1/auth/signout", () => {
    it("returns 401 when unauthenticated", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await POST(makeRequest());
        expect(res.status).toBe(401);
        expect(mockRevokeAll).not.toHaveBeenCalled();
    });

    it("returns 422 when profile is missing", async () => {
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING" as any);

        const res = await POST(makeRequest());
        expect(res.status).toBe(422);
        expect(mockRevokeAll).not.toHaveBeenCalled();
    });

    it("revokes refresh tokens and returns count on success", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "p1",
            userId: "user-1",
        });
        mockRevokeAll.mockResolvedValue(3);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ revoked: 3 });
        expect(mockRevokeAll).toHaveBeenCalledWith("user-1");
    });
});
