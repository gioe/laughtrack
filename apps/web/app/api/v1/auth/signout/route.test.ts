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
    revokeRefreshToken: vi.fn(),
}));

import { POST } from "./route";
import { resolveAuth } from "@/lib/auth/resolveAuth";
import {
    revokeAllRefreshTokens,
    revokeRefreshToken,
} from "@/lib/auth/refreshTokens";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockRevokeAll = vi.mocked(revokeAllRefreshTokens);
const mockRevokeOne = vi.mocked(revokeRefreshToken);

function makeRequest(body?: unknown): NextRequest {
    return new NextRequest("http://localhost/api/v1/auth/signout", {
        method: "POST",
        body: body === undefined ? undefined : JSON.stringify(body),
        headers:
            body === undefined
                ? undefined
                : { "content-type": "application/json" },
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
        mockResolveAuth.mockResolvedValue("PROFILE_MISSING" as never);

        const res = await POST(makeRequest());
        expect(res.status).toBe(422);
        expect(mockRevokeAll).not.toHaveBeenCalled();
    });

    it("keeps empty-body legacy requests compatible by revoking all tokens", async () => {
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
        expect(mockRevokeOne).not.toHaveBeenCalled();
    });

    it("revokes only the caller-owned presented token and logs sanitized client context", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "p1",
            userId: "user-1",
        });
        mockRevokeOne.mockResolvedValue(1);
        const infoSpy = vi.spyOn(console, "info").mockImplementation(() => {});

        const res = await POST(
            makeRequest({
                refreshToken: "secret-refresh-token",
                platform: "ios",
                appVersion: "2.17.0+57",
                source: "profile",
            }),
        );
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ revoked: 1 });
        expect(mockRevokeOne).toHaveBeenCalledWith(
            "user-1",
            "secret-refresh-token",
        );
        expect(mockRevokeAll).not.toHaveBeenCalled();

        const logged = infoSpy.mock.calls.flat().join(" ");
        expect(logged).toContain("platform=ios");
        expect(logged).toContain("appVersion=2.17.0+57");
        expect(logged).toContain("source=profile");
        expect(logged).not.toContain("secret-refresh-token");
        infoSpy.mockRestore();
    });

    it("returns 400 for malformed nonempty JSON", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "p1",
            userId: "user-1",
        });
        const req = new NextRequest("http://localhost/api/v1/auth/signout", {
            method: "POST",
            body: "not json",
            headers: { "content-type": "application/json" },
        });

        const res = await POST(req);

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({ error: "invalid_body" });
        expect(mockRevokeAll).not.toHaveBeenCalled();
        expect(mockRevokeOne).not.toHaveBeenCalled();
    });

    it("returns 400 for invalid or unsafe client metadata", async () => {
        mockResolveAuth.mockResolvedValue({
            profileId: "p1",
            userId: "user-1",
        });

        const res = await POST(
            makeRequest({
                refreshToken: "secret-refresh-token",
                platform: "ios",
                appVersion: "2.17.0\nforged=true",
                source: "profile",
            }),
        );

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({ error: "invalid_body" });
        expect(mockRevokeAll).not.toHaveBeenCalled();
        expect(mockRevokeOne).not.toHaveBeenCalled();
    });
});
