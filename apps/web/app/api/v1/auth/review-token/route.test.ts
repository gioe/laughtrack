import { randomBytes, scryptSync } from "node:crypto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
    rateLimitHeaders: vi.fn(() => ({ "X-RateLimit-Remaining": "9" })),
    rateLimitResponse: vi.fn(),
}));

vi.mock("@/util/token", () => ({
    ACCESS_TOKEN_TTL_SECONDS: 900,
    generateAccessToken: vi.fn(() => "review-access-jwt"),
}));

vi.mock("@/lib/auth/refreshTokens", () => ({
    issueRefreshToken: vi.fn(() =>
        Promise.resolve({
            token: "review-refresh-token",
            expiresAt: new Date("2026-08-14T00:00:00Z"),
        }),
    ),
}));

vi.mock("@/lib/db", () => ({
    db: {
        user: {
            upsert: vi.fn(),
        },
    },
}));

import { POST } from "./route";
import { db } from "@/lib/db";
import { issueRefreshToken } from "@/lib/auth/refreshTokens";

const mockUpsertUser = vi.mocked(db.user.upsert);
const mockIssueRefresh = vi.mocked(issueRefreshToken);

function passwordHash(password: string): string {
    const salt = randomBytes(16);
    const key = scryptSync(password, salt, 64);
    return `scrypt$${salt.toString("hex")}$${key.toString("hex")}`;
}

function makeRequest(body: unknown, origin = "http://localhost"): NextRequest {
    return new NextRequest("http://localhost/api/v1/auth/review-token", {
        method: "POST",
        body: JSON.stringify(body),
        headers: { "content-type": "application/json", origin },
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("APP_REVIEW_EMAIL", "app-review@laugh-track.com");
    vi.stubEnv("APP_REVIEW_PASSWORD_HASH", passwordHash("correct-password"));
    mockUpsertUser.mockResolvedValue({
        id: "review-user-123",
        email: "app-review@laugh-track.com",
    } as never);
});

afterEach(() => {
    vi.unstubAllEnvs();
});

describe("POST /api/v1/auth/review-token", () => {
    it("returns 404 when review auth is not configured", async () => {
        vi.stubEnv("APP_REVIEW_PASSWORD_HASH", "");

        const response = await POST(
            makeRequest({
                email: "app-review@laugh-track.com",
                password: "correct-password",
            }),
        );

        expect(response.status).toBe(404);
        expect(mockUpsertUser).not.toHaveBeenCalled();
    });

    it("rejects cross-origin requests", async () => {
        const response = await POST(
            makeRequest(
                {
                    email: "app-review@laugh-track.com",
                    password: "correct-password",
                },
                "https://attacker.example",
            ),
        );

        expect(response.status).toBe(403);
        expect(mockUpsertUser).not.toHaveBeenCalled();
    });

    it("returns one generic error for an invalid email or password", async () => {
        const wrongEmail = await POST(
            makeRequest({
                email: "other@example.com",
                password: "correct-password",
            }),
        );
        const wrongPassword = await POST(
            makeRequest({
                email: "app-review@laugh-track.com",
                password: "wrong-password",
            }),
        );

        expect(wrongEmail.status).toBe(401);
        expect(wrongPassword.status).toBe(401);
        await expect(wrongEmail.json()).resolves.toEqual({
            error: "invalid_credentials",
        });
        await expect(wrongPassword.json()).resolves.toEqual({
            error: "invalid_credentials",
        });
        expect(mockUpsertUser).not.toHaveBeenCalled();
    });

    it("ensures the review user exists and returns native tokens", async () => {
        const response = await POST(
            makeRequest({
                email: "  APP-REVIEW@laugh-track.com ",
                password: "correct-password",
            }),
        );
        const body = await response.json();

        expect(response.status).toBe(200);
        expect(response.headers.get("Cache-Control")).toBe("no-store");
        expect(body).toEqual({
            accessToken: "review-access-jwt",
            refreshToken: "review-refresh-token",
            expiresIn: 900,
        });
        expect(mockUpsertUser).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { email: "app-review@laugh-track.com" },
            }),
        );
        expect(mockIssueRefresh).toHaveBeenCalledWith("review-user-123");
    });
});
