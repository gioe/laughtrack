/**
 * @vitest-environment happy-dom
 */

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { AdminPipelineRun } from "@/lib/admin/pipelines";
import AdminPipelineRunsTable from "./AdminPipelineRunsTable";

const runs: AdminPipelineRun[] = [
    {
        id: 7,
        runKey: "scraper:2026-05-19T12:00:00.000Z",
        pipelineKey: "scraper",
        pipelineName: "Scraper pipeline run details",
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
        workflowStatus: "failure",
        failureSummary: "Failed jobs: Build: Build",
    },
];

afterEach(() => {
    cleanup();
});

describe("AdminPipelineRunsTable", () => {
    it("groups runs by pipeline", () => {
        render(
            <AdminPipelineRunsTable
                runs={[
                    runs[0],
                    {
                        ...runs[0],
                        id: 8,
                        runKey: "scraper:2026-05-18T12:00:00.000Z",
                    },
                ]}
            />,
        );

        expect(
            screen.getAllByText("Scraper pipeline run details"),
        ).toHaveLength(1);
        expect(screen.getAllByText("2").length).toBeGreaterThan(0);
        expect(
            screen.queryByText("scraper:2026-05-18T12:00:00.000Z"),
        ).toBeNull();
    });

    it("expands a GitHub Actions row to show workflow details and links", () => {
        render(<AdminPipelineRunsTable runs={runs} />);

        expect(screen.queryByText("Workflow")).toBeNull();
        expect(screen.queryByText("Shows inserted")).toBeNull();

        fireEvent.click(
            screen.getByRole("button", {
                name: /Scraper pipeline run details scraper/,
            }),
        );
        fireEvent.click(
            screen.getByRole("button", {
                name: /scraper:2026-05-19T12:00:00.000Z/,
            }),
        );

        expect(screen.getByText("Workflow")).toBeTruthy();
        expect(
            screen.getAllByText("Scraper Production Run").length,
        ).toBeGreaterThan(0);
        expect(screen.getByText("Event")).toBeTruthy();
        expect(screen.getByText("schedule")).toBeTruthy();
        expect(screen.getByText("Failure reason")).toBeTruthy();
        expect(screen.getByText("Failed jobs: Build: Build")).toBeTruthy();
        expect(screen.queryByText("Shows inserted")).toBeNull();
        expect(
            screen.getByRole("link", { name: /Open run/ }).getAttribute("href"),
        ).toBe("https://github.com/example/repo/actions/runs/123");
    });

    it("expands a scraper row to show scraper metrics", () => {
        render(
            <AdminPipelineRunsTable
                runs={[
                    {
                        ...runs[0],
                        source: null,
                        runUrl: null,
                        workflowName: null,
                        event: null,
                        actor: null,
                        ref: null,
                        sha: null,
                        runAttempt: null,
                        runNumber: null,
                        displayTitle: null,
                        workflowStatus: null,
                        failureSummary: null,
                    },
                ]}
            />,
        );

        fireEvent.click(
            screen.getByRole("button", {
                name: /Scraper pipeline run details scraper/,
            }),
        );
        fireEvent.click(
            screen.getByRole("button", {
                name: /scraper:2026-05-19T12:00:00.000Z/,
            }),
        );

        expect(screen.getByText("Shows inserted")).toBeTruthy();
        expect(screen.getByText("44")).toBeTruthy();
        expect(screen.getByText("Skipped duplicates")).toBeTruthy();
        expect(screen.queryByText("Workflow")).toBeNull();
    });

    it("renders an empty state", () => {
        render(<AdminPipelineRunsTable runs={[]} />);

        expect(screen.getByText("No recent runs found.")).toBeTruthy();
    });
});
