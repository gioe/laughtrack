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
                runUrl: null,
                source: null,
                workflowName: null,
                event: null,
                actor: null,
                ref: null,
                sha: null,
                runAttempt: null,
                runNumber: null,
                displayTitle: null,
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
            runUrl: "https://github.com/example/repo/actions/runs/123",
            source: "github_actions",
            workflowName: "Scraper Production Run",
            event: "schedule",
            actor: "mattgioe",
            ref: "main",
            sha: "abc123def4567890",
            runAttempt: "1",
            runNumber: "88",
            displayTitle: "Scraper Production Run",
        },
        {
            id: 8,
            runKey: "github_actions_social_follower_refresh:123:1",
            pipelineKey: "github_actions_social_follower_refresh",
            pipelineName: "Github Actions Social Follower Refresh",
            status: "healthy",
            exportedAt: "2026-05-18T12:00:00.000Z",
            durationSeconds: 0,
            showsScraped: 0,
            showsSaved: 0,
            showsInserted: 0,
            showsUpdated: 0,
            showsFailedSave: 0,
            showsSkippedDedup: 0,
            showsValidationFailed: 0,
            showsDbErrors: 0,
            clubsProcessed: 0,
            clubsSuccessful: 0,
            clubsFailed: 0,
            errorsTotal: 0,
            successRate: 100,
            runUrl: "https://github.com/example/repo/actions/runs/456",
            source: "github_actions",
            workflowName: "Social Follower Refresh",
            event: "workflow_dispatch",
            actor: "mattgioe",
            ref: "main",
            sha: "abc123def4567890",
            runAttempt: "1",
            runNumber: "89",
            displayTitle: "Social Follower Refresh",
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
    it("renders the pipeline runs table first", async () => {
        const element = await AdminPipelinesPage();
        const markup = renderToStaticMarkup(element);

        expect(markup).toContain("Admin · Pipelines");
        expect(markup).toContain("Pipeline runs");
        expect(markup).toContain("Recent runs");
        expect(markup).toContain("Venue scraper");
        expect(markup).toContain("83.3%");
        expect(markup).toContain("Github Actions Social Follower Refresh");
        expect(markup).not.toContain("Slowest latest-run clubs");
        expect(markup).not.toContain("Latest failures");
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

        expect(markup).toContain("No recent runs found.");
    });
});
