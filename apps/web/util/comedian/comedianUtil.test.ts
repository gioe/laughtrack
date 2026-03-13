import { describe, it, expect } from "vitest";
import {
    filterAndMapLineupItems,
    containsAliasTag,
    getEffectiveComedian,
} from "./comedianUtil";

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

const parentComedian = {
    id: 10,
    uuid: "uuid-10",
    name: "Parent Comedian",
    taggedComedians: [],
};
// parentInLineup=true: child's parentComedian.id matches the parent fixture (id 10)
// parentInLineup=false: child's parentComedian.id is 99, which is not in the lineup
const makeChild = (parentInLineup: boolean) =>
    makeItem({
        id: 2,
        uuid: "uuid-2",
        name: "Child Comedian",
        parentComedian: parentInLineup
            ? parentComedian
            : {
                  id: 99,
                  uuid: "uuid-99",
                  name: "Absent Parent",
                  taggedComedians: [],
              },
    });
const makeParent = () =>
    makeItem({ id: 10, uuid: "uuid-10", name: "Parent Comedian" });

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

    describe("parent-deduplication", () => {
        it("excludes a child comedian when its parent is present in the lineup", () => {
            const parent = makeParent();
            const child = makeChild(true);
            const results = filterAndMapLineupItems([parent, child]);
            expect(results).toHaveLength(1);
            expect(results[0].id).toBe(10);
        });

        it("retains a child comedian when its parent is absent from the lineup", () => {
            const child = makeChild(false); // parent id 99 not in lineup
            const results = filterAndMapLineupItems([child]);
            expect(results).toHaveLength(1);
        });

        it("filters correctly regardless of child-before-parent ordering", () => {
            const parent = makeParent();
            const child = makeChild(true);
            const results = filterAndMapLineupItems([child, parent]);
            expect(results).toHaveLength(1);
            expect(results[0].id).toBe(10);
        });
    });
});

describe("containsAliasTag", () => {
    it("returns true when the alias tag is present", () => {
        const taggedComedians = [
            { tag: { slug: "headliner" } },
            { tag: { slug: "alias" } },
        ];
        expect(containsAliasTag(taggedComedians)).toBe(true);
    });

    it("returns false when no alias tag is present", () => {
        const taggedComedians = [{ tag: { slug: "headliner" } }];
        expect(containsAliasTag(taggedComedians)).toBe(false);
    });

    it("returns false for an empty array", () => {
        expect(containsAliasTag([])).toBe(false);
    });

    it("does not throw and returns false when a taggedComedian entry has a null tag", () => {
        const taggedComedians = [{ tag: null }, { tag: { slug: "headliner" } }];
        expect(() => containsAliasTag(taggedComedians)).not.toThrow();
        expect(containsAliasTag(taggedComedians)).toBe(false);
    });

    it("does not throw and returns false when a taggedComedian entry has an undefined tag", () => {
        const taggedComedians = [
            { tag: undefined },
            { tag: { slug: "headliner" } },
        ];
        expect(() => containsAliasTag(taggedComedians)).not.toThrow();
        expect(containsAliasTag(taggedComedians)).toBe(false);
    });
});

describe("getEffectiveComedian", () => {
    it("returns parentComedian when it is set", () => {
        const comedian = {
            id: 2,
            name: "Alias",
            parentComedian: { id: 1, name: "Real" },
        };
        expect(getEffectiveComedian(comedian)).toEqual({ id: 1, name: "Real" });
    });

    it("returns the comedian itself when parentComedian is null", () => {
        const comedian = { id: 1, name: "Real", parentComedian: null };
        expect(getEffectiveComedian(comedian)).toEqual(comedian);
    });

    it("returns the comedian itself when parentComedian is undefined", () => {
        const comedian = { id: 1, name: "Real" };
        expect(getEffectiveComedian(comedian)).toEqual(comedian);
    });
});
