import { describe, it, expect } from "vitest";
import { QueryHelper } from "./QueryHelper";

function makeHelper(zip?: string, distance?: string): QueryHelper {
    return new QueryHelper({
        params: { zip, distance },
        timezone: "America/New_York",
    });
}

describe("QueryHelper.getZipCodeClause", () => {
    describe("no location input", () => {
        it("returns empty object when zip is undefined", () => {
            expect(makeHelper(undefined, "25").getZipCodeClause()).toEqual({});
        });

        it("returns empty object when zip is empty string", () => {
            expect(makeHelper("", "25").getZipCodeClause()).toEqual({});
        });
    });

    describe("5-digit zip code input", () => {
        it("returns exact match when no distance is provided", () => {
            const clause = makeHelper("10001", undefined).getZipCodeClause();
            expect(clause).toEqual({ zipCode: { equals: "10001" } });
        });

        it("returns an IN clause with nearby zips when distance is provided", () => {
            const clause = makeHelper("10001", "10").getZipCodeClause();
            expect(clause).toHaveProperty("zipCode.in");
            const zips = (clause as any).zipCode.in as string[];
            expect(zips.length).toBeGreaterThan(1);
            expect(zips).toContain("10001");
        });
    });

    describe("city name input", () => {
        it("returns IN clause for a known city name with state", () => {
            const clause = makeHelper("Chicago, IL", "25").getZipCodeClause();
            expect(clause).toHaveProperty("zipCode.in");
            const zips = (clause as any).zipCode.in as string[];
            expect(zips.length).toBeGreaterThan(0);
        });

        it("returns IN clause for a known city name without state", () => {
            const clause = makeHelper("Chicago", "25").getZipCodeClause();
            expect(clause).toHaveProperty("zipCode.in");
            const zips = (clause as any).zipCode.in as string[];
            expect(zips.length).toBeGreaterThan(0);
        });

        it("returns exact-match-on-empty for unresolvable city name", () => {
            // Unknown city → resolveLocationInput returns found:false →
            // clause should match nothing
            const clause = makeHelper("Faketown", "25").getZipCodeClause();
            expect(clause).toEqual({ zipCode: { equals: "" } });
        });

        it("expands radius from each state cluster for ambiguous city names", () => {
            // Portland exists in OR, ME, TN, and several other states;
            // the combined IN list should be larger than a single-city expansion.
            const singleCityClause = makeHelper(
                "Chicago, IL",
                "25",
            ).getZipCodeClause();
            const multiCityClause = makeHelper(
                "Portland",
                "25",
            ).getZipCodeClause();

            const singleZips = (singleCityClause as any).zipCode.in as string[];
            const multiZips = (multiCityClause as any).zipCode.in as string[];

            // Portland across many states should yield more unique zips than
            // a single-state city at the same radius
            expect(multiZips.length).toBeGreaterThan(singleZips.length);
        });

        it("falls back to exact match when no distance is provided for a city", () => {
            // No valid radius → returns the starting zip(s) as exact/in match
            const clause = makeHelper(
                "Chicago, IL",
                undefined,
            ).getZipCodeClause();
            // Could be { equals: "xxxxx" } or { in: [...] } depending on number of zips
            expect(
                "zipCode" in clause &&
                    ("equals" in (clause as any).zipCode ||
                        "in" in (clause as any).zipCode),
            ).toBe(true);
        });
    });
});
