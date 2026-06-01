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

    it("filters to clubs near the supplied ZIP when location is known", async () => {
        await getTrendingShowsThisWeek("America/New_York", "10001", 25);

        const [where, orderBy, take, options] =
            mockFindShowsForHome.mock.calls[0];
        expect(where.club).toMatchObject({
            visible: true,
            zipCode: {
                in: expect.arrayContaining(["10001"]),
            },
        });
        expect(orderBy).toEqual({ popularity: "desc" });
        expect(take).toBeUndefined();
        expect(options).toEqual({ zipCode: "10001" });
    });

    describe("tags emission (TASK-2567)", () => {
        // Wrapper is pure delegation to findShowsForHome; comprehensive
        // tags-emission tests (PUBLIC filter, null filtering, empty case)
        // live on findShowsForHome.test.ts. This block guards against a
        // future regression that adds a mapper here which strips tags.

        it("passes tags through from findShowsForHome unchanged", async () => {
            const tagged = [
                { id: 1, tags: [{ slug: "open mic", name: "Open Mic" }] },
            ];
            mockFindShowsForHome.mockResolvedValue(tagged as never);

            const result = await getTrendingShowsThisWeek("UTC");

            expect(result).toBe(tagged);
            expect(result[0].tags).toEqual([
                { slug: "open mic", name: "Open Mic" },
            ]);
        });
    });
});
