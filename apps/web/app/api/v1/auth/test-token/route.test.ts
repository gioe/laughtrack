import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
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
    generateAccessToken: vi.fn(() => "test-access-jwt"),
}));

vi.mock("@/lib/auth/refreshTokens", () => ({
    issueRefreshToken: vi.fn(() =>
        Promise.resolve({
            token: "test-refresh-token",
            expiresAt: new Date("2026-06-29T00:00:00Z"),
        }),
    ),
}));

vi.mock("@/lib/db", () => ({
    db: {
        user: {
            findUnique: vi.fn(),
        },
    },
}));

import { POST } from "./route";
import { db } from "@/lib/db";
import { issueRefreshToken } from "@/lib/auth/refreshTokens";

const mockFindUser = vi.mocked(db.user.findUnique);
const mockIssueRefresh = vi.mocked(issueRefreshToken);

function makeRequest(body: unknown, secret = "correct-secret"): NextRequest {
    return new NextRequest("http://localhost/api/v1/auth/test-token", {
        method: "POST",
        body: JSON.stringify(body),
        headers: {
            "content-type": "application/json",
            "x-test-auth-secret": secret,
        },
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("ENABLE_TEST_AUTH", "1");
    vi.stubEnv("TEST_AUTH_SECRET", "correct-secret");
    vi.stubEnv("TEST_AUTH_EMAIL_ALLOWLIST", "admin@laugh-track.com");
    vi.stubEnv("VERCEL_ENV", "preview");
});

afterEach(() => {
    vi.unstubAllEnvs();
});

describe("POST /api/v1/auth/test-token", () => {
    it("returns 404 when test auth is disabled", async () => {
        vi.stubEnv("ENABLE_TEST_AUTH", "0");

        const res = await POST(makeRequest({ email: "admin@laugh-track.com" }));

        expect(res.status).toBe(404);
        expect(mockFindUser).not.toHaveBeenCalled();
    });

    it("returns 404 in production even when enabled", async () => {
        vi.stubEnv("VERCEL_ENV", "production");

        const res = await POST(makeRequest({ email: "admin@laugh-track.com" }));

        expect(res.status).toBe(404);
        expect(mockFindUser).not.toHaveBeenCalled();
    });

    it("returns 401 when the shared secret is missing or wrong", async () => {
        const res = await POST(
            makeRequest({ email: "admin@laugh-track.com" }, "wrong-secret"),
        );

        expect(res.status).toBe(401);
        expect(mockFindUser).not.toHaveBeenCalled();
    });

    it("returns 403 when the requested email is not allowlisted", async () => {
        const res = await POST(makeRequest({ email: "other@example.com" }));

        expect(res.status).toBe(403);
        expect(mockFindUser).not.toHaveBeenCalled();
    });

    it("returns 401 when the allowlisted user row is missing", async () => {
        mockFindUser.mockResolvedValue(null);

        const res = await POST(makeRequest({ email: "admin@laugh-track.com" }));

        expect(res.status).toBe(401);
    });

    it("returns native token pair for an allowlisted real user", async () => {
        mockFindUser.mockResolvedValue({
            id: "user-123",
            email: "admin@laugh-track.com",
        } as never);

        const res = await POST(makeRequest({ email: "admin@laugh-track.com" }));
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({
            accessToken: "test-access-jwt",
            refreshToken: "test-refresh-token",
            expiresIn: 900,
        });
        expect(mockFindUser).toHaveBeenCalledWith({
            where: { email: "admin@laugh-track.com" },
            select: { id: true, email: true },
        });
        expect(mockIssueRefresh).toHaveBeenCalledWith("user-123");
    });
});
