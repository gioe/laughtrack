import { describe, it, expect, vi, beforeEach } from "vitest";

const mockHeadersGet = vi.fn<(key: string) => string | null>();
const mockHeadersFn = vi.fn(async () => ({ get: mockHeadersGet }));

vi.mock("next/headers", () => ({
    headers: () => mockHeadersFn(),
}));

vi.mock("zipcodes", () => ({
    default: {
        lookup: vi.fn(),
    },
}));

import { getHeroContext } from "./getHeroContext";
import zipcodesMod from "zipcodes";

const mockLookup = vi.mocked(zipcodesMod.lookup);

function withHeaders(map: Record<string, string | null | undefined>): void {
    mockHeadersGet.mockImplementation((key: string) => {
        const value = map[key];
        return value == null ? null : value;
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    mockHeadersGet.mockReturnValue(null);
    mockHeadersFn.mockImplementation(async () => ({ get: mockHeadersGet }));
});

describe("getHeroContext", () => {
    it("prefers session zip and looks up city/state", async () => {
        withHeaders({
            "x-vercel-ip-country": "US",
            "x-vercel-ip-postal-code": "10001",
            "x-vercel-ip-city": "Los Angeles",
            "x-vercel-ip-country-region": "CA",
        });
        mockLookup.mockReturnValue({
            zip: "78701",
            city: "Austin",
            state: "TX",
            latitude: 30.27,
            longitude: -97.74,
            country: "US",
        } as ReturnType<typeof zipcodesMod.lookup>);

        const ctx = await getHeroContext("78701");

        expect(ctx.zipCode).toBe("78701");
        expect(ctx.city).toBe("Austin");
        expect(ctx.state).toBe("TX");
        expect(mockLookup).toHaveBeenCalledWith("78701");
    });

    it("falls back to geo-IP zip when session zip is absent", async () => {
        withHeaders({
            "x-vercel-ip-country": "US",
            "x-vercel-ip-postal-code": "94103",
            "x-vercel-ip-city": "San Francisco",
            "x-vercel-ip-country-region": "CA",
        });
        mockLookup.mockReturnValue({
            zip: "94103",
            city: "San Francisco",
            state: "CA",
            latitude: 37.77,
            longitude: -122.41,
            country: "US",
        } as ReturnType<typeof zipcodesMod.lookup>);

        const ctx = await getHeroContext(null);

        expect(ctx.zipCode).toBe("94103");
        expect(ctx.city).toBe("San Francisco");
        expect(ctx.state).toBe("CA");
    });

    it("uses geo-IP city when zip lookup returns nothing", async () => {
        withHeaders({
            "x-vercel-ip-country": "US",
            "x-vercel-ip-postal-code": "00000",
            "x-vercel-ip-city": "Anytown",
            "x-vercel-ip-country-region": "xx",
        });
        mockLookup.mockReturnValue(
            undefined as ReturnType<typeof zipcodesMod.lookup>,
        );

        const ctx = await getHeroContext(null);

        expect(ctx.zipCode).toBe("00000");
        expect(ctx.city).toBe("Anytown");
        expect(ctx.state).toBe("XX");
    });

    it("returns all-null when neither session nor geo-IP is available", async () => {
        withHeaders({});

        const ctx = await getHeroContext(null);

        expect(ctx).toEqual({ zipCode: null, city: null, state: null });
        expect(mockLookup).not.toHaveBeenCalled();
    });

    it("decodes URI-encoded geo-IP city headers", async () => {
        withHeaders({
            "x-vercel-ip-country": "US",
            "x-vercel-ip-postal-code": null,
            "x-vercel-ip-city": "New%20York",
            "x-vercel-ip-country-region": "NY",
        });

        const ctx = await getHeroContext(null);

        expect(ctx.city).toBe("New York");
        expect(ctx.state).toBe("NY");
        expect(ctx.zipCode).toBe(null);
    });

    it("rejects malformed session zip and falls through to geo-IP", async () => {
        withHeaders({
            "x-vercel-ip-country": "US",
            "x-vercel-ip-postal-code": "30301",
            "x-vercel-ip-city": "Atlanta",
            "x-vercel-ip-country-region": "GA",
        });
        mockLookup.mockReturnValue({
            zip: "30301",
            city: "Atlanta",
            state: "GA",
            latitude: 33.75,
            longitude: -84.39,
            country: "US",
        } as ReturnType<typeof zipcodesMod.lookup>);

        const ctx = await getHeroContext("not-a-zip");

        expect(ctx.zipCode).toBe("30301");
        expect(ctx.city).toBe("Atlanta");
    });

    it("strips ZIP+4 session zip to 5 digits before lookup", async () => {
        mockLookup.mockReturnValue({
            zip: "60601",
            city: "Chicago",
            state: "IL",
            latitude: 41.88,
            longitude: -87.63,
            country: "US",
        } as ReturnType<typeof zipcodesMod.lookup>);

        const ctx = await getHeroContext("60601-1234");

        expect(ctx.zipCode).toBe("60601");
        expect(mockLookup).toHaveBeenCalledWith("60601");
    });

    it("ignores non-US geo-IP headers (e.g., German 5-digit postal codes)", async () => {
        withHeaders({
            "x-vercel-ip-country": "DE",
            "x-vercel-ip-postal-code": "10115",
            "x-vercel-ip-city": "Berlin",
            "x-vercel-ip-country-region": "BE",
        });

        const ctx = await getHeroContext(null);

        expect(ctx).toEqual({ zipCode: null, city: null, state: null });
        expect(mockLookup).not.toHaveBeenCalled();
    });

    it("drops malformed state codes (not 2 uppercase letters)", async () => {
        withHeaders({
            "x-vercel-ip-country": "US",
            "x-vercel-ip-postal-code": null,
            "x-vercel-ip-city": "Sacramento",
            "x-vercel-ip-country-region": "California",
        });

        const ctx = await getHeroContext(null);

        expect(ctx.city).toBe("Sacramento");
        expect(ctx.state).toBe(null);
    });

    it("returns all-null when headers() throws (outside a request context)", async () => {
        mockHeadersFn.mockImplementationOnce(async () => {
            throw new Error("headers() called outside request scope");
        });

        const ctx = await getHeroContext(null);

        expect(ctx).toEqual({ zipCode: null, city: null, state: null });
    });

    it("survives zipcodes.lookup throwing and falls back to geo-IP fields", async () => {
        withHeaders({
            "x-vercel-ip-country": "US",
            "x-vercel-ip-postal-code": "02108",
            "x-vercel-ip-city": "Boston",
            "x-vercel-ip-country-region": "MA",
        });
        mockLookup.mockImplementation(() => {
            throw new Error("zipcodes dataset corrupted");
        });

        const ctx = await getHeroContext(null);

        expect(ctx.zipCode).toBe("02108");
        expect(ctx.city).toBe("Boston");
        expect(ctx.state).toBe("MA");
    });
});
