import { describe, it, expect } from "vitest";
import { formatShowCountdown, formatShowDate } from "./dateUtil";

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

describe("formatShowCountdown", () => {
    const now = new Date("2026-05-14T18:00:00Z");

    it("renders future shows with 'Show in N' phrasing and a future tone", () => {
        const inThreeDays = new Date(
            now.getTime() + 3 * 24 * 60 * 60 * 1000,
        ).toISOString();
        expect(formatShowCountdown(inThreeDays, now)).toEqual({
            label: "Show in 3 days",
            tone: "future",
        });
    });

    it("treats a show that started within the live window as happening now", () => {
        const halfHourAgo = new Date(now.getTime() - 30 * 60 * 1000).toISOString();
        expect(formatShowCountdown(halfHourAgo, now)).toEqual({
            label: "Happening now",
            tone: "live",
        });
    });

    it("renders past shows with 'Ended N ago' phrasing and a past tone", () => {
        const twoDaysAgo = new Date(
            now.getTime() - 2 * 24 * 60 * 60 * 1000,
        ).toISOString();
        expect(formatShowCountdown(twoDaysAgo, now)).toEqual({
            label: "Ended 2 days ago",
            tone: "past",
        });
    });

    it("scales the unit down to hours and minutes for imminent shows", () => {
        const inNinetyMinutes = new Date(
            now.getTime() + 90 * 60 * 1000,
        ).toISOString();
        expect(formatShowCountdown(inNinetyMinutes, now).label).toBe(
            "Show in 2 hours",
        );

        const inFifteenMinutes = new Date(
            now.getTime() + 15 * 60 * 1000,
        ).toISOString();
        expect(formatShowCountdown(inFifteenMinutes, now).label).toBe(
            "Show in 15 minutes",
        );
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
