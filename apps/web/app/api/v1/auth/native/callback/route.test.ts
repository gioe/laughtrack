import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET } from "./route";

describe("GET /api/v1/auth/native/callback", () => {
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
});
