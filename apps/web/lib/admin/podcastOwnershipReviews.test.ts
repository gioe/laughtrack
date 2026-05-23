import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    podcastCandidateReviewFindMany: vi.fn(),
    comedianPodcastFindMany: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        podcastCandidateReview: {
            findMany: mocks.podcastCandidateReviewFindMany,
        },
        comedianPodcast: {
            findMany: mocks.comedianPodcastFindMany,
        },
    },
}));

import { listPodcastOwnershipReviews } from "./podcastOwnershipReviews";

beforeEach(() => {
    vi.clearAllMocks();
    mocks.podcastCandidateReviewFindMany.mockResolvedValue([]);
    mocks.comedianPodcastFindMany.mockResolvedValue([]);
});

describe("listPodcastOwnershipReviews", () => {
    it("selects and serializes podcast episode counts for admin sorting", async () => {
        const createdAt = new Date("2026-05-17T12:00:00.000Z");
        const updatedAt = new Date("2026-05-18T12:00:00.000Z");
        mocks.podcastCandidateReviewFindMany.mockResolvedValue([
            {
                id: 12,
                comedianId: 42,
                podcastId: 99,
                source: "podcast-index",
                sourcePodcastId: "feed-99",
                candidateStatus: "pending",
                associationType: "host",
                confidence: 0.91,
                evidence: { matched_name: "Jane Comic" },
                createdAt,
                updatedAt,
                comedian: {
                    id: 42,
                    uuid: "uuid-42",
                    name: "Jane Comic",
                    popularity: 74,
                },
                podcast: {
                    id: 99,
                    slug: "jane-show",
                    title: "The Jane Show",
                    authorName: "Jane Comic",
                    _count: { episodes: 12 },
                    imageUrl: null,
                    websiteUrl: "https://pod.example",
                    feedUrl: "https://pod.example/feed.xml",
                    denyListEntries: [],
                },
            },
        ]);

        const reviews = await listPodcastOwnershipReviews();

        expect(mocks.podcastCandidateReviewFindMany).toHaveBeenCalledWith(
            expect.objectContaining({
                select: expect.objectContaining({
                    podcast: {
                        select: expect.objectContaining({
                            _count: {
                                select: {
                                    episodes: true,
                                },
                            },
                        }),
                    },
                }),
            }),
        );
        expect(reviews[0].podcast?.episodeCount).toBe(12);
    });
});
