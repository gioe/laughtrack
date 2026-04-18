import { describe, it, expect, afterEach, beforeEach, vi } from "vitest";
import {
    datesAreSame,
    datesAreToday,
    datesAreTomorrow,
    formatShowDate,
    isToday,
    isTomorrow,
} from "./dateUtil";

describe("formatShowDate", () => {
    it("renders a Pacific show at 9:30 pm PDT from its UTC instant", () => {
        // 2026-04-17 21:30 PDT == 2026-04-18 04:30 UTC
        expect(
            formatShowDate("2026-04-18T04:30:00Z", "America/Los_Angeles"),
        ).toBe("April 17th at 9:30 pm PDT");
    });

    it("renders an Eastern show at 6:30 pm EDT from its UTC instant", () => {
        // 2026-04-17 18:30 EDT == 2026-04-17 22:30 UTC
        expect(formatShowDate("2026-04-17T22:30:00Z", "America/New_York")).toBe(
            "April 17th at 6:30 pm EDT",
        );
    });

    it("renders a Central show at 7:00 pm CDT from its UTC instant", () => {
        // The Sports Drink "Thursday 7pm" fixture — stored as 2026-04-17 00:00 UTC
        // because Chicago is UTC-5 (CDT). This was the "12:00 am" bug on the homepage.
        expect(formatShowDate("2026-04-17T00:00:00Z", "America/Chicago")).toBe(
            "April 16th at 7:00 pm CDT",
        );
    });

    it("falls back to America/New_York when timezone is missing or null", () => {
        // 2026-04-17 00:00 UTC == 2026-04-16 20:00 EDT
        expect(formatShowDate("2026-04-17T00:00:00Z")).toBe(
            "April 16th at 8:00 pm EDT",
        );
        expect(formatShowDate("2026-04-17T00:00:00Z", null)).toBe(
            "April 16th at 8:00 pm EDT",
        );
        expect(formatShowDate("2026-04-17T00:00:00Z", undefined)).toBe(
            "April 16th at 8:00 pm EDT",
        );
    });

    it("renders standard-time (non-DST) shows with the correct zone label", () => {
        // January is EST (no DST). 2026-01-06 04:00 UTC == 2026-01-05 23:00 EST
        expect(formatShowDate("2026-01-06T04:00:00Z", "America/New_York")).toBe(
            "January 5th at 11:00 pm EST",
        );
    });

    it("pads minutes to two digits", () => {
        // 2026-04-17 20:05 EDT == 2026-04-18 00:05 UTC
        expect(formatShowDate("2026-04-18T00:05:00Z", "America/New_York")).toBe(
            "April 17th at 8:05 pm EDT",
        );
    });

    it("uses 12 (not 0) for midnight and noon", () => {
        // Midnight local ET
        expect(formatShowDate("2026-04-17T04:00:00Z", "America/New_York")).toBe(
            "April 17th at 12:00 am EDT",
        );
        // Noon local ET
        expect(formatShowDate("2026-04-17T16:00:00Z", "America/New_York")).toBe(
            "April 17th at 12:00 pm EDT",
        );
    });
});

describe("isToday / isTomorrow (timezone-aware)", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it("treats a late-night Chicago show as today (not tomorrow) when it's still that day locally", () => {
        // "Now" is 2026-04-17 22:00 CDT == 2026-04-18 03:00 UTC.
        // The show starts at 2026-04-17 23:30 CDT == 2026-04-18 04:30 UTC.
        // Naively comparing UTC calendar parts would say it's tomorrow (UTC day is 18),
        // but the venue calendar still reads April 17.
        vi.setSystemTime(new Date("2026-04-18T03:00:00Z"));
        const show = new Date("2026-04-18T04:30:00Z");

        expect(isToday(show, "America/Chicago")).toBe(true);
        expect(isTomorrow(show, "America/Chicago")).toBe(false);
    });

    it("treats the UTC-day-boundary rollover as tomorrow when the venue clock has passed midnight", () => {
        // "Now" is 2026-04-17 20:00 ET == 2026-04-18 00:00 UTC.
        // The show is 2026-04-18 21:00 ET (== 2026-04-19 01:00 UTC) — tomorrow locally.
        vi.setSystemTime(new Date("2026-04-18T00:00:00Z"));
        const show = new Date("2026-04-19T01:00:00Z");

        expect(isToday(show, "America/New_York")).toBe(false);
        expect(isTomorrow(show, "America/New_York")).toBe(true);
    });

    it("defaults to America/New_York when no timezone is provided", () => {
        // "Now" is 2026-04-17 22:00 ET == 2026-04-18 02:00 UTC.
        // A 23:00 ET show is today in ET even though its UTC day is April 18.
        vi.setSystemTime(new Date("2026-04-18T02:00:00Z"));
        const show = new Date("2026-04-18T03:00:00Z");

        expect(isToday(show)).toBe(true);
        expect(isToday(show, null)).toBe(true);
        expect(isToday(show, undefined)).toBe(true);
    });

    it("works in standard time (non-DST) for Pacific shows near midnight", () => {
        // January → PST (UTC-8). "Now" is 2026-01-10 23:30 PST == 2026-01-11 07:30 UTC.
        // A show at 2026-01-10 23:45 PST == 2026-01-11 07:45 UTC is still "today" in PST.
        vi.setSystemTime(new Date("2026-01-11T07:30:00Z"));
        const show = new Date("2026-01-11T07:45:00Z");

        expect(isToday(show, "America/Los_Angeles")).toBe(true);
    });

    it("handles the spring-forward DST transition (America/New_York, 2026-03-08)", () => {
        // DST starts 2026-03-08 in the US (clocks jump 02:00 → 03:00 ET).
        // "Now" is 2026-03-08 23:00 EDT == 2026-03-09 03:00 UTC.
        // A show at 2026-03-08 23:30 EDT == 2026-03-09 03:30 UTC — still March 8 locally.
        vi.setSystemTime(new Date("2026-03-09T03:00:00Z"));
        const show = new Date("2026-03-09T03:30:00Z");

        expect(isToday(show, "America/New_York")).toBe(true);
        expect(isTomorrow(show, "America/New_York")).toBe(false);
    });

    it("handles month rollover when computing tomorrow", () => {
        // "Now" is 2026-04-30 22:00 ET == 2026-05-01 02:00 UTC.
        // A show at 2026-05-01 20:00 ET == 2026-05-02 00:00 UTC is tomorrow locally.
        vi.setSystemTime(new Date("2026-05-01T02:00:00Z"));
        const show = new Date("2026-05-02T00:00:00Z");

        expect(isTomorrow(show, "America/New_York")).toBe(true);
    });
});

