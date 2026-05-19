import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AdminPipelinesData } from "@/lib/admin/pipelines";

const mocks = vi.hoisted(() => ({
    listAdminPipelines: vi.fn(),
}));

vi.mock("@/lib/admin/pipelines", () => ({
    listAdminPipelines: mocks.listAdminPipelines,
}));

import AdminPipelinesPage from "./page";

const pipelinesData: AdminPipelinesData = {
    summaries: [
        {
            pipelineKey: "scraper",
            pipelineName: "Venue scraper",
            runCount: 3,
            averageDurationSeconds: 93.4,
            averageSuccessRate: 96.2,
            totalShowsSaved: 210,
            totalErrors: 2,
            latestExportedAt: "2026-05-19T12:00:00.000Z",
            latestRun: {
                id: 7,
                runKey: "scraper:2026-05-19T12:00:00.000Z",
                pipelineKey: "scraper",
                pipelineName: "Venue scraper",
                status: "degraded",
                exportedAt: "2026-05-19T12:00:00.000Z",
                durationSeconds: 102.5,
                showsScraped: 120,
                showsSaved: 116,
                showsInserted: 44,
                showsUpdated: 72,
                showsFailedSave: 1,
                showsSkippedDedup: 5,
                showsValidationFailed: 0,
                showsDbErrors: 1,
                clubsProcessed: 12,
                clubsSuccessful: 10,
                clubsFailed: 2,
                errorsTotal: 2,
                successRate: 83.3,
            },
        },
    ],
    recentRuns: [
        {
            id: 7,
            runKey: "scraper:2026-05-19T12:00:00.000Z",
            pipelineKey: "scraper",
            pipelineName: "Venue scraper",
            status: "degraded",
            exportedAt: "2026-05-19T12:00:00.000Z",
            durationSeconds: 102.5,
            showsScraped: 120,
            showsSaved: 116,
            showsInserted: 44,
            showsUpdated: 72,
            showsFailedSave: 1,
            showsSkippedDedup: 5,
            showsValidationFailed: 0,
            showsDbErrors: 1,
            clubsProcessed: 12,
            clubsSuccessful: 10,
            clubsFailed: 2,
            errorsTotal: 2,
            successRate: 83.3,
        },
    ],
    latestSlowClubs: [
        {
            clubId: 42,
            clubName: "Comedy Cellar",
            numShows: 24,
            executionTimeSeconds: 17.4,
            success: true,
            errorMessage: null,
            showsSaved: 20,
            errorsCount: 0,
            httpStatus: 200,
            botBlockDetected: false,
            playwrightFallbackUsed: true,
        },
    ],
    latestFailedClubs: [
        {
            clubId: 43,
            clubName: "Broken Club",
            numShows: 0,
            executionTimeSeconds: 9.3,
            success: false,
            errorMessage: "403 from source",
            showsSaved: 0,
            errorsCount: 1,
            httpStatus: 403,
            botBlockDetected: true,
            playwrightFallbackUsed: false,
        },
    ],
    latestErrors: [
        {
            clubName: "Broken Club",
            errorMessage: "403 from source",
            executionTimeSeconds: 9.3,
        },
    ],
};

beforeEach(() => {
    vi.clearAllMocks();
    mocks.listAdminPipelines.mockResolvedValue(pipelinesData);
});

describe("AdminPipelinesPage", () => {
    it("renders pipeline status, recent runs, and latest failures", async () => {
        const element = await AdminPipelinesPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("Admin · Pipelines");
        expect(markup).toContain("Pipeline status");
        expect(markup).toContain("Venue scraper");
        expect(markup).toContain("83.3%");
        expect(markup).toContain("Recent runs");
        expect(markup).toContain("Comedy Cellar");
        expect(markup).toContain("Broken Club");
        expect(markup).toContain("Bot block");
    });

    it("renders empty states", async () => {
        mocks.listAdminPipelines.mockResolvedValue({
            summaries: [],
            recentRuns: [],
            latestSlowClubs: [],
            latestFailedClubs: [],
            latestErrors: [],
        } satisfies AdminPipelinesData);

        const element = await AdminPipelinesPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain(
            "No pipeline run summaries have been recorded yet.",
        );
        expect(markup).toContain("No recent runs found.");
        expect(markup).toContain("No club timing rows found.");
        expect(markup).toContain("No failures in the latest run.");
    });
});
