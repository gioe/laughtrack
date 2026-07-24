import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/lib/discovery/featureSnapshotJob", () => ({
    runDiscoveryFeatureSnapshotJob: vi.fn(),
}));

import { GET, POST } from "./route";
import { runDiscoveryFeatureSnapshotJob } from "@/lib/discovery/featureSnapshotJob";

const mockRunJob = vi.mocked(runDiscoveryFeatureSnapshotJob);
const ORIGINAL_CRON_SECRET = process.env.CRON_SECRET;

function makeRequest(
    headers: Record<string, string> = {},
    url = "http://localhost/api/cron/discovery-feature-snapshots",
    method = "GET",
): NextRequest {
    return new NextRequest(url, { method, headers });
}

function result(overrides: Record<string, unknown> = {}) {
    return {
        asOf: "2026-09-01T00:00:00.000Z",
        processed: 3,
        succeeded: 3,
        failed: 0,
        stale: 0,
        failures: [],
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
    process.env.CRON_SECRET = "test-secret-value";
});

afterEach(() => {
    if (ORIGINAL_CRON_SECRET === undefined) {
        delete process.env.CRON_SECRET;
    } else {
        process.env.CRON_SECRET = ORIGINAL_CRON_SECRET;
    }
});

describe("GET /api/cron/discovery-feature-snapshots", () => {
    it("returns 401 without the configured cron bearer", async () => {
        const response = await GET(makeRequest());

        expect(response.status).toBe(401);
        expect(mockRunJob).not.toHaveBeenCalled();
    });

    it("returns 401 for the wrong bearer or an unset secret", async () => {
        const wrong = await GET(
            makeRequest({ authorization: "Bearer wrong-secret" }),
        );
        delete process.env.CRON_SECRET;
        const unset = await GET(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(wrong.status).toBe(401);
        expect(unset.status).toBe(401);
        expect(mockRunJob).not.toHaveBeenCalled();
    });

    it("runs the bounded snapshot job for Vercel cron", async () => {
        mockRunJob.mockResolvedValue(result());

        const response = await GET(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(response.status).toBe(200);
        expect(await response.json()).toEqual(result());
        expect(mockRunJob).toHaveBeenCalledWith({ asOf: undefined });
    });

    it("accepts a fixed as-of time for reproducible manual runs", async () => {
        mockRunJob.mockResolvedValue(result());

        const response = await GET(
            makeRequest(
                { authorization: "Bearer test-secret-value" },
                "http://localhost/api/cron/discovery-feature-snapshots?asOf=2026-09-01T15%3A30%3A00Z",
            ),
        );

        expect(response.status).toBe(200);
        expect(mockRunJob).toHaveBeenCalledWith({
            asOf: new Date("2026-09-01T15:30:00.000Z"),
        });
    });

    it("rejects an invalid as-of time", async () => {
        const response = await GET(
            makeRequest(
                { authorization: "Bearer test-secret-value" },
                "http://localhost/api/cron/discovery-feature-snapshots?asOf=nope",
            ),
        );

        expect(response.status).toBe(400);
        expect(await response.json()).toEqual({ error: "invalid_as_of" });
        expect(mockRunJob).not.toHaveBeenCalled();
    });

    it("returns a failing status with partial-run counts", async () => {
        mockRunJob.mockResolvedValue(
            result({
                succeeded: 2,
                failed: 1,
                stale: 1,
                failures: [{ showId: 7, error: "write failed" }],
            }),
        );

        const response = await GET(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(response.status).toBe(500);
        expect(await response.json()).toMatchObject({
            error: "discovery_feature_snapshot_partial_failure",
            processed: 3,
            succeeded: 2,
            failed: 1,
            stale: 1,
        });
    });

    it("returns 500 when the job cannot load its batch", async () => {
        mockRunJob.mockRejectedValue(new Error("database unavailable"));

        const response = await GET(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(response.status).toBe(500);
        expect(await response.json()).toEqual({
            error: "discovery_feature_snapshot_job_failed",
        });
    });
});

describe("POST /api/cron/discovery-feature-snapshots", () => {
    it("supports authenticated manual invocations", async () => {
        mockRunJob.mockResolvedValue(result());

        const response = await POST(
            makeRequest(
                { authorization: "Bearer test-secret-value" },
                "http://localhost/api/cron/discovery-feature-snapshots",
                "POST",
            ),
        );

        expect(response.status).toBe(200);
        expect(mockRunJob).toHaveBeenCalledOnce();
    });
});