describe("datesAreSame / datesAreToday / datesAreTomorrow", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it("treats two Chicago shows on the same local calendar day as same — even across UTC boundary", () => {
        // Both shows are April 17 in Chicago (CDT = UTC-5).
        // show1: 21:00 CDT == 2026-04-18 02:00 UTC.
        // show2: 23:30 CDT == 2026-04-18 04:30 UTC.
        // UTC calendar parts match coincidentally here, but the point is
        // that datesAreSame must stay correct across the local midnight boundary.
        const show1 = new Date("2026-04-18T02:00:00Z");
        const show2 = new Date("2026-04-18T04:30:00Z");

        expect(datesAreSame(show1, show2, "America/Chicago")).toBe(true);
    });

    it("treats shows on different local days as different when UTC dates accidentally match", () => {
        // show1: 2026-04-17 23:00 ET == 2026-04-18 03:00 UTC (local day: April 17).
        // show2: 2026-04-18 20:00 ET == 2026-04-19 00:00 UTC (local day: April 18).
        const show1 = new Date("2026-04-18T03:00:00Z");
        const show2 = new Date("2026-04-19T00:00:00Z");

        expect(datesAreSame(show1, show2, "America/New_York")).toBe(false);
    });

    it("datesAreToday / datesAreTomorrow thread timezone through", () => {
        // "Now" is 2026-04-17 22:00 ET == 2026-04-18 02:00 UTC.
        vi.setSystemTime(new Date("2026-04-18T02:00:00Z"));

        const today1 = new Date("2026-04-18T03:30:00Z"); // 2026-04-17 23:30 ET
        const today2 = new Date("2026-04-18T02:45:00Z"); // 2026-04-17 22:45 ET
        expect(datesAreToday(today1, today2, "America/New_York")).toBe(true);

        const tomorrow1 = new Date("2026-04-19T01:00:00Z"); // 2026-04-18 21:00 ET
        const tomorrow2 = new Date("2026-04-19T03:00:00Z"); // 2026-04-18 23:00 ET
        expect(datesAreTomorrow(tomorrow1, tomorrow2, "America/New_York")).toBe(
            true,
        );
    });

    it("defaults to America/New_York when timezone is omitted", () => {
        const show1 = new Date("2026-04-18T03:00:00Z"); // 2026-04-17 23:00 ET
        const show2 = new Date("2026-04-18T02:30:00Z"); // 2026-04-17 22:30 ET
        expect(datesAreSame(show1, show2)).toBe(true);
        expect(datesAreSame(show1, show2, null)).toBe(true);
    });
});

describe("formatShowDate — additional suffix cases", () => {
    it("applies the correct ordinal suffix (st/nd/rd/th and teens)", () => {
        // Day 1 → 1st
        expect(formatShowDate("2026-05-01T13:00:00Z", "America/New_York")).toBe(
            "May 1st at 9:00 am EDT",
        );
        // Day 2 → 2nd
        expect(formatShowDate("2026-05-02T13:00:00Z", "America/New_York")).toBe(
            "May 2nd at 9:00 am EDT",
        );
        // Day 3 → 3rd
        expect(formatShowDate("2026-05-03T13:00:00Z", "America/New_York")).toBe(
            "May 3rd at 9:00 am EDT",
        );
        // Day 11/12/13 → th (teens override)
        expect(formatShowDate("2026-05-11T13:00:00Z", "America/New_York")).toBe(
            "May 11th at 9:00 am EDT",
        );
        expect(formatShowDate("2026-05-12T13:00:00Z", "America/New_York")).toBe(
            "May 12th at 9:00 am EDT",
        );
        expect(formatShowDate("2026-05-13T13:00:00Z", "America/New_York")).toBe(
            "May 13th at 9:00 am EDT",
        );
        // Day 21 → 21st
        expect(formatShowDate("2026-05-21T13:00:00Z", "America/New_York")).toBe(
            "May 21st at 9:00 am EDT",
        );
    });
});
