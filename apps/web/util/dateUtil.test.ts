import { describe, it, expect, vi } from "vitest";
import { formatShowCountdown, formatShowDate, isShowPast } from "./dateUtil";

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
        const halfHourAgo = new Date(
            now.getTime() - 30 * 60 * 1000,
        ).toISOString();
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
        // 90 minutes floors to 1 hour — the bucket flips only when the next unit
        // boundary is fully crossed (no jump from '89 minutes' to '2 hours').
        const inNinetyMinutes = new Date(
            now.getTime() + 90 * 60 * 1000,
        ).toISOString();
        expect(formatShowCountdown(inNinetyMinutes, now).label).toBe(
            "Show in 1 hour",
        );

        const inFifteenMinutes = new Date(
            now.getTime() + 15 * 60 * 1000,
        ).toISOString();
        expect(formatShowCountdown(inFifteenMinutes, now).label).toBe(
            "Show in 15 minutes",
        );
    });

    it("promotes to years for far-future shows, matching past-show symmetry", () => {
        const inFourteenMonths = new Date(
            now.getTime() + 14 * 30 * 24 * 60 * 60 * 1000,
        ).toISOString();
        expect(formatShowCountdown(inFourteenMonths, now).label).toBe(
            "Show in 1 year",
        );
    });
});

