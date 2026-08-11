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

        it("is true for a visible canonical parent that is favorited", () => {
            const item = makeItem({
                favoriteComedians: [],
                parentComedian: {
                    id: 99,
                    uuid: "uuid-99",
                    name: "Canonical Comedian",
                    visible: true,
                    taggedComedians: [],
                    favoriteComedians: [{ id: 99 }],
                },
            });
            const [result] = filterAndMapLineupItems([item], "user-1");

            expect(result.id).toBe(99);
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

    describe("showCount", () => {
        it("maps lineup item count from the effective comedian", () => {
            const item = makeItem({ _count: { lineupItems: 17 } });
            const [result] = filterAndMapLineupItems([item]);

            expect(result.showCount).toBe(17);
        });

        it("maps parent lineup item count for alias comedians", () => {
            const child = makeItem({
                id: 2,
                uuid: "uuid-2",
                name: "Child Comedian",
                _count: { lineupItems: 2 },
                parentComedian: {
                    id: 99,
                    uuid: "uuid-99",
                    name: "Parent Comic",
                    visible: true,
                    taggedComedians: [],
                    _count: { lineupItems: 41 },
                },
            });

            const [result] = filterAndMapLineupItems([child]);

            expect(result.name).toBe("Parent Comic");
            expect(result.showCount).toBe(41);
        });
    });

    describe("socialData popularity hydration", () => {
        it("attaches socialData with the effective comedian's popularity", () => {
            const item = makeItem({ popularity: 42.5 });
            const [result] = filterAndMapLineupItems([item]);

            expect(result.socialData).toEqual({ id: 1, popularity: 42.5 });
        });

        it("attaches socialData for an explicit popularity of 0", () => {
            // 0 must hydrate — the headliner comparator ranks an explicit 0
            // above missing socialData (-1), so dropping it would silently
            // demote zero-popularity comedians.
            const item = makeItem({ popularity: 0 });
            const [result] = filterAndMapLineupItems([item]);

            expect(result.socialData).toEqual({ id: 1, popularity: 0 });
        });

        it("omits socialData when the caller's select did not load popularity", () => {
            const item = makeItem({});
            const [result] = filterAndMapLineupItems([item]);

            expect(result.socialData).toBeUndefined();
            expect("socialData" in result).toBe(false);
        });

        it("uses the parent's popularity for alias comedians", () => {
            const child = makeItem({
                id: 2,
                uuid: "uuid-2",
                name: "Child Comedian",
                popularity: 3,
                parentComedian: {
                    id: 99,
                    uuid: "uuid-99",
                    name: "Parent Comic",
                    visible: true,
                    taggedComedians: [],
                    popularity: 77,
                },
            });

            const [result] = filterAndMapLineupItems([child]);

            expect(result.socialData).toEqual({ id: 99, popularity: 77 });
        });
    });

    describe("role", () => {
        it("maps explicit lineup item role without deriving it from comedian data", () => {
            const [result] = filterAndMapLineupItems([
                { ...makeItem(), role: "Headliner" },
            ]);

            expect(result.role).toBe("Headliner");
        });

        it("leaves role absent when the lineup item does not provide one", () => {
            const [result] = filterAndMapLineupItems([makeItem()]);

            expect(result.role).toBeUndefined();
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
        let result: boolean;
        expect(() => {
            result = containsAliasTag(taggedComedians);
        }).not.toThrow();
        expect(result!).toBe(false);
    });

    it("does not throw and returns false when a taggedComedian entry has an undefined tag", () => {
        const taggedComedians = [
            { tag: undefined },
            { tag: { slug: "headliner" } },
        ];
        let result: boolean;
        expect(() => {
            result = containsAliasTag(taggedComedians);
        }).not.toThrow();
        expect(result!).toBe(false);
    });
});

describe("getEffectiveComedian", () => {
    it("returns parentComedian when it is set and visible", () => {
        const comedian = {
            id: 2,
            name: "Alias",
            parentComedian: { id: 1, name: "Real", visible: true },
        };
        expect(getEffectiveComedian(comedian)).toEqual({
            id: 1,
            name: "Real",
            visible: true,
        });
    });

    it("returns the comedian itself when parentComedian is null", () => {
        const comedian = { id: 1, name: "Real", parentComedian: null };
        expect(getEffectiveComedian(comedian)).toEqual(comedian);
    });

    it("returns the comedian itself when parentComedian is undefined", () => {
        const comedian = { id: 1, name: "Real" };
        expect(getEffectiveComedian(comedian)).toEqual(comedian);
    });

    it("returns the alias itself when parentComedian.visible is false", () => {
        // Hidden parent must not leak through alias substitution — a visible
        // alias of a hidden parent should display as itself, not surface the
        // suppressed parent's name and social handles.
        const comedian = {
            id: 2,
            name: "Alias",
            parentComedian: { id: 1, name: "Hidden", visible: false },
        };
        expect(getEffectiveComedian(comedian)).toEqual(comedian);
    });
});
