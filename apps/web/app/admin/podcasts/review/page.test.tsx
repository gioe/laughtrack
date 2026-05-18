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
    it("renders pending candidate count and manager", async () => {
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
                comedian: { id: 42, name: "Jane Comic", uuid: "uuid-42" },
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
        ]);

        const element = await AdminPodcastOwnershipReviewPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("Admin · Podcast Reviews");
        expect(markup).toContain("1 pending candidate");
        expect(markup).toContain("podcast-review-manager");
    });
});
