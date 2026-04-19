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
    describe("self-exclusion", () => {
        it("passes id: { not: showId } in the where clause", async () => {
            await findRelatedShowsForShow(42, 99);

            const [where] = mockFindShowsForHome.mock.calls[0];
            expect(where.id).toEqual({ not: 42 });
        });
    });

    describe("past-show exclusion", () => {
        it("requires date >= now in the where clause", async () => {
            const before = new Date();
            await findRelatedShowsForShow(1, 99);
            const after = new Date();

            const [where] = mockFindShowsForHome.mock.calls[0];
            const gte = (where.date as { gte: Date }).gte;
            expect(gte).toBeInstanceOf(Date);
            expect(gte.getTime()).toBeGreaterThanOrEqual(before.getTime());
            expect(gte.getTime()).toBeLessThanOrEqual(after.getTime());
        });
    });

    describe("club scope", () => {
        it("scopes to the same clubId and only visible clubs", async () => {
            await findRelatedShowsForShow(1, 99);

            const [where] = mockFindShowsForHome.mock.calls[0];
            expect(where.club).toEqual({ id: 99, visible: true });
        });
    });

    describe("ordering", () => {
        it("orders by date ascending then id ascending", async () => {
            await findRelatedShowsForShow(1, 99);

            const [, orderBy] = mockFindShowsForHome.mock.calls[0];
            expect(orderBy).toEqual([{ date: "asc" }, { id: "asc" }]);
        });
    });

    describe("limit", () => {
        it("limits results to 4", async () => {
            await findRelatedShowsForShow(1, 99);

            const [, , take] = mockFindShowsForHome.mock.calls[0];
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
