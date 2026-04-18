import { describe, it, expect } from "vitest";
import { QueryHelper } from "./QueryHelper";

function makeHelper(params: Record<string, string | undefined> = {}) {
    return new QueryHelper({
        params,
        timezone: "America/New_York",
    });
}

describe("QueryHelper.getDateClause", () => {
    describe("no date params", () => {
        it("returns an empty object when both fromDate and toDate are absent", () => {
            const result = makeHelper().getDateClause();
            expect(result).toEqual({});
        });

        it("returns an empty object when fromDate and toDate are both undefined", () => {
            const result = makeHelper({
                fromDate: undefined,
                toDate: undefined,
            }).getDateClause();
            expect(result).toEqual({});
        });
    });

    describe("fromDate invalid, toDate absent — fall back to empty", () => {
        // An invalid fromDate with no toDate is equivalent to "no date params"
        // in intent. Previously this returned gte:now; now it returns {} so
        // callers can decide whether to apply their own upcoming-only filter.
        it("returns an empty object for a non-ISO fromDate when toDate is absent", () => {
            const result = makeHelper({
                fromDate: "not-a-date",
            }).getDateClause();
            expect(result).toEqual({});
        });
    });

    describe("fromDate invalid, toDate present — upcoming-only fallback", () => {
        it("returns a gte:now filter when fromDate is invalid but toDate is set", () => {
            const before = Date.now();
            const result = makeHelper({
                fromDate: "not-a-date",
                toDate: "2026-06-30",
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

        it("returns fromDate-only clause when toDate is an invalid ISO string", () => {
            const result = makeHelper({
                fromDate: "2026-06-15",
                toDate: "not-a-date",
            }).getDateClause() as any;
            expect(result).toHaveProperty("date.gte");
            expect(result.date.gte).toContain("2026-06-15");
            expect(result.date.lte).toBeUndefined();
        });

        it("returns fromDate-only clause when toDate fails date parsing", () => {
            const result = makeHelper({
                fromDate: "2026-06-15",
                toDate: "2026-99-99",
            }).getDateClause() as any;
            expect(result).toHaveProperty("date.gte");
            expect(result.date.lte).toBeUndefined();
        });

        it("converts fromDate midnight in America/New_York (EDT) to exact UTC", () => {
            const result = makeHelper({
                fromDate: "2026-06-15",
            }).getDateClause() as any;
            // Midnight EDT (UTC-4) → 04:00 UTC
            expect(result.date.gte).toBe("2026-06-15T04:00:00.000Z");
        });

        it("converts toDate end-of-day in America/New_York (EDT) to exact UTC", () => {
            const result = makeHelper({
                fromDate: "2026-06-15",
                toDate: "2026-06-30",
            }).getDateClause() as any;
            // 23:59:59.999 EDT (UTC-4) → 03:59:59.999 UTC next day
            expect(result.date.gte).toBe("2026-06-15T04:00:00.000Z");
            expect(result.date.lte).toBe("2026-07-01T03:59:59.999Z");
        });

        it("converts fromDate midnight in America/New_York (EST) to exact UTC", () => {
            // January is EST (UTC-5)
            const result = makeHelper({
                fromDate: "2026-01-10",
            }).getDateClause() as any;
            // Midnight EST (UTC-5) → 05:00 UTC
            expect(result.date.gte).toBe("2026-01-10T05:00:00.000Z");
        });

        it("converts toDate end-of-day in America/New_York (EST) to exact UTC", () => {
            const result = makeHelper({
                fromDate: "2026-01-10",
                toDate: "2026-01-15",
            }).getDateClause() as any;
            // 23:59:59.999 EST (UTC-5) → 04:59:59.999 UTC next day
            expect(result.date.gte).toBe("2026-01-10T05:00:00.000Z");
            expect(result.date.lte).toBe("2026-01-16T04:59:59.999Z");
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
