import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

const mockCheckRateLimit = vi.fn();

vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: mockCheckRateLimit,
    getClientIp: () => "127.0.0.1",
    RATE_LIMITS: { authToken: { limit: 10, windowMs: 60_000 } },
    rateLimitResponse: () => new NextResponse(null, { status: 429 }),
}));

describe("GET /api/v1/auth/native/callback", () => {
    beforeEach(() => {
        mockCheckRateLimit.mockReset();
        mockCheckRateLimit.mockResolvedValue({
            allowed: true,
            limit: 10,
            remaining: 9,
            resetAt: Date.now() + 60_000,
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("redirects back into the app with the exchanged tokens", async () => {
        vi.spyOn(global, "fetch").mockResolvedValue(
            new Response(
                JSON.stringify({
                    accessToken: "access-jwt",
                    refreshToken: "opaque-refresh",
                    expiresIn: 900,
                }),
                {
                    status: 200,
                    headers: { "content-type": "application/json" },
                },
            ),
        );

        const { GET } = await import("./route");
        const response = await GET(
            new NextRequest(
                "https://laughtrack.app/api/v1/auth/native/callback?provider=google",
                {
                    headers: {
                        cookie: "next-auth.session-token=session-cookie",
                    },
                },
            ),
        );

        expect(response.status).toBe(307);
        expect(response.headers.get("location")).toBe(
            "laughtrack://auth/callback?provider=google&accessToken=access-jwt&refreshToken=opaque-refresh&expiresIn=900",
        );
        expect(global.fetch).toHaveBeenCalledWith(
            "https://laughtrack.app/api/v1/auth/token",
            expect.objectContaining({
                method: "POST",
                headers: expect.objectContaining({
                    cookie: "next-auth.session-token=session-cookie",
                    origin: "https://laughtrack.app",
                }),
            }),
        );
    });

    it("preserves upstream oauth errors", async () => {
        const { GET } = await import("./route");
        const response = await GET(
            new NextRequest(
                "https://laughtrack.app/api/v1/auth/native/callback?provider=apple&error=AccessDenied",
            ),
        );

        expect(response.status).toBe(307);
        expect(response.headers.get("location")).toBe(
            "laughtrack://auth/callback?provider=apple&error=AccessDenied",
        );
    });

    it("returns a token exchange error when the session exchange fails", async () => {
        vi.spyOn(global, "fetch").mockResolvedValue(
            new Response(JSON.stringify({ message: "Unauthorized" }), {
                status: 401,
                headers: { "content-type": "application/json" },
            }),
        );

        const { GET } = await import("./route");
        const response = await GET(
            new NextRequest(
                "https://laughtrack.app/api/v1/auth/native/callback?provider=google",
            ),
        );

        expect(response.status).toBe(307);
        expect(response.headers.get("location")).toBe(
            "laughtrack://auth/callback?provider=google&error=token_exchange_failed_401",
        );
    });

    it("returns 429 when the rate limit is exceeded", async () => {
        mockCheckRateLimit.mockResolvedValue({
            allowed: false,
            limit: 10,
            remaining: 0,
            resetAt: Date.now() + 60_000,
        });
        const fetchSpy = vi.spyOn(global, "fetch");

        const { GET } = await import("./route");
        const response = await GET(
            new NextRequest(
                "https://laughtrack.app/api/v1/auth/native/callback?provider=google",
            ),
        );

        expect(response.status).toBe(429);
        expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("ignores attacker-supplied laughtrack:// deep_link hosts and falls back to canonical", async () => {
        vi.spyOn(global, "fetch").mockResolvedValue(
            new Response(
                JSON.stringify({
                    accessToken: "access-jwt",
                    refreshToken: "opaque-refresh",
                    expiresIn: 900,
                }),
                {
                    status: 200,
                    headers: { "content-type": "application/json" },
                },
            ),
        );

        const { GET } = await import("./route");
        const response = await GET(
            new NextRequest(
                "https://laughtrack.app/api/v1/auth/native/callback?provider=google&deep_link=laughtrack%3A%2F%2Fattacker-host%2Fexfil",
            ),
        );

        expect(response.status).toBe(307);
        expect(response.headers.get("location")).toBe(
            "laughtrack://auth/callback?provider=google&accessToken=access-jwt&refreshToken=opaque-refresh&expiresIn=900",
        );
    });

    it("falls back to the canonical deep link for non-laughtrack callbackUrl values", async () => {
        vi.spyOn(global, "fetch").mockResolvedValue(
            new Response(
                JSON.stringify({
                    accessToken: "access-jwt",
                    refreshToken: "opaque-refresh",
                    expiresIn: 900,
                }),
                {
                    status: 200,
                    headers: { "content-type": "application/json" },
                },
            ),
        );

        const { GET } = await import("./route");
        const response = await GET(
            new NextRequest(
                "https://laughtrack.app/api/v1/auth/native/callback?provider=google&callbackUrl=https%3A%2F%2Fattacker.example%2Fexfil",
            ),
        );

        expect(response.status).toBe(307);
        expect(response.headers.get("location")).toBe(
            "laughtrack://auth/callback?provider=google&accessToken=access-jwt&refreshToken=opaque-refresh&expiresIn=900",
        );
    });

    // Even when the deep_link's scheme/host/path matches canonical, query
    // params, fragments, and userinfo on the supplied URL must be stripped —
    // the redirect base is hard-coded and never reflects user input.
    it.each([
        [
            "smuggled query params on a canonical-looking deep_link",
            "deep_link=laughtrack%3A%2F%2Fauth%2Fcallback%3Fevil%3D1",
        ],
        [
            "smuggled fragment on a canonical-looking deep_link",
            "deep_link=laughtrack%3A%2F%2Fauth%2Fcallback%23frag%3Devil",
        ],
        [
            "smuggled userinfo on a canonical-looking deep_link",
            "deep_link=laughtrack%3A%2F%2Fevil%40auth%2Fcallback",
        ],
    ])("strips %s", async (_label, queryFragment) => {
        vi.spyOn(global, "fetch").mockResolvedValue(
            new Response(
                JSON.stringify({
                    accessToken: "access-jwt",
                    refreshToken: "opaque-refresh",
                    expiresIn: 900,
                }),
                {
                    status: 200,
                    headers: { "content-type": "application/json" },
                },
            ),
        );

        const { GET } = await import("./route");
        const response = await GET(
            new NextRequest(
                `https://laughtrack.app/api/v1/auth/native/callback?provider=google&${queryFragment}`,
            ),
        );

        expect(response.status).toBe(307);
        expect(response.headers.get("location")).toBe(
            "laughtrack://auth/callback?provider=google&accessToken=access-jwt&refreshToken=opaque-refresh&expiresIn=900",
        );
    });

    it("drops unknown provider values from the redirect", async () => {
        vi.spyOn(global, "fetch").mockResolvedValue(
            new Response(
                JSON.stringify({
                    accessToken: "access-jwt",
                    refreshToken: "opaque-refresh",
                    expiresIn: 900,
                }),
                {
                    status: 200,
                    headers: { "content-type": "application/json" },
                },
            ),
        );

        const { GET } = await import("./route");
        const response = await GET(
            new NextRequest(
                "https://laughtrack.app/api/v1/auth/native/callback?provider=evil",
            ),
        );

        expect(response.status).toBe(307);
        expect(response.headers.get("location")).toBe(
            "laughtrack://auth/callback?accessToken=access-jwt&refreshToken=opaque-refresh&expiresIn=900",
        );
    });
});
