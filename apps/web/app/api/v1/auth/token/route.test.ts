import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() => ({
        allowed: true,
        limit: 100,
        remaining: 99,
        resetAt: 0,
    })),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { authToken: {} },
    rateLimitHeaders: vi.fn(() => ({})),
    rateLimitResponse: vi.fn(),
}));

vi.mock("@/auth", () => ({
    auth: vi.fn(),
}));

vi.mock("@/util/token", () => ({
    ACCESS_TOKEN_TTL_SECONDS: 900,
    generateAccessToken: vi.fn(() => "mock-access-jwt"),
}));

vi.mock("@/lib/auth/refreshTokens", () => ({
    issueRefreshToken: vi.fn(() =>
        Promise.resolve({
            token: "mock-refresh-token",
            expiresAt: new Date("2026-05-24T00:00:00Z"),
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
import { auth } from "@/auth";
import { db } from "@/lib/db";
import { issueRefreshToken } from "@/lib/auth/refreshTokens";

const mockAuth = vi.mocked(auth);
const mockFindUser = vi.mocked(db.user.findUnique);
const mockIssueRefresh = vi.mocked(issueRefreshToken);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/auth/token", {
        method: "POST",
    });
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("POST /api/v1/auth/token", () => {
    it("returns 401 when auth() returns null", async () => {
        mockAuth.mockResolvedValue(null as any);

        const res = await POST(makeRequest());

        expect(res.status).toBe(401);
    });

    it("returns 401 when session has no user email", async () => {
        mockAuth.mockResolvedValue({ user: {} } as any);

        const res = await POST(makeRequest());

        expect(res.status).toBe(401);
    });

    it("returns 401 when user row is missing", async () => {
        mockAuth.mockResolvedValue({
            user: { email: "user@example.com" },
        } as any);
        mockFindUser.mockResolvedValue(null);

        const res = await POST(makeRequest());

        expect(res.status).toBe(401);
    });

    it("returns 200 with both tokens and expiresIn on valid session", async () => {
        mockAuth.mockResolvedValue({
            user: { email: "user@example.com" },
        } as any);
        mockFindUser.mockResolvedValue({ id: "user-123" } as any);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({
            accessToken: "mock-access-jwt",
            refreshToken: "mock-refresh-token",
            expiresIn: 900,
        });
        expect(mockIssueRefresh).toHaveBeenCalledWith("user-123");
    });
});
