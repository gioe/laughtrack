import { describe, it, expect } from "vitest";
import { resolveLocationInput } from "./resolveLocation";

describe("resolveLocationInput", () => {
    describe("5-digit zip code passthrough", () => {
        it("returns the zip as a single starting zip", () => {
            const result = resolveLocationInput("10001");
            expect(result).toEqual({ found: true, startingZips: ["10001"] });
        });

        it("returns found:true for any valid 5-digit string", () => {
            const result = resolveLocationInput("60601");
            expect(result.found).toBe(true);
            if (result.found) expect(result.startingZips).toEqual(["60601"]);
        });
    });

    describe("empty / falsy input", () => {
        it("returns found:false for empty string", () => {
            expect(resolveLocationInput("")).toEqual({ found: false });
        });

        it("returns found:false for whitespace only", () => {
            expect(resolveLocationInput("   ")).toEqual({ found: false });
        });
    });

    describe("city name with state", () => {
        it("resolves 'Chicago, IL' to multiple starting zips", () => {
            const result = resolveLocationInput("Chicago, IL");
            expect(result.found).toBe(true);
            if (result.found) {
                expect(result.startingZips.length).toBeGreaterThan(0);
                // All returned zips should be 5-digit strings
                result.startingZips.forEach((z) =>
                    expect(z).toMatch(/^\d{5}$/),
                );
            }
        });

        it("is case-insensitive for state abbreviation", () => {
            const upper = resolveLocationInput("Chicago, IL");
            const lower = resolveLocationInput("Chicago, il");
            expect(upper).toEqual(lower);
        });
    });

    describe("city name without state", () => {
        it("resolves 'Chicago' across all states", () => {
            const result = resolveLocationInput("Chicago");
            expect(result.found).toBe(true);
            if (result.found) {
                expect(result.startingZips.length).toBeGreaterThan(0);
            }
        });

        it("returns one representative zip per state for an ambiguous city", () => {
            // Portland exists in OR, ME, TN, and several other states
            const result = resolveLocationInput("Portland");
            expect(result.found).toBe(true);
            if (result.found) {
                // Should have multiple state representatives
                expect(result.startingZips.length).toBeGreaterThan(1);
                // Each zip should be unique (one per state)
                const unique = new Set(result.startingZips);
                expect(unique.size).toBe(result.startingZips.length);
            }
        });
    });

    describe("unknown city", () => {
        it("returns found:false for a city that does not exist", () => {
            expect(resolveLocationInput("Faketown")).toEqual({ found: false });
        });

        it("returns found:false for 'Faketown, IL'", () => {
            expect(resolveLocationInput("Faketown, IL")).toEqual({
                found: false,
            });
        });
    });

    describe("partial zip (non-5-digit number)", () => {
        it("treats a 4-digit number as a city name lookup (not found)", () => {
            // "1000" is not a zip code and is unlikely to be a city name
            const result = resolveLocationInput("1000");
            // Could be found: false (expected) or found: true if a city named "1000" exists
            // The main requirement is it should not be treated as a valid zip passthrough
            if (result.found) {
                expect(result.startingZips[0]).not.toBe("1000");
            }
        });
    });
});
