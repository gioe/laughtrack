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
                    comedianPodcasts: {
                        some: {
                            reviewStatus: "accepted",
                        },
                    },
                },
            }),
        );
    });
});
