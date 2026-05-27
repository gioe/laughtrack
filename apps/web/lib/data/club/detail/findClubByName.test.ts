import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { club: { findFirst: vi.fn() } },
}));

vi.mock("@/util/imageUtil", () => ({
    buildClubHeroImageUrl: vi.fn((path?: string | null) =>
        path ? `https://cdn.example.com/${path}` : "",
    ),
    buildClubImageUrl: vi.fn(
        (name: string) => `https://cdn.example.com/clubs/${name}.png`,
    ),
}));

import { db } from "@/lib/db";
import { buildClubHeroImageUrl } from "@/util/imageUtil";
import { findClubByName } from "./findClubByName";

const mockFindFirst = vi.mocked(db.club.findFirst);
const mockBuildClubHeroImageUrl = vi.mocked(buildClubHeroImageUrl);

function makeHelper(slug = "Comedy Cellar") {
    return {
        getSlug: () => slug,
    };
}

function makeClubRow() {
    return {
        id: 1,
        name: "Comedy Cellar",
        website: "https://www.comedycellar.com",
        address: "117 MacDougal St",
        city: "New York",
        state: "NY",
        zipCode: "10012",
        hasImage: true,
        status: "active",
        closedAt: null,
        clubType: "club",
        phoneNumber: null,
        description: null,
        hours: null,
        chain: null,
        imageAssets: [{ heroPath: "clubs/Comedy%20Cellar-hero.jpg" }],
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

describe("findClubByName", () => {
    it("threads the active club hero asset through the detail DTO", async () => {
        mockFindFirst.mockResolvedValue(makeClubRow() as never);

        const result = await findClubByName(makeHelper() as never);

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                select: expect.objectContaining({
                    imageAssets: {
                        where: { isActive: true },
                        select: { heroPath: true },
                        orderBy: { publishedAt: "desc" },
                        take: 1,
                    },
                }),
            }),
        );
        expect(mockBuildClubHeroImageUrl).toHaveBeenCalledWith(
            "clubs/Comedy%20Cellar-hero.jpg",
        );
        expect(result.heroUrl).toBe(
            "https://cdn.example.com/clubs/Comedy%20Cellar-hero.jpg",
        );
    });
});
