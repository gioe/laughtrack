import { describe, it, expect } from "vitest";
import { filterAndMapLineupItems } from "./comedianUtil";

const makeItem = (overrides: Record<string, unknown> = {}) => ({
    comedian: {
        id: 1,
        uuid: "uuid-1",
        name: "Test Comedian",
        parentComedian: null,
        taggedComedians: [],
        favoriteComedians: [],
        ...overrides,
    },
});

describe("filterAndMapLineupItems", () => {
    describe("isFavorite", () => {
        it("is false when userId is absent", () => {
            const item = makeItem({ favoriteComedians: [{ id: 99 }] });
            const [result] = filterAndMapLineupItems([item]);
            expect(result.isFavorite).toBe(false);
        });

        it("is true when userId is set and favoriteComedians is non-empty", () => {
            const item = makeItem({ favoriteComedians: [{ id: 99 }] });
            const [result] = filterAndMapLineupItems([item], "user-1");
            expect(result.isFavorite).toBe(true);
        });

        it("is false when userId is set and favoriteComedians is empty", () => {
            const item = makeItem({ favoriteComedians: [] });
            const [result] = filterAndMapLineupItems([item], "user-1");
            expect(result.isFavorite).toBe(false);
        });

        it("does not throw when userId is set but favoriteComedians is absent (null profileId)", () => {
            const item = makeItem();
            delete (item.comedian as Record<string, unknown>).favoriteComedians;
            let result: ReturnType<typeof filterAndMapLineupItems>[0];
            expect(() => {
                [result] = filterAndMapLineupItems([item], "user-1");
            }).not.toThrow();
            expect(result!.isFavorite).toBe(false);
        });
    });
});
