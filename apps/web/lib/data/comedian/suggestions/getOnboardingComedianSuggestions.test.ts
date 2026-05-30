import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        comedian: { findMany: vi.fn() },
        $queryRaw: vi.fn(),
    },
}));
vi.mock("@/util/imageUtil", () => ({
    buildComedianImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/${name}.png`,
    ),
}));

import {
    getOnboardingComedianSuggestions,
    ONBOARDING_POPULARITY_FLOOR,
    ONBOARDING_SUGGESTION_LIMIT,
} from "./getOnboardingComedianSuggestions";
import { db } from "@/lib/db";

const mockQueryRaw = vi.mocked(db.$queryRaw);
const mockFindMany = vi.mocked(db.comedian.findMany);

// The Prisma.sql tagged template exposes the static fragments (`strings`) and the
// interpolated parameters (`values`) — assert against both so we verify the
// generated SQL without depending on a live database.
function sqlText(arg: unknown): string {
    const sql = arg as { strings?: string[] };
    return Array.isArray(sql.strings) ? sql.strings.join(" ") : String(arg);
}
function sqlValues(arg: unknown): unknown[] {
    const sql = arg as { values?: unknown[] };
    return Array.isArray(sql.values) ? sql.values : [];
}

function makeRow(id: number, popularity = 0.8, name = `Comedian ${id}`) {
    return {
        id,
        uuid: `uuid-${id}`,
        name,
        linktree: null,
        instagramAccount: null,
        instagramFollowers: null,
        tiktokAccount: null,
        tiktokFollowers: null,
        youtubeAccount: null,
        youtubeFollowers: null,
        website: null,
        popularity,
        hasImage: false,
        alternativeNames: [],
        taggedComedians: [],
        _count: { lineupItems: 0 },
        favoriteComedians: [],
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("getOnboardingComedianSuggestions", () => {
    it("exposes a 0.60 popularity floor constant", () => {
        expect(ONBOARDING_POPULARITY_FLOOR).toBe(0.6);
    });

    it("samples only comedians at or above the popularity floor", async () => {
        mockQueryRaw.mockResolvedValue([{ id: 1 }] as never);
        mockFindMany.mockResolvedValue([makeRow(1)] as never);

        await getOnboardingComedianSuggestions();

        expect(mockQueryRaw).toHaveBeenCalledTimes(1);
        const arg = mockQueryRaw.mock.calls[0][0];
        // Floor predicate present and parameterized with the named constant.
        expect(sqlText(arg)).toMatch(/c\.popularity\s*>=/i);
        expect(sqlValues(arg)).toContain(ONBOARDING_POPULARITY_FLOOR);
    });

    it("orders by the Efraimidis–Spirakis weighted-random key and bounds the result", async () => {
        mockQueryRaw.mockResolvedValue([] as never);

        await getOnboardingComedianSuggestions();

        const arg = mockQueryRaw.mock.calls[0][0];
        // Weighted-random ordering → varying membership AND popularity bias.
        expect(sqlText(arg).replace(/\s+/g, " ")).toMatch(
            /ORDER BY power\(random\(\), 1\.0 \/ c\.popularity\) DESC/i,
        );
        expect(sqlValues(arg)).toContain(ONBOARDING_SUGGESTION_LIMIT);
    });

    it("preserves the comedian-search eligibility filters", async () => {
        mockQueryRaw.mockResolvedValue([] as never);

        await getOnboardingComedianSuggestions();

        const text = sqlText(mockQueryRaw.mock.calls[0][0]);
        expect(text).toMatch(/parent_comedian_id"?\s+IS NULL/i); // aliases excluded
        expect(text).toMatch(/comedian_deny_list/i); // deny-list
        expect(text).toMatch(/restrictContent/i); // restricted tag
        expect(text).toMatch(/lineup_items/i); // upcoming-only
        expect(text).toMatch(/s\.date > NOW\(\)/i);
    });

    it("returns mapped comedians preserving the sampled order", async () => {
        // Sampling returns weighted-random order 3,1,2; findMany returns arbitrary order.
        mockQueryRaw.mockResolvedValue([
            { id: 3 },
            { id: 1 },
            { id: 2 },
        ] as never);
        mockFindMany.mockResolvedValue([
            makeRow(1),
            makeRow(2),
            makeRow(3),
        ] as never);

        const result = await getOnboardingComedianSuggestions();

        expect(result.map((c) => c.id)).toEqual([3, 1, 2]);
        expect(result[0]).toMatchObject({
            id: 3,
            name: "Comedian 3",
            imageUrl: "https://cdn.example.com/Comedian 3.png",
            socialData: { popularity: 0.8 },
        });
    });

    it("short-circuits to an empty array when nothing clears the floor", async () => {
        mockQueryRaw.mockResolvedValue([] as never);

        const result = await getOnboardingComedianSuggestions();

        expect(result).toEqual([]);
        expect(mockFindMany).not.toHaveBeenCalled();
    });

    it("requests favorite flags only when a profileId is supplied", async () => {
        mockQueryRaw.mockResolvedValue([{ id: 1 }] as never);
        mockFindMany.mockResolvedValue([makeRow(1)] as never);

        await getOnboardingComedianSuggestions("profile-123");
        const withProfile = mockFindMany.mock.calls[0][0]!.select as Record<
            string,
            unknown
        >;
        expect(withProfile.favoriteComedians).toEqual({
            where: { profileId: "profile-123" },
            select: { id: true },
        });

        vi.clearAllMocks();
        mockQueryRaw.mockResolvedValue([{ id: 1 }] as never);
        mockFindMany.mockResolvedValue([makeRow(1)] as never);

        await getOnboardingComedianSuggestions();
        const noProfile = mockFindMany.mock.calls[0][0]!.select as Record<
            string,
            unknown
        >;
        expect(noProfile.favoriteComedians).toBeUndefined();
    });
});
