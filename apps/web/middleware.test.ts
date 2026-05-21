import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { middleware, setParamDefaults } from "./middleware";
import { QueryProperty } from "./objects/enum";
import { getToken } from "next-auth/jwt";

vi.mock("next-auth/jwt", () => ({
    getToken: vi.fn(),
}));

const mockGetToken = vi.mocked(getToken);

function makeRequest(path: string, headers?: HeadersInit): NextRequest {
    return new NextRequest(`https://www.laugh-track.com${path}`, { headers });
}

function expectRedirectTo(response: Response, expectedPathAndSearch: string) {
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe(
        `https://www.laugh-track.com${expectedPathAndSearch}`,
    );
}

function authToken(sub?: string) {
    return {
        accessTokenExp: Math.floor(Date.now() / 1000) + 60,
        ...(sub ? { sub } : {}),
    };
}

beforeEach(() => {
    mockGetToken.mockReset();
});

describe("setParamDefaults", () => {
    it("uses a smaller default page size for comedian detail pages", () => {
        const params = setParamDefaults(
            new URLSearchParams(),
            "/comedian/Taylor-Tomlinson",
        );

        expect(params.get(QueryProperty.Size)).toBe("5");
    });

    it("keeps the standard default page size for comedian search", () => {
        const params = setParamDefaults(
            new URLSearchParams(),
            "/comedian/search",
        );

        expect(params.get(QueryProperty.Size)).toBe("20");
    });

    it("does not override explicit page sizes on comedian detail pages", () => {
        const params = setParamDefaults(
            new URLSearchParams("size=20"),
            "/comedian/Taylor-Tomlinson",
        );

        expect(params.get(QueryProperty.Size)).toBe("20");
    });

    it("uses a profile zip when defaulting zip parameters", () => {
        const params = setParamDefaults(new URLSearchParams(), "/show/search", {
            id: "user-1",
            email: "user@example.com",
            role: "user",
            zipCode: "90210",
        });

        expect(params.get(QueryProperty.Zip)).toBe("90210");
        expect(params.get(QueryProperty.Sort)).toBe("date_asc");
    });

    it("uses podcast-specific search sort defaults", () => {
        const params = setParamDefaults(
            new URLSearchParams(),
            "/podcast/search",
        );

        expect(params.get(QueryProperty.Sort)).toBe("show_count_desc");
    });
});

describe("middleware SEO headers", () => {
    it("adds noindex to non-canonical hosts", async () => {
        const response = await middleware(
            new NextRequest("https://laughtrack.vercel.app/club/search"),
        );

        expect(response.headers.get("X-Robots-Tag")).toBe("noindex");
    });

    it("does not add noindex to canonical hosts", async () => {
        const response = await middleware(
            new NextRequest("https://www.laugh-track.com/club/search"),
        );

        expect(response.headers.get("X-Robots-Tag")).toBeNull();
    });
});

describe("middleware API handling", () => {
    it("adds CORS and security headers to API preflight responses", async () => {
        const response = await middleware(
            new NextRequest("https://www.laugh-track.com/api/v1/clubs/search", {
                method: "OPTIONS",
                headers: { origin: "laughtrack.b-cdn.net" },
            }),
        );

        expect(response.status).toBe(200);
        expect(response.headers.get("Access-Control-Allow-Origin")).toBe(
            "laughtrack.b-cdn.net",
        );
        expect(response.headers.get("X-Frame-Options")).toBe("DENY");
    });

    it("adds CORS and security headers to non-preflight API responses", async () => {
        const response = await middleware(
            new NextRequest("https://www.laugh-track.com/api/v1/clubs/search", {
                headers: { origin: "laughtrack.b-cdn.net" },
            }),
        );

        expect(response.status).toBe(200);
        expect(response.headers.get("Access-Control-Allow-Origin")).toBe(
            "laughtrack.b-cdn.net",
        );
        expect(response.headers.get("X-Frame-Options")).toBe("DENY");
    });
});

describe("middleware auth redirects", () => {
    it("redirects an unauthenticated protected route request to login with a callback", async () => {
        mockGetToken.mockResolvedValue(null);

        const response = await middleware(makeRequest("/profile"));

        expect(mockGetToken).toHaveBeenCalledOnce();
        expectRedirectTo(response, "/?callbackUrl=%2Fprofile");
        expect(response.headers.get("X-Frame-Options")).toBe("DENY");
    });

    it("treats an expired JWT on a protected route as unauthenticated", async () => {
        mockGetToken.mockResolvedValue(null);

        const response = await middleware(
            makeRequest("/profile/user-1", {
                cookie: "authjs.session-token=expired-token",
            }),
        );

        expect(mockGetToken).toHaveBeenCalledOnce();
        expectRedirectTo(response, "/?callbackUrl=%2Fprofile%2Fuser-1");
    });

    it("redirects protected profile requests when the token lacks a user id", async () => {
        mockGetToken.mockResolvedValue(authToken());

        const response = await middleware(makeRequest("/profile/user-1"));

        expectRedirectTo(response, "/");
    });

    it("redirects authenticated users away from another user's profile", async () => {
        mockGetToken.mockResolvedValue(authToken("user-1"));

        const response = await middleware(makeRequest("/profile/user-2"));

        expectRedirectTo(response, "/profile/user-1");
    });

    it("rewrites an authenticated user's own profile route", async () => {
        mockGetToken.mockResolvedValue(authToken("user-1"));

        const response = await middleware(makeRequest("/profile/user-1"));

        expect(response.status).toBe(200);
        expect(response.headers.get("location")).toBeNull();
        expect(response.headers.get("x-middleware-rewrite")).toBe(
            "https://www.laugh-track.com/profile/user-1?page=1&size=20&direction=asc&zip=&distance=5",
        );
    });

    it("does not redirect an authenticated user visiting a public route", async () => {
        mockGetToken.mockResolvedValue(authToken("user-1"));

        const response = await middleware(makeRequest("/club/search"));

        expect(mockGetToken).not.toHaveBeenCalled();
        expect(response.status).toBe(200);
        expect(response.headers.get("location")).toBeNull();
        expect(response.headers.get("x-middleware-rewrite")).toBe(
            "https://www.laugh-track.com/club/search?sort=total_shows_desc&page=1&size=20&direction=asc&zip=&distance=5",
        );
    });
});
