import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db", () => ({
    db: { $queryRaw: vi.fn() },
}));

import { db } from "@/lib/db";
import { getAdminOverviewData } from "./overview";

const mockQueryRaw = vi.mocked(db.$queryRaw);

beforeEach(() => {
    vi.clearAllMocks();
});

describe("getAdminOverviewData", () => {
    it("maps scraper run summaries and insight queues from Postgres rows", async () => {
        mockQueryRaw
            .mockResolvedValueOnce([
                {
                    id: BigInt(7),
                    exported_at: new Date("2026-05-18T01:00:00Z"),
                    duration_seconds: 93.4,
                    shows_scraped: 120,
                    shows_saved: 116,
                    clubs_processed: 12,
                    clubs_successful: 10,
                    clubs_failed: 2,
                    errors_total: 3,
                    success_rate: 83.333,
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    id: BigInt(7),
                    exported_at: new Date("2026-05-18T01:00:00Z"),
                    clubs_failed: 2,
                    errors_total: 3,
                    success_rate: 83.333,
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    club_id: 42,
                    club_name: "Comedy Cellar",
                    error_message: "403 from source",
                    http_status: 403,
                    bot_block_detected: true,
                    execution_time_seconds: 12.5,
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    scraper_key: "seatengine",
                    enabled_source_count: BigInt(3),
                    recent_show_count: BigInt(0),
                    most_recent_scrape: null,
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    club_id: 11,
                    club_name: "Austin Room",
                    platform: "custom",
                    scraper_key: "",
                    source_url: null,
                    issue: "missing source locator",
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    club_id: 12,
                    club_name: "No Future Club",
                    city: "Austin",
                    state: "TX",
                    enabled_source_count: BigInt(1),
                    last_show_date: new Date("2026-05-01T01:00:00Z"),
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    show_id: 99,
                    show_name: null,
                    show_date: new Date("2026-05-20T01:00:00Z"),
                    club_id: 12,
                    club_name: "No Future Club",
                    missing_fields: ["title", "tickets"],
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    club_id: 13,
                    club_name: "Thin Metadata Club",
                    city: "Denver",
                    state: "CO",
                    missing_fields: ["description", "hours"],
                },
            ] as never)
            .mockResolvedValueOnce([
                {
                    queue: "Podcast candidates",
                    count: BigInt(4),
                    oldest_created_at: new Date("2026-05-10T01:00:00Z"),
                },
            ] as never);

        const data = await getAdminOverviewData();

        expect(data.latestRun).toMatchObject({
            id: 7,
            exportedAt: "2026-05-18T01:00:00.000Z",
            clubsFailed: 2,
            errorsTotal: 3,
            successRate: 83.333,
        });
        expect(data.recentFailureTrend).toHaveLength(1);
        expect(data.latestFailedClubs[0]).toMatchObject({
            clubId: 42,
            clubName: "Comedy Cellar",
            botBlockDetected: true,
        });
        expect(data.outliers.staleScraperKeys[0]).toMatchObject({
            scraperKey: "seatengine",
            enabledSourceCount: 3,
        });
        expect(data.outliers.pendingReviews[0]).toMatchObject({
            queue: "Podcast candidates",
            count: 4,
        });
        expect(mockQueryRaw).toHaveBeenCalledTimes(9);
    });

    it("returns empty dashboard states when no scraper run has been persisted", async () => {
        mockQueryRaw.mockResolvedValue([] as never);

        const data = await getAdminOverviewData();

        expect(data.latestRun).toBeNull();
        expect(data.latestFailedClubs).toEqual([]);
        expect(data.outliers.clubsWithoutFutureShows).toEqual([]);
    });
});
