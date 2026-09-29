import { afterEach, describe, expect, it, vi } from "vitest";
import zipcodes from "zipcodes";
import { resolveNearbyZips } from "./resolveNearbyZips";

describe("resolveNearbyZips", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it.each(["94102", "01923"])(
        "retains origin %s with the real installed radius library",
        (origin) => {
            const neighbors = zipcodes.radius(origin, 25);
            const result = resolveNearbyZips(origin, 25);
            expect(result).toContain(origin);
            expect(result).toEqual(
                [...new Set([origin, ...neighbors])].slice(0, 500),
            );
        },
    );

    it("caps expanded zip lists at 500 entries", () => {
        const bigList = Array.from({ length: 600 }, (_, index) =>
            String(10000 + index),
        );
        vi.spyOn(zipcodes, "radius").mockReturnValue(bigList as never);

        const zips = resolveNearbyZips("10001", 25);

        expect(zips).toHaveLength(500);
        expect(zips).toEqual(
            ["10001", ...bigList.filter((zip) => zip !== "10001")].slice(
                0,
                500,
            ),
        );
    });

    it("falls back to the input zip when the radius is invalid", () => {
        expect(resolveNearbyZips("10001", 501)).toEqual(["10001"]);
        expect(resolveNearbyZips("10001", 0)).toEqual(["10001"]);
        expect(resolveNearbyZips("10001", undefined)).toEqual(["10001"]);
    });
    describe("origin cap invariants", () => {
        it.each([499, 500, 501, 600])(
            "reserves the missing origin within a %i-neighbor pool",
            (count) => {
                const neighbors = Array.from({ length: count }, (_, i) =>
                    String(20000 + i),
                );
                vi.spyOn(zipcodes, "radius").mockReturnValue(neighbors);
                const result = resolveNearbyZips("01923", 25);
                expect(result).toEqual(["01923", ...neighbors].slice(0, 500));
                expect(result).toHaveLength(Math.min(count + 1, 500));
            },
        );
        it("retains an origin after the cap boundary exactly once", () => {
            const neighbors = Array.from({ length: 600 }, (_, i) =>
                String(20000 + i),
            );
            vi.spyOn(zipcodes, "radius").mockReturnValue([
                ...neighbors,
                "01923",
                "01923",
            ]);
            const result = resolveNearbyZips("01923", 25);
            expect(result).toEqual(["01923", ...neighbors.slice(0, 499)]);
            expect(result.filter((zip) => zip === "01923")).toHaveLength(1);
        });
        it("deduplicates object and string results while preserving neighbor order", () => {
            vi.spyOn(zipcodes, "radius").mockReturnValue([
                { zip: "01923" },
                "01923",
                "01960",
                { zip: "01960" },
                "01915",
            ] as never);
            expect(resolveNearbyZips("01923", 25)).toEqual([
                "01923",
                "01960",
                "01915",
            ]);
        });
        it.each([" 01923 ", "01923-1234", " 01923-1234 "])(
            "normalizes origin %s using the real library",
            (input) => {
                expect(resolveNearbyZips(input, 25)).toEqual(
                    resolveNearbyZips("01923", 25),
                );
                expect(resolveNearbyZips(input, 0)).toEqual(["01923"]);
            },
        );
        it.each([
            "",
            " ",
            "00000",
            "99999",
            "1923",
            "01923-123",
            "01923junk",
            "H2Y",
            "H2Y 1C6",
            "SW1A 1AA",
        ])(
            "rejects invalid or non-US input %s before radius expansion",
            (input) => {
                const radius = vi.spyOn(zipcodes, "radius");
                for (const distance of [undefined, 0, 25, 501])
                    expect(resolveNearbyZips(input, distance)).toEqual([]);
                expect(radius).not.toHaveBeenCalled();
            },
        );
        it("rejects a lookup outside the US", () => {
            vi.spyOn(zipcodes, "lookup").mockReturnValue({
                ...zipcodes.lookup("01923")!,
                country: "Canada",
            });
            const radius = vi.spyOn(zipcodes, "radius");
            expect(resolveNearbyZips("01923", 25)).toEqual([]);
            expect(radius).not.toHaveBeenCalled();
        });
        it.each([undefined, 0, -1, 501, NaN, Infinity])(
            "keeps normalized origin for invalid radius %s",
            (distance) => {
                const radius = vi.spyOn(zipcodes, "radius");
                expect(resolveNearbyZips(" 01923-1234 ", distance)).toEqual([
                    "01923",
                ]);
                expect(radius).not.toHaveBeenCalled();
            },
        );
        it("keeps origin when radius has no results", () => {
            vi.spyOn(zipcodes, "radius").mockReturnValue([]);
            expect(resolveNearbyZips("01923-1234", 25)).toEqual(["01923"]);
        });
        it("keeps origin when radius throws", () => {
            vi.spyOn(zipcodes, "radius").mockImplementation(() => {
                throw new Error("radius unavailable");
            });
            expect(resolveNearbyZips("01923-1234", 25)).toEqual(["01923"]);
        });
    });
});
