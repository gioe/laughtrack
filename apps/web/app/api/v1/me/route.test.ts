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
    RATE_LIMITS: { authenticated: {}, authToken: {} },
    rateLimitHeaders: vi.fn(() => ({ "X-RateLimit-Remaining": "99" })),
    rateLimitResponse: vi.fn(() => new Response(null, { status: 429 }) as any),
}));

vi.mock("@/lib/auth/resolveAuth", () => ({
    resolveAuth: vi.fn(),
    PROFILE_MISSING: "PROFILE_MISSING",
}));

vi.mock("@/lib/db", () => ({
    db: {
        user: {
            findUnique: vi.fn(),
        },
    },
}));

import { GET } from "./route";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { db } from "@/lib/db";

const mockResolveAuth = vi.mocked(resolveAuth);
const mockCheckRateLimit = vi.mocked(checkRateLimit);
const mockRateLimitHeaders = vi.mocked(rateLimitHeaders);
const mockFindUser = vi.mocked(db.user.findUnique);

function makeRequest(): NextRequest {
    return new NextRequest("http://localhost/api/v1/me", { method: "GET" });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockCheckRateLimit.mockResolvedValue({
        allowed: true,
        limit: 100,
        remaining: 99,
        resetAt: 0,
    });
    mockRateLimitHeaders.mockReturnValue({ "X-RateLimit-Remaining": "99" });
});

describe("GET /api/v1/me", () => {
    it("returns 401 when resolveAuth returns null", async () => {
        mockResolveAuth.mockResolvedValue(null);

        const res = await GET(makeRequest());

        expect(res.status).toBe(401);
        expect(mockFindUser).not.toHaveBeenCalled();
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("99");
    });

    it("returns 422 when authenticated user has no UserProfile row", async () => {
        mockResolveAuth.mockResolvedValue(PROFILE_MISSING);

        const res = await GET(makeRequest());

        expect(res.status).toBe(422);
        const body = await res.json();
        expect(body).toEqual({ error: "profile_missing" });
        expect(mockFindUser).not.toHaveBeenCalled();
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("99");
    });

    it("returns 429 when the pre-auth IP rate limit is exceeded", async () => {
        mockCheckRateLimit.mockResolvedValueOnce({
            allowed: false,
            limit: 10,
            remaining: 0,
            resetAt: 0,
        });

        const res = await GET(makeRequest());

        expect(res.status).toBe(429);
        expect(mockResolveAuth).not.toHaveBeenCalled();
    });

    it("returns 429 when the per-user rate limit is exceeded", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        // First call (IP) allowed, second call (user) blocked.
        mockCheckRateLimit
            .mockResolvedValueOnce({
                allowed: true,
                limit: 10,
                remaining: 9,
                resetAt: 0,
            })
            .mockResolvedValueOnce({
                allowed: false,
                limit: 100,
                remaining: 0,
                resetAt: 0,
            });

        const res = await GET(makeRequest());

        expect(res.status).toBe(429);
        expect(mockFindUser).not.toHaveBeenCalled();
    });

    it("returns 401 when the User row is missing despite a valid AuthContext", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        mockFindUser.mockResolvedValue(null);

        const res = await GET(makeRequest());

        expect(res.status).toBe(401);
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("99");
    });

    it("returns 200 with display_name, email, and avatar_url on success", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        mockFindUser.mockResolvedValue({
            name: "Ada Lovelace",
            email: "ada@example.com",
            image: "https://cdn.example.com/avatar.png",
        } as any);

        const res = await GET(makeRequest());

        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body).toEqual({
            data: {
                display_name: "Ada Lovelace",
                email: "ada@example.com",
                avatar_url: "https://cdn.example.com/avatar.png",
            },
        });
        expect(res.headers.get("X-RateLimit-Remaining")).toBe("99");
        expect(mockFindUser).toHaveBeenCalledWith({
            where: { id: "user-123" },
            select: { name: true, email: true, image: true },
        });
    });

    it("returns nulls for display_name and avatar_url when User columns are null", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-123",
            profileId: "profile-123",
        });
        mockFindUser.mockResolvedValue({
            name: null,
            email: "anon@example.com",
            image: null,
        } as any);

        const res = await GET(makeRequest());

        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body).toEqual({
            data: {
                display_name: null,
                email: "anon@example.com",
                avatar_url: null,
            },
        });
    });

    it("keys rate limits by IP first, then by userId after auth resolves", async () => {
        mockResolveAuth.mockResolvedValue({
            userId: "user-abc",
            profileId: "profile-abc",
        });
        mockFindUser.mockResolvedValue({
            name: "X",
            email: "x@example.com",
            image: null,
        } as any);

        await GET(makeRequest());

        expect(mockCheckRateLimit).toHaveBeenNthCalledWith(
            1,
            "me-ip:127.0.0.1",
            expect.any(Object),
        );
        expect(mockCheckRateLimit).toHaveBeenNthCalledWith(
            2,
            "me:user-abc",
            expect.any(Object),
        );
    });
});
