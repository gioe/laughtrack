import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { ShowDTO } from "@/objects/class/show/show.interface";

const { mockQueryRaw } = vi.hoisted(() => ({
    mockQueryRaw: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: mockQueryRaw },
}));

vi.mock("./findShowsForHome", () => ({
    findShowsForHome: vi.fn(),
}));
vi.mock("@/util/location/resolveNearbyZips", () => ({
    resolveNearbyZips: vi.fn(() => ["10801", "10803"]),
}));

import { findShowsForHome } from "./findShowsForHome";
import { resolveNearbyZips } from "@/util/location/resolveNearbyZips";
import { getFavoriteComedianShows } from "./getFavoriteComedianShows";

const mockFindShowsForHome = vi.mocked(findShowsForHome);
const mockResolveNearbyZips = vi.mocked(resolveNearbyZips);

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-06-01T12:00:00.000Z"));
    vi.clearAllMocks();
    mockQueryRaw.mockResolvedValue([{ member_uuid: "root-uuid" }]);
});

afterEach(() => {
    vi.useRealTimers();
});

function show(id: number, hour: number, headlinerId: number): ShowDTO {
    return {
        id,
        clubId: 1,
        date: new Date(`2026-06-02T${String(hour).padStart(2, "0")}:00:00Z`),
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

describe("getFavoriteComedianShows", () => {
    it("returns an empty rail without querying when no profile id is provided", async () => {
        await expect(getFavoriteComedianShows(null)).resolves.toEqual([]);

        expect(mockQueryRaw).not.toHaveBeenCalled();
        expect(mockFindShowsForHome).not.toHaveBeenCalled();
    });

    it("resolves all favorite families in one recursive query and matches exact descendant UUIDs", async () => {
        const shows = [{ id: 7, name: "Favorite Comic Night" }];
        mockQueryRaw.mockResolvedValue([
            { member_uuid: "root-uuid" },
            { member_uuid: "child-uuid" },
            { member_uuid: "grandchild-uuid" },
            { member_uuid: "hidden-alias-uuid" },
        ]);
        mockFindShowsForHome.mockResolvedValue(shows as never);

        await expect(getFavoriteComedianShows("profile-1")).resolves.toEqual(
            shows,
        );

        expect(mockQueryRaw).toHaveBeenCalledOnce();
        const query = mockQueryRaw.mock.calls[0][0] as {
            strings: string[];
            values: unknown[];
        };
        const sql = query.strings.join("?");
        expect(sql).toContain("WITH RECURSIVE favorite_ancestors");
        expect(sql).toContain("parent.id = ancestors.parent_comedian_id");
        expect(sql).toContain("child.parent_comedian_id = members.member_id");
        expect(sql).toContain("root.visible = true");
        expect(sql).toContain("SELECT DISTINCT member_uuid");
        expect(sql).not.toContain("child.visible");
        expect(query.values).toContain("profile-1");
        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            {
                date: { gte: new Date("2026-06-01T12:00:00.000Z") },
                club: { visible: true },
                lineupItems: {
                    some: {
                        comedianId: {
                            in: [
                                "root-uuid",
                                "child-uuid",
                                "grandchild-uuid",
                                "hidden-alias-uuid",
                            ],
                        },
                    },
                },
            },
            [{ date: "asc" }, { id: "asc" }],
            50,
            {
                profileId: "profile-1",
                sortByHomeRelevance: false,
                requireLineup: true,
            },
        );
    });

    it("filters followed-comedian shows to the supplied ZIP radius", async () => {
        mockFindShowsForHome.mockResolvedValue([]);

        await getFavoriteComedianShows("profile-1", "10801", 50);

        expect(mockResolveNearbyZips).toHaveBeenCalledWith("10801", 50);
        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            {
                date: { gte: new Date("2026-06-01T12:00:00.000Z") },
                club: {
                    visible: true,
                    zipCode: { in: ["10801", "10803"] },
                },
                lineupItems: {
                    some: {
                        comedianId: { in: ["root-uuid"] },
                    },
                },
            },
            [{ date: "asc" }, { id: "asc" }],
            50,
            {
                profileId: "profile-1",
                zipCode: "10801",
                sortByHomeRelevance: false,
                requireLineup: true,
            },
        );
    });

    it("keeps one show when multiple canonical family members share its lineup", async () => {
        mockQueryRaw.mockResolvedValue([
            { member_uuid: "root-uuid" },
            { member_uuid: "child-uuid" },
        ]);
        const sharedShow = show(10, 10, 1);
        mockFindShowsForHome.mockResolvedValue([sharedShow]);

        const result = await getFavoriteComedianShows("profile-1");

        expect(result.map(({ id }) => id)).toEqual([10]);
        expect(mockFindShowsForHome).toHaveBeenCalledOnce();
        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            expect.objectContaining({
                lineupItems: {
                    some: {
                        comedianId: {
                            in: ["root-uuid", "child-uuid"],
                        },
                    },
                },
            }),
            expect.anything(),
            expect.anything(),
            expect.anything(),
        );
    });

    it("preserves candidate-window diversity selection for canonical matches", async () => {
        mockFindShowsForHome.mockResolvedValue([
            ...Array.from({ length: 8 }, (_, index) =>
                show(index + 1, index + 1, 1),
            ),
            show(9, 9, 2),
        ]);

        const result = await getFavoriteComedianShows("profile-1");

        expect(result.map(({ id }) => id)).toEqual([1, 2, 3, 4, 5, 6, 7, 9]);
        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            expect.anything(),
            [{ date: "asc" }, { id: "asc" }],
            50,
            expect.objectContaining({
                profileId: "profile-1",
                sortByHomeRelevance: false,
                requireLineup: true,
            }),
        );
    });

    it("preserves global followed-comedian results without a usable ZIP", async () => {
        const shows = [{ id: 8, name: "Global Favorite Comic Night" }];
        mockFindShowsForHome.mockResolvedValue(shows as never);

        await expect(
            getFavoriteComedianShows("profile-1", "not-a-zip", 50),
        ).resolves.toEqual(shows);

        expect(mockResolveNearbyZips).not.toHaveBeenCalled();
        expect(mockFindShowsForHome).toHaveBeenCalledWith(
            expect.objectContaining({ club: { visible: true } }),
            [{ date: "asc" }, { id: "asc" }],
            50,
            {
                profileId: "profile-1",
                sortByHomeRelevance: false,
                requireLineup: true,
            },
        );
    });

    describe("tags emission (TASK-2567)", () => {
        // Comprehensive
        // tags-emission tests (PUBLIC filter, null filtering, empty case)
        // live on findShowsForHome.test.ts. This block guards against a
        // future regression that adds a mapper here which strips tags.

        it("passes tags through from findShowsForHome unchanged", async () => {
            const tagged = [
                { id: 1, tags: [{ slug: "open mic", name: "Open Mic" }] },
            ];
            mockFindShowsForHome.mockResolvedValue(tagged as never);

            const result = await getFavoriteComedianShows("profile-1");

            expect(result).toEqual(tagged);
            expect(result[0].tags).toEqual([
                { slug: "open mic", name: "Open Mic" },
            ]);
        });
    });
});
