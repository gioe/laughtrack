import { afterEach, describe, expect, it, vi } from "vitest";
import zipcodes from "zipcodes";
import { resolveNearbyZips } from "./resolveNearbyZips";

describe("resolveNearbyZips", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("caps expanded zip lists at 500 entries", () => {
        const bigList = Array.from({ length: 600 }, (_, index) =>
            String(10000 + index),
        );
        vi.spyOn(zipcodes, "radius").mockReturnValue(bigList as never);

        const zips = resolveNearbyZips("10001", 25);

        expect(zips).toHaveLength(500);
        expect(zips).toEqual(bigList.slice(0, 500));
    });

    it("falls back to the input zip when the radius is invalid", () => {
        expect(resolveNearbyZips("10001", 501)).toEqual(["10001"]);
        expect(resolveNearbyZips("10001", 0)).toEqual(["10001"]);
        expect(resolveNearbyZips("10001", undefined)).toEqual(["10001"]);
    });
});
