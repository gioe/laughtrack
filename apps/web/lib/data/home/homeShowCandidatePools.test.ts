import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ShowDTO } from "@/objects/class/show/show.interface";

vi.mock("./findShowsForHome", () => ({ findShowsForHome: vi.fn() }));
vi.mock("@/lib/db", () => ({ db: { $queryRaw: vi.fn() } }));
vi.mock("zipcodes", () => ({ default: { radius: () => ["10801"] } }));

import { findShowsForHome } from "./findShowsForHome";
import { db } from "@/lib/db";
import { getShowsTonight } from "./getShowsTonight";
import { getTrendingShowsThisWeek } from "./getTrendingShowsThisWeek";
import { getFavoriteComedianShows } from "./getFavoriteComedianShows";
import { getShowsNearZip } from "./getShowsNearZip";

const candidates: ShowDTO[] = Array.from({ length: 50 }, (_, index) => ({
    id: index + 1,
    clubId: 1,
    name: `Show ${index + 1}`,
    date: new Date(Date.UTC(2026, 8, 15, 12, index)),
    imageUrl: "",
    lineup: [
        {
            id: index + 1,
            uuid: `comic-${index + 1}`,
            name: `Comic ${index + 1}`,
            imageUrl: "",
        },
    ],
}));

beforeEach(() => {
    vi.mocked(findShowsForHome).mockResolvedValue(candidates);
    vi.mocked(db.$queryRaw).mockResolvedValue([{ member_uuid: "favorite" }]);
});

describe("bounded home feed candidate pools", () => {
    it.each([
        [
            "Tonight",
            (limit?: number) => getShowsTonight("UTC", "10801", 25, limit),
        ],
        [
            "This week",
            (limit?: number) =>
                getTrendingShowsThisWeek("UTC", "10801", 25, limit),
        ],
        [
            "Followed comedians",
            (limit?: number) =>
                getFavoriteComedianShows("profile-1", "10801", 25, limit),
        ],
        [
            "Near you",
            (limit?: number) => getShowsNearZip("10801", 25, undefined, limit),
        ],
    ] as const)(
        "%s keeps the default cap and exposes bounded alternatives for feed selection",
        async (_name, load) => {
            expect(await load()).toHaveLength(8);
            const pool = await load(50);
            expect(pool).toHaveLength(50);
            expect(pool[49].id).toBe(50);
            expect(await load(100)).toHaveLength(50);
            expect(candidates).toHaveLength(50);
        },
    );
});
