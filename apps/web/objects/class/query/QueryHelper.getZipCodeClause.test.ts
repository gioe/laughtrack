import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { QueryHelper } from "./QueryHelper";
import zipcodes from "zipcodes";
import { resolveLocationInput } from "@/util/location/resolveLocation";

function makeHelper(zip?: string, distance?: string): QueryHelper {
    return new QueryHelper({
        params: { zip, distance },
        timezone: "America/New_York",
    });
}

type ZipCodeClause = {
    zipCode: {
        equals?: string;
        in?: string[];
    };
};

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
        it.each(["94102", "01923"])(
            "retains origin %s with the real installed radius library",
            (origin) => {
                const helper = makeHelper(origin, "25");
                const clause = helper.getZipCodeClause() as ZipCodeClause;
                expect(clause.zipCode.in).toContain(origin);
                expect(clause.zipCode.in!.length).toBeGreaterThan(1);
                expect(helper.isZipCapTriggered()).toBe(false);
            },
        );

        it("returns exact match when no distance is provided", () => {
            const clause = makeHelper("10001", undefined).getZipCodeClause();
            expect(clause).toEqual({ zipCode: { equals: "10001" } });
        });

        it("returns an IN clause with nearby zips when distance is provided", () => {
            const clause = makeHelper("10001", "10").getZipCodeClause();
            expect(clause).toHaveProperty("zipCode.in");
            const zips = (clause as ZipCodeClause).zipCode.in as string[];
            expect(zips.length).toBeGreaterThan(1);
            expect(zips).toContain("10001");
        });
    });

    describe("city name input", () => {
        it("returns IN clause for a known city name with state", () => {
            const clause = makeHelper("Chicago, IL", "25").getZipCodeClause();
            expect(clause).toHaveProperty("zipCode.in");
            const zips = (clause as ZipCodeClause).zipCode.in as string[];
            expect(zips.length).toBeGreaterThan(0);
        });

        it("returns IN clause for a known city name without state", () => {
            const clause = makeHelper("Chicago", "25").getZipCodeClause();
            expect(clause).toHaveProperty("zipCode.in");
            const zips = (clause as ZipCodeClause).zipCode.in as string[];
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

            const singleZips = (singleCityClause as ZipCodeClause).zipCode
                .in as string[];
            const multiZips = (multiCityClause as ZipCodeClause).zipCode
                .in as string[];

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
                    ("equals" in (clause as ZipCodeClause).zipCode ||
                        "in" in (clause as ZipCodeClause).zipCode),
            ).toBe(true);
        });
    });

    describe("zip cap enforcement", () => {
        let radiusSpy: ReturnType<typeof vi.spyOn>;
        let warnSpy: ReturnType<typeof vi.spyOn>;

        beforeEach(() => {
            warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
        });

        afterEach(() => {
            radiusSpy?.mockRestore();
            warnSpy.mockRestore();
        });

        it.each([499, 500, 501, 600])(
            "counts a missing origin toward the cap with %i neighbors",
            (neighborCount) => {
                const neighbors = Array.from(
                    { length: neighborCount },
                    (_, i) => String(10000 + i),
                );
                radiusSpy = vi
                    .spyOn(zipcodes, "radius")
                    .mockReturnValue(neighbors as never);
                const helper = makeHelper("94102", "25");
                const zips = (helper.getZipCodeClause() as ZipCodeClause)
                    .zipCode.in!;

                expect(zips[0]).toBe("94102");
                expect(zips.filter((zip) => zip === "94102")).toHaveLength(1);
                expect(zips).toHaveLength(Math.min(neighborCount + 1, 500));
                expect(new Set(zips).size).toBe(zips.length);
                const capped = neighborCount + 1 > 500;
                expect(helper.isZipCapTriggered()).toBe(capped);
                expect(warnSpy).toHaveBeenCalledTimes(capped ? 1 : 0);
                if (capped) {
                    expect(warnSpy).toHaveBeenCalledWith(
                        expect.stringContaining(
                            `raw count=${neighborCount + 1}`,
                        ),
                    );
                }
            },
        );

        it("deduplicates an origin returned after the cap and as a ZIP object", () => {
            const neighbors = Array.from({ length: 500 }, (_, i) =>
                String(10000 + i),
            );
            radiusSpy = vi
                .spyOn(zipcodes, "radius")
                .mockReturnValue([
                    ...neighbors,
                    "94102",
                    { zip: "94102" },
                    neighbors[0],
                ] as never);
            const helper = makeHelper("94102", "25");
            const zips = (helper.getZipCodeClause() as ZipCodeClause).zipCode
                .in!;

            expect(zips).toEqual(["94102", ...neighbors.slice(0, 499)]);
            expect(helper.isZipCapTriggered()).toBe(true);
            expect(warnSpy).toHaveBeenCalledWith(
                expect.stringContaining("raw count=501"),
            );
        });

        it("reserves every ambiguous-city origin before capping the combined pool", () => {
            const resolution = resolveLocationInput("Portland");
            if (!resolution.found) throw new Error("Portland must resolve");
            const origins = resolution.startingZips;
            expect(origins.length).toBeGreaterThan(1);
            const neighbors = Array.from({ length: 600 }, (_, i) =>
                String(10000 + i),
            ).filter((zip) => !origins.includes(zip));
            radiusSpy = vi
                .spyOn(zipcodes, "radius")
                .mockReturnValue(neighbors as never);
            const helper = makeHelper("Portland", "25");
            const zips = (helper.getZipCodeClause() as ZipCodeClause).zipCode
                .in!;

            expect(zips.slice(0, origins.length)).toEqual(origins);
            expect(zips).toHaveLength(500);
            expect(new Set(zips).size).toBe(500);
            expect(radiusSpy).toHaveBeenCalledTimes(origins.length);
            for (const origin of origins) {
                expect(radiusSpy).toHaveBeenCalledWith(origin, 25);
            }
            expect(helper.isZipCapTriggered()).toBe(true);
            expect(warnSpy).toHaveBeenCalledOnce();
        });

        it("preserves all city origins when the library returns no neighbors", () => {
            const resolution = resolveLocationInput("Portland");
            if (!resolution.found) throw new Error("Portland must resolve");
            radiusSpy = vi.spyOn(zipcodes, "radius").mockReturnValue([]);
            const helper = makeHelper("Portland", "25");

            expect(helper.getZipCodeClause()).toEqual({
                zipCode: { in: resolution.startingZips },
            });
            expect(helper.isZipCapTriggered()).toBe(false);
            expect(warnSpy).not.toHaveBeenCalled();
        });

        it("preserves all city origins when the library throws", () => {
            const resolution = resolveLocationInput("Portland");
            if (!resolution.found) throw new Error("Portland must resolve");
            radiusSpy = vi.spyOn(zipcodes, "radius").mockImplementation(() => {
                throw new Error("radius failed");
            });
            const errorSpy = vi
                .spyOn(console, "error")
                .mockImplementation(() => {});
            try {
                const helper = makeHelper("Portland", "25");
                expect(helper.getZipCodeClause()).toEqual({
                    zipCode: { in: resolution.startingZips },
                });
                expect(helper.isZipCapTriggered()).toBe(false);
                expect(warnSpy).not.toHaveBeenCalled();
            } finally {
                errorSpy.mockRestore();
            }
        });

        it("caps the IN clause at 500 when the union exceeds the limit", () => {
            // Mock radius to return 600 unique zips for any starting zip
            const bigList = Array.from({ length: 600 }, (_, i) =>
                String(10000 + i).padStart(5, "0"),
            );
            radiusSpy = vi
                .spyOn(zipcodes, "radius")
                .mockReturnValue(bigList as never);

            const clause = makeHelper("10001", "25").getZipCodeClause();
            const zips = (clause as ZipCodeClause).zipCode.in as string[];
            expect(zips.length).toBe(500);
        });

        it("logs a warning with city and zip count when the cap is hit", () => {
            const bigList = Array.from({ length: 600 }, (_, i) =>
                String(10000 + i).padStart(5, "0"),
            );
            radiusSpy = vi
                .spyOn(zipcodes, "radius")
                .mockReturnValue(bigList as never);

            makeHelper("Portland", "25").getZipCodeClause();

            expect(warnSpy).toHaveBeenCalledOnce();
            const msg = warnSpy.mock.calls[0][0] as string;
            expect(msg).toContain("Portland");
            expect(msg).toContain("500");
            const resolution = resolveLocationInput("Portland");
            if (!resolution.found) throw new Error("Portland must resolve");
            const origins = resolution.startingZips;
            expect(msg).toContain(
                `raw count=${new Set([...origins, ...bigList]).size}`,
            );
        });

        it("does not warn when the zip count is at or below the cap", () => {
            const normalList = Array.from({ length: 100 }, (_, i) =>
                String(10000 + i).padStart(5, "0"),
            );
            radiusSpy = vi
                .spyOn(zipcodes, "radius")
                .mockReturnValue(normalList as never);

            makeHelper("10001", "25").getZipCodeClause();
            expect(warnSpy).not.toHaveBeenCalled();
        });

        it("isZipCapTriggered() returns true after a cap-triggering call", () => {
            const bigList = Array.from({ length: 600 }, (_, i) =>
                String(10000 + i).padStart(5, "0"),
            );
            radiusSpy = vi
                .spyOn(zipcodes, "radius")
                .mockReturnValue(bigList as never);

            const helper = makeHelper("10001", "25");
            helper.getZipCodeClause();
            expect(helper.isZipCapTriggered()).toBe(true);
        });

        it("isZipCapTriggered() returns false when the cap is not hit", () => {
            const normalList = Array.from({ length: 100 }, (_, i) =>
                String(10000 + i).padStart(5, "0"),
            );
            radiusSpy = vi
                .spyOn(zipcodes, "radius")
                .mockReturnValue(normalList as never);

            const helper = makeHelper("10001", "25");
            helper.getZipCodeClause();
            expect(helper.isZipCapTriggered()).toBe(false);
        });
    });
});
