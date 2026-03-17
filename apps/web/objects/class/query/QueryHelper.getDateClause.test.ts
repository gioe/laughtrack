import { describe, it, expect } from "vitest";
import { QueryHelper } from "./QueryHelper";

function makeHelper(params: Record<string, string | undefined> = {}) {
    return new QueryHelper({
        params,
        timezone: "America/New_York",
    });
}

describe("QueryHelper.getDateClause", () => {
    describe("default — no fromDate provided", () => {
        it("returns a gte filter using the current time when fromDate is absent", () => {
            const before = Date.now();
            const result = makeHelper().getDateClause();
            const after = Date.now();

            expect(result).toHaveProperty("date.gte");
            const gte = new Date((result as any).date.gte).getTime();
            expect(gte).toBeGreaterThanOrEqual(before);
            expect(gte).toBeLessThanOrEqual(after);
        });

        it("does not include lte when fromDate is absent", () => {
            const result = makeHelper().getDateClause() as any;
            expect(result.date.lte).toBeUndefined();
        });
    });

    describe("default — invalid fromDate provided", () => {
        it("returns a gte:now filter for a non-ISO string", () => {
            const before = Date.now();
            const result = makeHelper({
                fromDate: "not-a-date",
            }).getDateClause() as any;
            const after = Date.now();

            expect(result).toHaveProperty("date.gte");
            const gte = new Date(result.date.gte).getTime();
            expect(gte).toBeGreaterThanOrEqual(before);
            expect(gte).toBeLessThanOrEqual(after);
        });
    });

    describe("explicit fromDate provided", () => {
        it("returns a gte filter at the specified date midnight in the timezone", () => {
            const result = makeHelper({
                fromDate: "2026-06-15",
            }).getDateClause() as any;
            expect(result).toHaveProperty("date.gte");
            expect(result.date.gte).toContain("2026-06-15");
        });

        it("does not include lte when toDate is not provided", () => {
            const result = makeHelper({
                fromDate: "2026-06-15",
            }).getDateClause() as any;
            expect(result.date.lte).toBeUndefined();
        });

        it("includes lte when toDate is provided", () => {
            const result = makeHelper({
                fromDate: "2026-06-15",
                toDate: "2026-06-30",
            }).getDateClause() as any;
            expect(result.date.lte).toBeDefined();
        });

        it("returns gte:now default when fromDate is today (uses current time not midnight)", () => {
            // When fromDate equals today, getDateClause uses currentDateUTC not midnight
            const todayNYC = new Intl.DateTimeFormat("en-CA", {
                timeZone: "America/New_York",
            }).format(new Date());
            const before = Date.now();
            const result = makeHelper({
                fromDate: todayNYC,
            }).getDateClause() as any;
            const after = Date.now();

            const gte = new Date(result.date.gte).getTime();
            expect(gte).toBeGreaterThanOrEqual(before);
            expect(gte).toBeLessThanOrEqual(after);
        });
    });
});
