import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(() => Promise.resolve([])),
}));

import { getTrendingShowsThisWeek } from "./getTrendingShowsThisWeek";
import { findShowsForHome } from "./findShowsForHome";

const mockFindShowsForHome = vi.mocked(findShowsForHome);

beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    // 2026-04-27 03:00 UTC = 2026-04-26 20:00 PDT.
    vi.setSystemTime(new Date("2026-04-27T03:00:00Z"));
});

afterEach(() => {
    vi.useRealTimers();
});

function getDateClause() {
    const [where] = mockFindShowsForHome.mock.calls[0];
    return where.date as { gte: Date; lte: Date };
}

describe("getTrendingShowsThisWeek", () => {
    it("anchors the upper bound on end-of-day-7 in the caller's TZ", async () => {
        await getTrendingShowsThisWeek("America/Los_Angeles");

        const date = getDateClause();
        // Lower bound stays at "now"; upper bound is end of (today + 7 days)
        // wallclock in LA — today is 2026-04-26, +7 = 2026-05-03, end-of-day
        // PDT (UTC-7) = 2026-05-04 06:59:59.999 UTC.
        expect(date.gte.toISOString()).toBe("2026-04-27T03:00:00.000Z");
        expect(date.lte.toISOString()).toBe("2026-05-04T06:59:59.999Z");
    });

    it("uses UTC day boundaries when TZ is UTC", async () => {
        await getTrendingShowsThisWeek("UTC");

        const date = getDateClause();
        // today in UTC = 2026-04-27, +7 = 2026-05-04, end-of-day = 23:59:59.999Z
        expect(date.gte.toISOString()).toBe("2026-04-27T03:00:00.000Z");
        expect(date.lte.toISOString()).toBe("2026-05-04T23:59:59.999Z");
    });

    it("defaults to UTC when no timezone is provided", async () => {
        await getTrendingShowsThisWeek();

        const date = getDateClause();
        expect(date.gte.toISOString()).toBe("2026-04-27T03:00:00.000Z");
        expect(date.lte.toISOString()).toBe("2026-05-04T23:59:59.999Z");
    });
});
