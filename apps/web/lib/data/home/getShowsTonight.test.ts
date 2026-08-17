import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { ShowDTO } from "@/objects/class/show/show.interface";

vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(() => Promise.resolve([])),
}));
vi.mock("zipcodes", () => ({
    default: {
        radius: vi.fn(() => ["10801", "10802"]),
    },
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

function show(id: number, date: string, headlinerId: number): ShowDTO {
    return {
        id,
        clubId: 1,
        date: new Date(date),
        name: `Show ${id}`,
        imageUrl: "",
        lineup: [
            {
                id: headlinerId,
                uuid: `comedian-${headlinerId}`,
                name: `Comedian ${headlinerId}`,
                imageUrl: "",
            },
        ],
    };
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

    it("scopes tonight's shows to nearby club ZIP codes when a ZIP is provided", async () => {
        await getShowsTonight("UTC", "10801", 25);

        const [where] = mockFindShowsForHome.mock.calls[0];
        expect(where.club).toEqual({
            visible: true,
            zipCode: { in: ["10801", "10802"] },
        });
    });

    it("queries a chronological candidate pool without a popularity rerank", async () => {
        await getShowsTonight("UTC", "10801", 25);

        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            expect.any(Object),
            [{ date: "asc" }, { id: "asc" }],
            50,
            {
                zipCode: "10801",
                sortByHomeRelevance: false,
                requireLineup: true,
            },
        );
    });

    it("returns no more than one show at an exact start timestamp", async () => {
        mockFindShowsForHome.mockResolvedValue([
            show(1, "2026-04-27T20:00:00Z", 1),
            show(2, "2026-04-27T20:00:00Z", 2),
            show(3, "2026-04-27T20:30:00Z", 3),
        ]);

        const result = await getShowsTonight("UTC");

        expect(result.map(({ id }) => id)).toEqual([1, 3]);
    });

    describe("tags emission (TASK-2567)", () => {
        // Comprehensive
        // tags-emission tests (PUBLIC filter, null filtering, empty case)
        // live on findShowsForHome.test.ts. This block guards against a
        // future regression that adds a mapper here which strips tags.

        it("passes tags through from findShowsForHome unchanged", async () => {
            const tagged = [
                {
                    ...show(1, "2026-04-27T20:00:00Z", 1),
                    tags: [{ slug: "open mic", name: "Open Mic" }],
                },
            ];
            mockFindShowsForHome.mockResolvedValue(tagged);

            const result = await getShowsTonight("UTC");

            expect(result).toEqual(tagged);
            expect(result[0].tags).toEqual([
                { slug: "open mic", name: "Open Mic" },
            ]);
        });
    });
});
