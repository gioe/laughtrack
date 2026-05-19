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
    },
];

afterEach(() => {
    cleanup();
});

describe("AdminPipelineRunsTable", () => {
    it("expands a run row to show details and links", () => {
        render(<AdminPipelineRunsTable runs={runs} />);

        expect(screen.queryByText("Shows inserted")).toBeNull();

        fireEvent.click(
            screen.getByRole("button", {
                name: /Venue scraper scraper:2026-05-19T12:00:00.000Z/,
            }),
        );

        expect(screen.getByText("Shows inserted")).toBeTruthy();
        expect(screen.getByText("44")).toBeTruthy();
        expect(screen.getByText("Skipped duplicates")).toBeTruthy();
        expect(
            screen.getByRole("link", { name: /Open run/ }).getAttribute("href"),
        ).toBe("https://github.com/example/repo/actions/runs/123");
    });

    it("renders an empty state", () => {
        render(<AdminPipelineRunsTable runs={[]} />);

        expect(screen.getByText("No recent runs found.")).toBeTruthy();
    });
});
