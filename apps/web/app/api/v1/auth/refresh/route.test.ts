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

vi.mock("@/util/token", () => ({
    ACCESS_TOKEN_TTL_SECONDS: 900,
    generateAccessToken: vi.fn(() => "new-access-jwt"),
}));

vi.mock("@/lib/auth/refreshTokens", () => ({
    consumeRefreshToken: vi.fn(),
    issueRefreshToken: vi.fn(() =>
        Promise.resolve({
            token: "new-refresh-token",
            expiresAt: new Date("2026-05-24T00:00:00Z"),
        }),
    ),
}));

import { POST } from "./route";
import {
    consumeRefreshToken,
    issueRefreshToken,
} from "@/lib/auth/refreshTokens";

const mockConsume = vi.mocked(consumeRefreshToken);
const mockIssue = vi.mocked(issueRefreshToken);

function makeRequest(body: unknown): NextRequest {
    return new NextRequest("http://localhost/api/v1/auth/refresh", {
        method: "POST",
        body: body === undefined ? undefined : JSON.stringify(body),
        headers: { "content-type": "application/json" },
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("POST /api/v1/auth/refresh", () => {
    it("returns 400 when body is not valid JSON", async () => {
        const req = new NextRequest("http://localhost/api/v1/auth/refresh", {
            method: "POST",
            body: "not json",
            headers: { "content-type": "application/json" },
        });

        const res = await POST(req);
        expect(res.status).toBe(400);
        const body = await res.json();
        expect(body.error).toBe("invalid_body");
    });

    it("returns 400 when refreshToken field is missing", async () => {
        const res = await POST(makeRequest({ foo: "bar" }));
        expect(res.status).toBe(400);
        const body = await res.json();
        expect(body.error).toBe("missing_refresh_token");
    });

    it("returns 401 when refresh token is not found", async () => {
        mockConsume.mockResolvedValue("not_found");

        const res = await POST(makeRequest({ refreshToken: "abc" }));
        expect(res.status).toBe(401);
        const body = await res.json();
        expect(body.error).toBe("not_found");
    });

    it("returns 401 when refresh token is revoked", async () => {
        mockConsume.mockResolvedValue("revoked");

        const res = await POST(makeRequest({ refreshToken: "abc" }));
        expect(res.status).toBe(401);
        const body = await res.json();
        expect(body.error).toBe("revoked");
    });

    it("returns 401 when refresh token is expired", async () => {
        mockConsume.mockResolvedValue("expired");

        const res = await POST(makeRequest({ refreshToken: "abc" }));
        expect(res.status).toBe(401);
    });

    it("returns rotated access+refresh tokens on success", async () => {
        mockConsume.mockResolvedValue({
            id: "rt-1",
            userId: "user-1",
            userEmail: "user@example.com",
        });

        const res = await POST(makeRequest({ refreshToken: "old-refresh" }));
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({
            accessToken: "new-access-jwt",
            refreshToken: "new-refresh-token",
            expiresIn: 900,
        });
        expect(mockConsume).toHaveBeenCalledWith("old-refresh");
        expect(mockIssue).toHaveBeenCalledWith("user-1");
    });
});
