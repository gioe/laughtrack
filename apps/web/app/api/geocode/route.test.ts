import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

// Prevent next-auth (and its next/server import) from loading via the rateLimit chain
vi.mock("@/lib/rateLimit", () => ({
    checkRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 100,
            remaining: 99,
            resetAt: 0,
        }),
    ),
    getClientIp: vi.fn(() => "127.0.0.1"),
    RATE_LIMITS: { publicRead: {}, publicReadAuth: {} },
    rateLimitHeaders: vi.fn(() => ({})),
    rateLimitResponse: vi.fn(),
    applyPublicReadRateLimit: vi.fn(() =>
        Promise.resolve({
            allowed: true,
            limit: 60,
            remaining: 59,
            resetAt: 0,
        }),
    ),
}));

import { GET } from "./route";

function makeRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/geocode");
    for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
    }
    return new NextRequest(url.toString());
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("GET /api/geocode", () => {
    it("returns 200 with { zip } for valid US coordinates", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                json: async () => ({ address: { postcode: "10001" } }),
            }),
        );

        const res = await GET(makeRequest({ lat: "40.7128", lng: "-74.0060" }));
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ zip: "10001" });
    });

    it("extracts 5-digit zip from hyphenated postcode", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                json: async () => ({ address: { postcode: "10001-1234" } }),
            }),
        );

        const res = await GET(makeRequest({ lat: "40.7128", lng: "-74.0060" }));
        const body = await res.json();

        expect(res.status).toBe(200);
        expect(body).toEqual({ zip: "10001" });
    });

    it("returns 400 when lat is non-numeric", async () => {
        const res = await GET(makeRequest({ lat: "abc", lng: "-74.0060" }));
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body).toHaveProperty("error");
    });

    it("returns 400 when lat is out of range", async () => {
        const res = await GET(makeRequest({ lat: "999", lng: "-74.0060" }));
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body).toHaveProperty("error");
    });

    it("returns 400 when lng is non-numeric", async () => {
        const res = await GET(makeRequest({ lat: "40.7128", lng: "xyz" }));
        const body = await res.json();

        expect(res.status).toBe(400);
        expect(body).toHaveProperty("error");
    });

    it("returns 404 when Nominatim returns a non-5-digit postcode", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                json: async () => ({ address: { postcode: "SW1A 1AA" } }),
            }),
        );

        const res = await GET(makeRequest({ lat: "51.5074", lng: "-0.1278" }));
        const body = await res.json();

        expect(res.status).toBe(404);
        expect(body).toHaveProperty("error");
    });

    it("returns 404 when Nominatim returns no postcode", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                json: async () => ({ address: {} }),
            }),
        );

        const res = await GET(makeRequest({ lat: "0", lng: "0" }));
        const body = await res.json();

        expect(res.status).toBe(404);
        expect(body).toHaveProperty("error");
    });

    it("returns 502 when Nominatim responds with non-ok status", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: false,
                status: 503,
            }),
        );

        const res = await GET(makeRequest({ lat: "40.7128", lng: "-74.0060" }));
        const body = await res.json();

        expect(res.status).toBe(502);
        expect(body).toHaveProperty("error");
    });
});
