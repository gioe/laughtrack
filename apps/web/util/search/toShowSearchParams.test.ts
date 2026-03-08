import { describe, it, expect } from "vitest";
import { toSearchParams } from "./toShowSearchParams";

describe("toSearchParams", () => {
    it("returns undefined for absent keys", () => {
        const result = toSearchParams({});
        expect(result.fromDate).toBeUndefined();
        expect(result.toDate).toBeUndefined();
        expect(result.filters).toBeUndefined();
        expect(result.zip).toBeUndefined();
        expect(result.distance).toBeUndefined();
        expect(result.comedian).toBeUndefined();
        expect(result.club).toBeUndefined();
        expect(result.sort).toBeUndefined();
        expect(result.page).toBeUndefined();
        expect(result.size).toBeUndefined();
    });

    it("passes scalar string values through unchanged", () => {
        const raw = {
            fromDate: "2025-01-01",
            toDate: "2025-12-31",
            filters: "open-mic",
            zip: "90210",
            distance: "25",
            comedian: "jerry-seinfeld",
            club: "laugh-factory",
            sort: "date",
            page: "2",
            size: "10",
        };
        const result = toSearchParams(raw);
        expect(result.fromDate).toBe("2025-01-01");
        expect(result.toDate).toBe("2025-12-31");
        expect(result.filters).toBe("open-mic");
        expect(result.zip).toBe("90210");
        expect(result.distance).toBe("25");
        expect(result.comedian).toBe("jerry-seinfeld");
        expect(result.club).toBe("laugh-factory");
        expect(result.sort).toBe("date");
        expect(result.page).toBe("2");
        expect(result.size).toBe("10");
    });

    it("coerces string[] to the first element", () => {
        const result = toSearchParams({ zip: ["10001", "10002"] });
        expect(result.zip).toBe("10001");
    });

    it("coerces string[] for every field, returning first element", () => {
        const raw = {
            fromDate: ["2025-01-01", "2025-06-01"],
            toDate: ["2025-12-31", "2026-01-01"],
            filters: ["open-mic", "headliner"],
            zip: ["90210", "10001"],
            distance: ["50", "100"],
            comedian: ["abc", "def"],
            club: ["laugh-factory", "comedy-cellar"],
            sort: ["date", "name"],
            page: ["3", "1"],
            size: ["20", "50"],
        };
        const result = toSearchParams(raw);
        expect(result.fromDate).toBe("2025-01-01");
        expect(result.toDate).toBe("2025-12-31");
        expect(result.filters).toBe("open-mic");
        expect(result.zip).toBe("90210");
        expect(result.distance).toBe("50");
        expect(result.comedian).toBe("abc");
        expect(result.club).toBe("laugh-factory");
        expect(result.sort).toBe("date");
        expect(result.page).toBe("3");
        expect(result.size).toBe("20");
    });

    it("handles mixed present and absent fields", () => {
        const result = toSearchParams({ zip: "94105", page: "1" });
        expect(result.zip).toBe("94105");
        expect(result.page).toBe("1");
        expect(result.comedian).toBeUndefined();
        expect(result.club).toBeUndefined();
    });
});
