import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/data/home/findShowsForHome", () => ({
    findShowsForHome: vi.fn(),
}));

import { findRelatedShowsForShow } from "./findRelatedShowsForShow";
import { findShowsForHome } from "@/lib/data/home/findShowsForHome";

const mockFindShowsForHome = vi.mocked(findShowsForHome);

beforeEach(() => {
    vi.clearAllMocks();
    mockFindShowsForHome.mockResolvedValue([]);
});

describe("findRelatedShowsForShow", () => {
    describe("query args passed to findShowsForHome", () => {
        it("builds the expected where clause, orderBy, and limit", async () => {
            const before = new Date();
            await findRelatedShowsForShow(42, 99);
            const after = new Date();

            expect(mockFindShowsForHome).toHaveBeenCalledTimes(1);
            const [where, orderBy, take] = mockFindShowsForHome.mock.calls[0];

            // self-exclusion
            expect(where.id).toEqual({ not: 42 });

            // past-show exclusion (date >= now)
            const gte = (where.date as { gte: Date }).gte;
            expect(gte).toBeInstanceOf(Date);
            expect(gte.getTime()).toBeGreaterThanOrEqual(before.getTime());
            expect(gte.getTime()).toBeLessThanOrEqual(after.getTime());

            // club scope: same club, visible only
            expect(where.club).toEqual({ id: 99, visible: true });

            // ordering: date asc, then id asc as tiebreaker
            expect(orderBy).toEqual([{ date: "asc" }, { id: "asc" }]);

            // limit
            expect(take).toBe(4);
        });
    });

    describe("return value", () => {
        it("returns whatever findShowsForHome returns", async () => {
            const fakeShows = [
                { id: 2 } as any,
                { id: 3 } as any,
                { id: 4 } as any,
                { id: 5 } as any,
            ];
            mockFindShowsForHome.mockResolvedValueOnce(fakeShows);

            const result = await findRelatedShowsForShow(1, 99);

            expect(result).toBe(fakeShows);
        });

        it("returns an empty array when findShowsForHome returns no rows", async () => {
            mockFindShowsForHome.mockResolvedValueOnce([]);

            const result = await findRelatedShowsForShow(1, 99);

            expect(result).toEqual([]);
        });
    });
});
