import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("@/lib/db", () => ({
    db: {
        favoriteComedian: { findMany: vi.fn() },
        favoritePodcast: { findUnique: vi.fn() },
    },
}));

import { db } from "@/lib/db";
import {
    applyFavoriteOverlay,
    buildDetailCacheKey,
    isPodcastFavorite,
} from "./personalizedOverlay";
import { SortParamValue } from "@/objects/enum/sortParamValue";

const mockFavoriteComedianFindMany = vi.mocked(db.favoriteComedian.findMany);
const mockFavoritePodcastFindUnique = vi.mocked(db.favoritePodcast.findUnique);

beforeEach(() => {
    vi.clearAllMocks();
});

describe("buildDetailCacheKey", () => {
    it("keeps only whitelisted output params and excludes user identity", () => {
        const key = buildDetailCacheKey("comedian-detail-data", {
            slug: "jane-comic",
            timezone: "America/New_York",
            params: {
                page: "2",
                size: "10",
                sort: SortParamValue.DateAsc,
                filters: "free,standup",
                fromDate: "2026-08-01",
                zip: "10001",
                unboundedTrackingParam: "nope",
            } as never,
            userId: "user-123",
            profileId: "profile-123",
        });

        expect(key).toEqual([
            "comedian-detail-data",
            "slug:jane-comic",
            "timezone:America/New_York",
            "filters:free,standup",
            "fromDate:2026-08-01",
            "page:2",
            "size:10",
            "sort:date_asc",
            "zip:10001",
        ]);
        expect(key.join("|")).not.toContain("user-123");
        expect(key.join("|")).not.toContain("profile-123");
        expect(key.join("|")).not.toContain("unboundedTrackingParam");
    });
});

describe("applyFavoriteOverlay", () => {
    it("patches only matching comedian favorite flags for signed-in users", async () => {
        mockFavoriteComedianFindMany.mockResolvedValue([
            { comedianId: "comic-1" },
            { comedianId: "comic-3" },
        ] as never);

        const response = {
            data: { uuid: "comic-1", isFavorite: false },
            shows: [
                {
                    lineup: [
                        { uuid: "comic-1", isFavorite: false },
                        { uuid: "comic-2", isFavorite: true },
                    ],
                },
                {
                    lineup: [
                        { uuid: "comic-3" },
                        { uuid: "comic-1", isFavorite: false },
                    ],
                },
            ],
        };

        const personalized = await applyFavoriteOverlay(
            response,
            "profile-123",
        );

        expect(mockFavoriteComedianFindMany).toHaveBeenCalledWith({
            where: {
                profileId: "profile-123",
                comedianId: { in: ["comic-1", "comic-2", "comic-3"] },
            },
            select: { comedianId: true },
        });
        expect(personalized.data.isFavorite).toBe(true);
        expect(personalized.shows[0].lineup?.[0].isFavorite).toBe(true);
        expect(personalized.shows[0].lineup?.[1].isFavorite).toBe(false);
        expect(personalized.shows[1].lineup?.[0].isFavorite).toBe(true);
        expect(personalized.shows[1].lineup?.[1].isFavorite).toBe(true);
        expect(response.data.isFavorite).toBe(false);
        expect(response.shows[0].lineup?.[0].isFavorite).toBe(false);
    });

    it("sets anonymous favorite markers to false without querying", async () => {
        const response = {
            data: { uuid: "comic-1", isFavorite: true },
            shows: [{ lineup: [{ uuid: "comic-2", isFavorite: true }] }],
        };

        const personalized = await applyFavoriteOverlay(response, undefined);

        expect(mockFavoriteComedianFindMany).not.toHaveBeenCalled();
        expect(personalized.data.isFavorite).toBe(false);
        expect(personalized.shows[0].lineup?.[0].isFavorite).toBe(false);
        expect(response.data.isFavorite).toBe(true);
        expect(response.shows[0].lineup?.[0].isFavorite).toBe(true);
    });
});

describe("isPodcastFavorite", () => {
    it("checks podcast favorite status outside the cached detail fetch", async () => {
        mockFavoritePodcastFindUnique.mockResolvedValue({ id: 123 } as never);

        await expect(isPodcastFavorite(42, "profile-123")).resolves.toBe(true);

        expect(mockFavoritePodcastFindUnique).toHaveBeenCalledWith({
            where: {
                profileId_podcastId: {
                    profileId: "profile-123",
                    podcastId: 42,
                },
            },
            select: { id: true },
        });
    });
});
