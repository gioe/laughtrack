import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/lib/db", () => ({
    db: {
        $queryRaw: vi.fn(),
    },
}));

import { GET, POST } from "./route";
import { db } from "@/lib/db";

const mockQueryRaw = vi.mocked(db.$queryRaw);
const ORIGINAL_CRON_SECRET = process.env.CRON_SECRET;

function makeRequest(
    headers: Record<string, string> = {},
    url = "http://localhost/api/cron/cleanup-ticket-purchase-click-events",
    method = "GET",
): NextRequest {
    return new NextRequest(url, {
        method,
        headers,
    });
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

describe("GET /api/cron/cleanup-ticket-purchase-click-events", () => {
    it("returns 401 when no Authorization header is provided", async () => {
        const res = await GET(makeRequest());

        expect(res.status).toBe(401);
        expect(mockQueryRaw).not.toHaveBeenCalled();
    });

    it("returns 401 when the bearer token does not match CRON_SECRET", async () => {
        const res = await GET(
            makeRequest({ authorization: "Bearer wrong-secret" }),
        );

        expect(res.status).toBe(401);
        expect(mockQueryRaw).not.toHaveBeenCalled();
    });

    it("returns 401 when CRON_SECRET is unset", async () => {
        delete process.env.CRON_SECRET;

        const res = await GET(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(res.status).toBe(401);
        expect(mockQueryRaw).not.toHaveBeenCalled();
    });

    it("runs the retention helper and reports the deleted row count", async () => {
        mockQueryRaw.mockResolvedValue([
            {
                deleted_ticket_clicks: BigInt(7),
                deleted_discovery_impressions: BigInt(11),
            },
        ]);

        const res = await GET(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(res.status).toBe(200);
        expect(await res.json()).toEqual({
            deleted: 7,
            deletedTicketClicks: 7,
            deletedDiscoveryImpressions: 11,
            retentionMonths: 13,
        });
        expect(mockQueryRaw).toHaveBeenCalledOnce();
    });

    it("returns 500 when the cleanup query fails", async () => {
        mockQueryRaw.mockRejectedValue(new Error("database unavailable"));

        const res = await GET(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(res.status).toBe(500);
        expect(await res.json()).toEqual({
            error: "ticket_purchase_click_cleanup_failed",
        });
    });
});

describe("POST /api/cron/cleanup-ticket-purchase-click-events", () => {
    it("supports manual invocations with the same bearer token", async () => {
        mockQueryRaw.mockResolvedValue([
            {
                deleted_ticket_clicks: "2",
                deleted_discovery_impressions: "3",
            },
        ]);

        const res = await POST(
            makeRequest(
                { authorization: "Bearer test-secret-value" },
                "http://localhost/api/cron/cleanup-ticket-purchase-click-events",
                "POST",
            ),
        );

        expect(res.status).toBe(200);
        expect(await res.json()).toMatchObject({
            deleted: 2,
            deletedDiscoveryImpressions: 3,
        });
        expect(mockQueryRaw).toHaveBeenCalledOnce();
    });
});
