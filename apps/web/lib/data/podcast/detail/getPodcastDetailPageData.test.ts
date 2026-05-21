import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotFoundError } from "../../../../objects/NotFoundError";

const { mockFindFirst } = vi.hoisted(() => ({
    mockFindFirst: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        podcast: {
            findFirst: mockFindFirst,
        },
    },
}));

import {
    getPodcastDetailPageData,
    getPodcastDetailPageDataById,
} from "./getPodcastDetailPageData";

beforeEach(() => {
    vi.clearAllMocks();
    mockFindFirst.mockResolvedValue(null);
});

describe("getPodcastDetailPageData", () => {
    it("looks up slug detail pages only for podcasts with accepted comedian ownership", async () => {
        await expect(getPodcastDetailPageData("chrissy-chaos")).rejects.toThrow(
            NotFoundError,
        );

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    slug: "chrissy-chaos",
                    denyListEntries: {
                        none: {
                            restoredAt: null,
                        },
                    },
                    comedianPodcasts: {
                        some: {
                            reviewStatus: "accepted",
                        },
                    },
                },
            }),
        );
    });

    it("looks up id detail pages only for podcasts with accepted comedian ownership", async () => {
        await expect(getPodcastDetailPageDataById(42)).rejects.toThrow(
            NotFoundError,
        );

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                where: {
                    id: 42,
                    denyListEntries: {
                        none: {
                            restoredAt: null,
                        },
                    },
                    comedianPodcasts: {
                        some: {
                            reviewStatus: "accepted",
                        },
                    },
                },
            }),
        );
    });

    it("selects favorite rows when a profile id is provided", async () => {
        await expect(
            getPodcastDetailPageData("chrissy-chaos", "profile-123"),
        ).rejects.toThrow(NotFoundError);

        expect(mockFindFirst).toHaveBeenCalledWith(
            expect.objectContaining({
                select: expect.objectContaining({
                    favorites: {
                        where: { profileId: "profile-123" },
                        select: { id: true },
                    },
                }),
            }),
        );
    });
});
