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
});
