import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(() => Promise.resolve([])),
}));

import { getShowsTonight } from "./getShowsTonight";
import { findShowsForHome } from "./findShowsForHome";

const mockFindShowsForHome = vi.mocked(findShowsForHome);

beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    // 2026-04-27 03:00 UTC = 2026-04-26 20:00 PDT — sits across the LA/UTC
    // day boundary, which is the exact case this wiring exists to fix.
    vi.setSystemTime(new Date("2026-04-27T03:00:00Z"));
});

afterEach(() => {
    vi.useRealTimers();
});

function getDateClause() {
    const [where] = mockFindShowsForHome.mock.calls[0];
    return where.date as { gte: Date; lte: Date };
}

describe("getShowsTonight", () => {
    it("anchors the day window on the caller's wallclock date in TZ", async () => {
        await getShowsTonight("America/Los_Angeles");

        const date = getDateClause();
        // Today in LA at 2026-04-26 20:00 PDT is 2026-04-26.
        expect(date.gte.toISOString()).toBe("2026-04-26T07:00:00.000Z");
        expect(date.lte.toISOString()).toBe("2026-04-27T06:59:59.999Z");
    });

    it("uses UTC day boundaries when TZ is UTC", async () => {
        await getShowsTonight("UTC");

        const date = getDateClause();
        expect(date.gte.toISOString()).toBe("2026-04-27T00:00:00.000Z");
        expect(date.lte.toISOString()).toBe("2026-04-27T23:59:59.999Z");
    });

    it("defaults to UTC when no timezone is provided", async () => {
        await getShowsTonight();

        const date = getDateClause();
        expect(date.gte.toISOString()).toBe("2026-04-27T00:00:00.000Z");
        expect(date.lte.toISOString()).toBe("2026-04-27T23:59:59.999Z");
    });
});
