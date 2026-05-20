import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    findMany: vi.fn(),
    findOwnerships: vi.fn(),
}));

vi.mock("@/lib/db", () => ({
    db: {
        podcastCandidateReview: {
            findMany: mocks.findMany,
        },
        comedianPodcast: {
            findMany: mocks.findOwnerships,
        },
    },
}));

vi.mock("@/ui/pages/admin/podcasts/AdminPodcastOwnershipReviewManager", () => ({
    default: ({ candidates }: { candidates: Array<{ id: number }> }) => (
        <div data-testid="podcast-review-manager">
            {candidates.length} candidates
        </div>
    ),
}));

import AdminPodcastOwnershipReviewPage from "./page";

beforeEach(() => {
    vi.clearAllMocks();
    mocks.findMany.mockResolvedValue([]);
    mocks.findOwnerships.mockResolvedValue([]);
});

describe("AdminPodcastOwnershipReviewPage", () => {
    it("renders total and pending candidate counts with manager", async () => {
        mocks.findMany.mockResolvedValue([
            {
                id: 12,
                comedianId: 42,
                podcastId: 99,
                source: "podcast-index",
                sourcePodcastId: "feed-99",
                candidateStatus: "pending",
                associationType: "host",
                confidence: 0.91,
                evidence: {},
                createdAt: new Date("2026-05-17T12:00:00Z"),
                updatedAt: new Date("2026-05-17T12:00:00Z"),
                comedian: {
                    id: 42,
                    name: "Jane Comic",
                    uuid: "uuid-42",
                    popularity: 74,
                },
                podcast: {
                    id: 99,
                    slug: "jane-show",
                    title: "The Jane Show",
                    authorName: "Jane Comic",
                    imageUrl: null,
                    websiteUrl: null,
                    feedUrl: null,
                },
            },
            {
                id: 13,
                comedianId: 43,
                podcastId: 100,
                source: "podcast-index",
                sourcePodcastId: "feed-100",
                candidateStatus: "rejected",
                associationType: "host",
                confidence: 0.72,
                evidence: {},
                createdAt: new Date("2026-05-18T12:00:00Z"),
                updatedAt: new Date("2026-05-18T12:00:00Z"),
                comedian: {
                    id: 43,
                    name: "Other Comic",
                    uuid: "uuid-43",
                    popularity: 12,
                },
                podcast: {
                    id: 100,
                    slug: "other-show",
                    title: "Other Show",
                    authorName: "Other Comic",
                    imageUrl: null,
                    websiteUrl: null,
                    feedUrl: null,
                },
            },
        ]);

        const element = await AdminPodcastOwnershipReviewPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("Admin · Podcast Reviews");
        expect(markup).toContain("2 total candidates");
        expect(markup).toContain("1 pending");
        expect(markup).toContain("podcast-review-manager");
    });
});