describe("isShowPast", () => {
    const now = new Date("2026-05-14T18:00:00Z");

    it("keeps a show that started within the live window out of the past state", () => {
        const halfHourAgo = new Date(
            now.getTime() - 30 * 60 * 1000,
        ).toISOString();

        expect(isShowPast(halfHourAgo, now)).toBe(false);
    });

    it("marks a show past only after the live window has elapsed", () => {
        const threeHoursAgo = new Date(
            now.getTime() - 3 * 60 * 60 * 1000,
        ).toISOString();

        expect(isShowPast(threeHoursAgo, now)).toBe(true);
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

describe("Canadian permanent-time runtime regressions", () => {
    it.each([
        ["2026-01-15T20:00:00Z", "America/Edmonton", "1:00 pm"],
        ["2026-01-15T20:00:00Z", "America/Vancouver", "12:00 pm"],
        ["2026-10-31T20:00:00Z", "America/Edmonton", "2:00 pm"],
        ["2026-10-31T20:00:00Z", "America/Vancouver", "1:00 pm"],
        ["2026-11-01T08:00:00Z", "America/Edmonton", "2:00 am"],
        ["2026-11-01T09:00:00Z", "America/Vancouver", "2:00 am"],
        ["2026-12-01T20:00:00Z", "America/Edmonton", "2:00 pm"],
        ["2026-12-01T20:00:00Z", "America/Vancouver", "1:00 pm"],
        ["2027-03-14T02:00:00Z", "America/Edmonton", "8:00 pm"],
        ["2027-03-13T02:00:00Z", "America/Edmonton", "8:00 pm"],
    ])(
        "renders stored UTC %s in %s using current runtime rules",
        (instant, zone, wallTime) => {
            expect(formatShowDate(instant, zone)).toContain(`at ${wallTime}`);
        },
    );
});

describe("permanent Canadian time presentation", () => {
    it.each([
        [
            "2026-06-18T05:59:59Z",
            "America/Edmonton",
            "June 17th at 11:59 pm MDT",
        ],
        [
            "2026-06-18T06:00:00Z",
            "America/Edmonton",
            "June 18th at 12:00 am ABT",
        ],
        [
            "2026-06-18T06:00:01Z",
            "America/Edmonton",
            "June 18th at 12:00 am ABT",
        ],
        [
            "2026-03-09T06:59:59Z",
            "America/Vancouver",
            "March 8th at 11:59 pm PDT",
        ],
        [
            "2026-03-09T07:00:00Z",
            "America/Vancouver",
            "March 9th at 12:00 am PT",
        ],
        [
            "2026-03-09T07:00:01Z",
            "America/Vancouver",
            "March 9th at 12:00 am PT",
        ],
        [
            "2026-11-01T07:59:59Z",
            "America/Edmonton",
            "November 1st at 1:59 am ABT",
        ],
        [
            "2026-11-01T08:00:00Z",
            "America/Edmonton",
            "November 1st at 2:00 am ABT",
        ],
        [
            "2026-11-01T08:59:59Z",
            "America/Vancouver",
            "November 1st at 1:59 am PT",
        ],
        [
            "2026-11-01T09:00:00Z",
            "America/Vancouver",
            "November 1st at 2:00 am PT",
        ],
        [
            "2026-12-01T20:00:00Z",
            "America/Edmonton",
            "December 1st at 2:00 pm ABT",
        ],
        [
            "2026-12-01T20:00:00Z",
            "America/Vancouver",
            "December 1st at 1:00 pm PT",
        ],
        [
            "2027-03-14T01:00:00Z",
            "America/Edmonton",
            "March 13th at 7:00 pm ABT",
        ],
        [
            "2027-03-13T01:00:00Z",
            "America/Edmonton",
            "March 12th at 7:00 pm ABT",
        ],
        [
            "2027-07-15T20:00:00Z",
            "America/Edmonton",
            "July 15th at 2:00 pm ABT",
        ],
        [
            "2027-07-15T20:00:00Z",
            "America/Vancouver",
            "July 15th at 1:00 pm PT",
        ],
        [
            "2027-01-01T05:30:00Z",
            "America/Edmonton",
            "December 31st at 11:30 pm ABT",
        ],
        [
            "2027-01-01T06:30:00Z",
            "America/Vancouver",
            "December 31st at 11:30 pm PT",
        ],
        [
            "2026-01-15T20:00:00Z",
            "America/Edmonton",
            "January 15th at 1:00 pm MST",
        ],
        [
            "2026-01-15T20:00:00Z",
            "America/Vancouver",
            "January 15th at 12:00 pm PST",
        ],
        [
            "2025-07-15T20:00:00Z",
            "America/Edmonton",
            "July 15th at 2:00 pm MDT",
        ],
        [
            "2025-07-15T20:00:00Z",
            "America/Vancouver",
            "July 15th at 1:00 pm PDT",
        ],
        [
            "2026-12-01T20:00:00Z",
            "America/Denver",
            "December 1st at 1:00 pm MST",
        ],
        [
            "2026-12-01T20:00:00Z",
            "America/Los_Angeles",
            "December 1st at 12:00 pm PST",
        ],
        [
            "2026-12-01T20:00:00Z",
            "America/Toronto",
            "December 1st at 3:00 pm EST",
        ],
        [
            "2026-12-01T20:00:00Z",
            "America/Phoenix",
            "December 1st at 1:00 pm MST",
        ],
        [
            "2026-12-01T20:00:00Z",
            "Canada/Mountain",
            "December 1st at 2:00 pm ABT",
        ],
        [
            "2026-12-01T20:00:00Z",
            "Canada/Pacific",
            "December 1st at 1:00 pm PT",
        ],
        [
            "2026-01-15T20:00:00Z",
            "Canada/Mountain",
            "January 15th at 1:00 pm MST",
        ],
        [
            "2026-01-15T20:00:00Z",
            "Canada/Pacific",
            "January 15th at 12:00 pm PST",
        ],
    ])("formats %s in %s as %s", (instant, zone, expected) => {
        expect(formatShowDate(instant, zone)).toBe(expected);
    });

    it("does not change the stored UTC instant, timezone ID, or countdown", () => {
        const show = Object.freeze({
            date: "2027-03-14T01:00:00Z",
            timezone: "America/Edmonton",
        });
        const now = new Date("2027-03-14T00:00:00Z");
        const before = formatShowCountdown(show.date, now);
        expect(formatShowDate(show.date, show.timezone)).toBe(
            "March 13th at 7:00 pm ABT",
        );
        expect(show).toEqual({
            date: "2027-03-14T01:00:00Z",
            timezone: "America/Edmonton",
        });
        expect(formatShowCountdown(show.date, now)).toEqual(before);
        expect(before).toEqual({ label: "Show in 1 hour", tone: "future" });
    });

    it("renders correct client labels even when Intl still applies the old seasonal rules", async () => {
        const NativeFormatter = Intl.DateTimeFormat;
        const legacyZones: Record<string, string> = {
            "America/Edmonton": "America/Denver",
            "Canada/Mountain": "America/Denver",
            "America/Vancouver": "America/Los_Angeles",
            "Canada/Pacific": "America/Los_Angeles",
        };
        const staleFormatter = new Proxy(NativeFormatter, {
            construct(target, args) {
                const [locales, options] = args;
                return new target(locales, {
                    ...options,
                    timeZone:
                        legacyZones[options?.timeZone] ?? options?.timeZone,
                });
            },
        });
        vi.spyOn(Intl, "DateTimeFormat").mockImplementation(staleFormatter);
        // date-fns-tz caches Intl formatters by zone. Load a fresh module graph
        // after installing the stale client, rather than accidentally reusing
        // a server formatter and letting the regression pass for the wrong reason.
        vi.resetModules();
        try {
            const client = await import("./dateUtil");
            for (const [zone, staleHour, expected] of [
                ["America/Edmonton", "13:00", "December 1st at 2:00 pm ABT"],
                ["America/Vancouver", "12:00", "December 1st at 1:00 pm PT"],
                ["Canada/Mountain", "13:00", "December 1st at 2:00 pm ABT"],
                ["Canada/Pacific", "12:00", "December 1st at 1:00 pm PT"],
            ]) {
                const instant = "2026-12-01T20:00:00Z";
                expect(
                    new Intl.DateTimeFormat("en-GB", {
                        timeZone: zone,
                        hour: "2-digit",
                        minute: "2-digit",
                        hourCycle: "h23",
                    }).format(new Date(instant)),
                ).toBe(staleHour);
                expect(client.formatShowDate(instant, zone)).toBe(expected);
            }
            expect(
                client.formatShowDate(
                    "2026-01-15T20:00:00Z",
                    "America/Edmonton",
                ),
            ).toBe("January 15th at 1:00 pm MST");
            expect(
                client.formatShowDate(
                    "2026-12-01T20:00:00Z",
                    "America/New_York",
                ),
            ).toBe("December 1st at 3:00 pm EST");
        } finally {
            vi.restoreAllMocks();
            vi.resetModules();
        }
    });
});
