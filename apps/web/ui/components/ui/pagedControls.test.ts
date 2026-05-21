import { describe, expect, it } from "vitest";
import { buildPageWindow } from "./pagedControls";

describe("buildPageWindow", () => {
    it("returns every page when totalPages is small", () => {
        expect(buildPageWindow(1, 1)).toEqual([1]);
        expect(buildPageWindow(3, 5)).toEqual([1, 2, 3, 4, 5]);
        expect(buildPageWindow(4, 7)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    });

    it("inserts a single ellipsis at the high end near page 1", () => {
        expect(buildPageWindow(1, 20)).toEqual([1, 2, "ellipsis", 20]);
        expect(buildPageWindow(2, 20)).toEqual([1, 2, 3, "ellipsis", 20]);
    });

    it("inserts a single ellipsis at the low end near the last page", () => {
        expect(buildPageWindow(20, 20)).toEqual([1, "ellipsis", 19, 20]);
        expect(buildPageWindow(19, 20)).toEqual([1, "ellipsis", 18, 19, 20]);
    });

    it("inserts ellipses on both sides for a middle page", () => {
        expect(buildPageWindow(10, 20)).toEqual([
            1,
            "ellipsis",
            9,
            10,
            11,
            "ellipsis",
            20,
        ]);
    });
});
