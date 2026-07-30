import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        club: { findUnique: vi.fn() },
        show: { findMany: vi.fn(), findFirst: vi.fn() },
        $queryRaw: vi.fn(),
    },
}));
vi.mock("@/lib/data/comedian/imageAssets", () => ({
    buildComedianImageUrls: vi.fn(
        ({
            name,
            hasImage,
            activeAsset,
        }: {
            name: string;
            hasImage?: boolean | null;
            activeAsset?: { avatarPath?: string | null } | null;
        }) => ({
            imageUrl: activeAsset?.avatarPath
                ? `https://cdn.example.com/${activeAsset.avatarPath}`
                : hasImage
                  ? `https://cdn.example.com/${name}.jpg`
                  : "",
            avatarUrl: "",
            heroUrl: "",
        }),
    ),
}));
vi.mock("@/util/imageUtil", () => ({
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.jpg`,
    ),
}));

import { db } from "@/lib/db";
import {
    buildFrequentPerformersQuery,
    findClubHighlights,
} from "./findClubHighlights";

const mockFindClub = vi.mocked(db.club.findUnique);
const mockFindManyShows = vi.mocked(db.show.findMany);
const mockFindNextShow = vi.mocked(db.show.findFirst);
const mockQueryRaw = vi.mocked(db.$queryRaw);

type SqlLike = { strings: readonly string[]; values: readonly unknown[] };

function makeShow(id: number, date: string) {
    return {
        id,
        name: `Show ${id}`,
        date: new Date(date),
        popularity: 0.5,
        room: null,
        tickets: [],
        club: {
            id: 7,
            name: "Comedy Cellar",
            address: "117 Macdougal St",
            city: "New York",
            state: "NY",
            zipCode: "10012",
            hasImage: true,
            timezone: "America/New_York",
        },
        lineupItems: [],
        taggedShows: [],
    };
}

function makePerformer(id: number, overrides: Record<string, unknown> = {}) {
    return {
        id,
        uuid: `uuid-${id}`,
        name: `Performer ${id}`,
        instagram_account: null,
        instagram_followers: null,
        tiktok_account: null,
        tiktok_followers: null,
        youtube_account: null,
        youtube_followers: null,
        website: null,
        popularity: 0.5,
        linktree: null,
        has_image: true,
        active_avatar_path: null,
        show_count: 4,
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    mockFindClub.mockResolvedValue({
        timezone: "America/New_York",
    } as never);
    mockFindManyShows.mockResolvedValue([]);
    mockFindNextShow.mockResolvedValue(null);
    mockQueryRaw.mockResolvedValue([]);
});

describe("findClubHighlights", () => {
    it("returns null for a missing or inactive club without querying highlights", async () => {
        mockFindClub.mockResolvedValue(null);

        await expect(findClubHighlights(404)).resolves.toBeNull();

        expect(mockFindManyShows).not.toHaveBeenCalled();
        expect(mockFindNextShow).not.toHaveBeenCalled();
        expect(mockQueryRaw).not.toHaveBeenCalled();
    });

    it("uses the club timezone even when its local calendar date differs from UTC", async () => {
        mockFindClub.mockResolvedValue({
            timezone: "America/Los_Angeles",
        } as never);
        const now = new Date("2026-07-30T02:00:00.000Z");

        await findClubHighlights(7, { now });

        expect(mockFindManyShows).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    clubId: 7,
                    date: {
                        gte: new Date("2026-07-29T07:00:00.000Z"),
                        lte: new Date("2026-07-30T06:59:59.999Z"),
                    },
                },
            }),
        );
        expect(mockFindNextShow).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    clubId: 7,
                    date: { gt: new Date("2026-07-30T06:59:59.999Z") },
                },
            }),
        );
    });

    it("falls back to the default show timezone when the club has none", async () => {
        mockFindClub.mockResolvedValue({ timezone: null } as never);

        await findClubHighlights(7, {
            now: new Date("2026-01-15T04:30:00.000Z"),
        });

        expect(mockFindManyShows).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    clubId: 7,
                    date: {
                        gte: new Date("2026-01-14T05:00:00.000Z"),
                        lte: new Date("2026-01-15T04:59:59.999Z"),
                    },
                },
            }),
        );
    });

    it("maps tonight shows, the next later-day show, and qualified performers", async () => {
        mockFindManyShows.mockResolvedValue([
            makeShow(1, "2026-07-30T00:00:00.000Z"),
        ] as never);
        mockFindNextShow.mockResolvedValue(
            makeShow(2, "2026-07-31T00:00:00.000Z") as never,
        );
        mockQueryRaw.mockResolvedValue([
            makePerformer(1),
            makePerformer(2, {
                active_avatar_path: "comedians/2/avatar.webp",
            }),
            makePerformer(3),
        ] as never);

        const result = await findClubHighlights(7, {
            now: new Date("2026-07-30T02:00:00.000Z"),
        });

        expect(result?.tonightShows.map((show) => show.id)).toEqual([1]);
        expect(result?.nextShow?.id).toBe(2);
        expect(result?.frequentPerformers).toHaveLength(3);
        expect(result?.frequentPerformers[1]).toMatchObject({
            id: 2,
            uuid: "uuid-2",
            imageUrl: "https://cdn.example.com/comedians/2/avatar.webp",
            showCount: 4,
            socialData: { id: 2, popularity: 0.5 },
        });
    });

    it("suppresses an untrustworthy ranking with fewer than three performers", async () => {
        mockQueryRaw.mockResolvedValue([
            makePerformer(1),
            makePerformer(2),
        ] as never);

        const result = await findClubHighlights(7, {
            now: new Date("2026-07-30T02:00:00.000Z"),
        });

        expect(result?.frequentPerformers).toEqual([]);
    });

    it("builds a 12-month distinct-show canonical ranking with coverage and visibility gates", () => {
        const since = new Date("2025-07-30T02:00:00.000Z");
        const until = new Date("2026-07-30T02:00:00.000Z");
        const query = buildFrequentPerformersQuery(
            7,
            since,
            until,
        ) as unknown as SqlLike;
        const sql = query.strings.join(" ");

        expect(sql).toContain(
            "COALESCE(performer.parent_comedian_id, performer.id)",
        );
        expect(sql).toContain("COUNT(DISTINCT ca.show_id)");
        expect(sql).toContain("coverage.lineup_show_count >=");
        expect(sql).toContain("performer.visible = true");
        expect(sql).toContain("c.visible = true");
        expect(sql).toContain("c.parent_comedian_id IS NULL");
        expect(sql).toContain("t.user_facing = false");
        expect(query.values).toEqual(
            expect.arrayContaining([7, since, until, 10, 8]),
        );
    });
});
