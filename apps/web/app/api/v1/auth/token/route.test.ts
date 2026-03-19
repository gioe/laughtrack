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
    generateToken: vi.fn(() => "mock-jwt-token"),
}));

import { POST } from "./route";
import { auth } from "@/auth";

const mockAuth = vi.mocked(auth);

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

    it("returns 401 when session has no user email (profile absent)", async () => {
        mockAuth.mockResolvedValue({ user: {} } as any);

        const res = await POST(makeRequest());

        expect(res.status).toBe(401);
    });

    it("returns 200 with token on valid session", async () => {
        mockAuth.mockResolvedValue({
            user: { email: "user@example.com" },
        } as any);

        const res = await POST(makeRequest());
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ token: "mock-jwt-token" });
    });
});
