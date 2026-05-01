import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(() => Promise.resolve([])),
}));
vi.mock("zipcodes", () => ({
    default: {
        radius: vi.fn(() => ["10801", "10802"]),
    },
}));

import { getShowsNearZip } from "./getShowsNearZip";
import { findShowsForHome } from "./findShowsForHome";

const mockFindShowsForHome = vi.mocked(findShowsForHome);

beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-30T12:00:00Z"));
});

afterEach(() => {
    vi.useRealTimers();
});

describe("getShowsNearZip", () => {
    it("returns no shows for an invalid ZIP", async () => {
        const result = await getShowsNearZip("not-a-zip", 25);

        expect(result).toEqual([]);
        expect(mockFindShowsForHome).not.toHaveBeenCalled();
    });

    it("scopes upcoming shows to nearby ZIP codes", async () => {
        await getShowsNearZip("10801", 25);

        const [where] = mockFindShowsForHome.mock.calls[0];
        expect(where.club).toEqual({
            visible: true,
            zipCode: { in: ["10801", "10802"] },
        });
        expect(where.date).toEqual({ gte: new Date("2026-04-30T12:00:00Z") });
    });

    it("asks the shared home query to rank ZIP-scoped shows by home relevance", async () => {
        await getShowsNearZip("10801", 25);

        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            expect.any(Object),
            { date: "asc" },
            8,
            { zipCode: "10801", sortByHomeRelevance: true },
        );
    });
});
