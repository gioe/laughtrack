import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { ShowDTO } from "@/objects/class/show/show.interface";

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

function show(id: number, headlinerID?: number): ShowDTO {
    return {
        id,
        clubId: 1,
        date: new Date("2026-04-28T00:00:00Z"),
        name: `Show ${id}`,
        imageUrl: "",
        lineup:
            headlinerID === undefined
                ? []
                : [
                      {
                          id: headlinerID,
                          uuid: `comic-${headlinerID}`,
                          name: `Comic ${headlinerID}`,
                          imageUrl: "",
                      },
                  ],
    };
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
        expect(take).toBe(50);
        expect(options).toEqual({ zipCode: "10001" });
    });

    it("prioritizes distinct inferred headliners before repeated performances", async () => {
        mockFindShowsForHome.mockResolvedValue([
            show(1, 1),
            show(2, 1),
            show(3, 1),
            show(4, 1),
            show(5, 1),
            show(6, 2),
            show(7, 3),
            show(8, 4),
            show(9, 5),
            show(10, 6),
            show(11, 7),
            show(12, 8),
        ]);

        const result = await getTrendingShowsThisWeek("UTC");

        expect(result.map(({ id }) => id)).toEqual([1, 6, 7, 8, 9, 10, 11, 12]);
        expect(mockFindShowsForHome.mock.calls[0][2]).toBe(50);
    });

    it("backfills repeated headliners when unique inventory is insufficient", async () => {
        mockFindShowsForHome.mockResolvedValue([
            show(1, 1),
            show(2, 1),
            show(3, 2),
            show(4, 2),
            show(5, 3),
            show(6, 3),
            show(7, 1),
            show(8, 2),
            show(9, 3),
            show(10, 4),
        ]);

        const result = await getTrendingShowsThisWeek("UTC");

        expect(result.map(({ id }) => id)).toEqual([1, 3, 5, 10, 2, 4, 6, 7]);
    });

    it("keeps shows without inferred headliners independently eligible", async () => {
        mockFindShowsForHome.mockResolvedValue([
            show(1),
            show(2),
            show(3),
            show(4, 1),
            show(5, 1),
            show(6, 2),
            show(7, 2),
            show(8, 3),
            show(9, 3),
        ]);

        const result = await getTrendingShowsThisWeek("UTC");

        expect(result.map(({ id }) => id)).toEqual([1, 2, 3, 4, 6, 8, 5, 7]);
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

            expect(result).toEqual(tagged);
            expect(result[0].tags).toEqual([
                { slug: "open mic", name: "Open Mic" },
            ]);
        });
    });
});
