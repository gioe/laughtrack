import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
    getAdminOverviewData: vi.fn(),
}));

vi.mock("@/lib/admin/overview", () => ({
    getAdminOverviewData: mocks.getAdminOverviewData,
}));

import AdminOverviewPage from "./page";
import type { AdminOverviewData } from "@/lib/admin/overview";

const overviewData: AdminOverviewData = {
    latestRun: {
        id: 7,
        exportedAt: "2026-05-18T01:00:00.000Z",
        durationSeconds: 93.4,
        showsScraped: 120,
        showsSaved: 116,
        clubsProcessed: 12,
        clubsSuccessful: 10,
        clubsFailed: 2,
        errorsTotal: 3,
        successRate: 83.333,
    },
    recentFailureTrend: [
        {
            id: 7,
            exportedAt: "2026-05-18T01:00:00.000Z",
            clubsFailed: 2,
            errorsTotal: 3,
            successRate: 83.333,
        },
    ],
    latestFailedClubs: [
        {
            clubId: 42,
            clubName: "Comedy Cellar",
            errorMessage: "403 from source",
            httpStatus: 403,
            botBlockDetected: true,
            executionTimeSeconds: 12.5,
        },
    ],
    outliers: {
        staleScraperKeys: [
            {
                scraperKey: "seatengine",
                enabledSourceCount: 3,
                recentShowCount: 0,
                mostRecentScrape: null,
            },
        ],
        sourceIssues: [],
        clubsWithoutFutureShows: [
            {
                clubId: 12,
                clubName: "No Future Club",
                city: "Austin",
                state: "TX",
                enabledSourceCount: 1,
                lastShowDate: "2026-05-01T01:00:00.000Z",
            },
        ],
        incompleteShows: [
            {
                showId: 99,
                showName: null,
                showDate: "2026-05-20T01:00:00.000Z",
                clubId: 12,
                clubName: "No Future Club",
                missingFields: ["title", "tickets"],
            },
        ],
        missingMetadata: [],
        pendingReviews: [
            {
                queue: "Podcast candidates",
                count: 4,
                oldestCreatedAt: "2026-05-10T01:00:00.000Z",
            },
        ],
    },
};

beforeEach(() => {
    vi.clearAllMocks();
});

describe("AdminOverviewPage", () => {
    it("renders scraper run health, failures, and insight queues", async () => {
        mocks.getAdminOverviewData.mockResolvedValue(overviewData);

        const element = await AdminOverviewPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("Scraper health");
        expect(markup).toContain("83.3%");
        expect(markup).toContain("Comedy Cellar");
        expect(markup).toContain("Bot block");
        expect(markup).toContain("Stale scraper keys");
        expect(markup).toContain("seatengine");
        expect(markup).toContain("Clubs without future shows");
        expect(markup).toContain('href="/admin/clubs/12"');
        expect(markup).toContain("Pending reviews");
    });

    it("renders an empty run-summary state", async () => {
        mocks.getAdminOverviewData.mockResolvedValue({
            ...overviewData,
            latestRun: null,
            recentFailureTrend: [],
            latestFailedClubs: [],
            outliers: {
                staleScraperKeys: [],
                sourceIssues: [],
                clubsWithoutFutureShows: [],
                incompleteShows: [],
                missingMetadata: [],
                pendingReviews: [],
            },
        } satisfies AdminOverviewData);

        const element = await AdminOverviewPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("No scraper run summaries have landed yet.");
        expect(markup).toContain("No urgent outliers in this queue.");
    });
});
