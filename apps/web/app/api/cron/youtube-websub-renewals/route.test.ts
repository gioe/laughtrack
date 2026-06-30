import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            findMany: vi.fn(),
        },
    },
}));

vi.mock("@/lib/youtube/youtubeWebSubSubscriptions", () => ({
    syncYouTubeWebSubSubscriptions: vi.fn(),
    resolveYouTubeWebSubCallbackUrl: vi.fn(
        (env: Record<string, string | undefined>) =>
            env.YOUTUBE_WEBSUB_CALLBACK_URL,
    ),
}));

import { POST } from "./route";
import { db } from "@/lib/db";
import {
    syncYouTubeWebSubSubscriptions,
    resolveYouTubeWebSubCallbackUrl,
} from "@/lib/youtube/youtubeWebSubSubscriptions";

const mockSync = vi.mocked(syncYouTubeWebSubSubscriptions);
const mockResolveCallbackUrl = vi.mocked(resolveYouTubeWebSubCallbackUrl);

const ORIGINAL_CRON_SECRET = process.env.CRON_SECRET;
const ORIGINAL_CALLBACK_URL = process.env.YOUTUBE_WEBSUB_CALLBACK_URL;

function makeRequest(
    headers: Record<string, string> = {},
    url = "http://localhost/api/cron/youtube-websub-renewals",
): NextRequest {
    return new NextRequest(url, {
        method: "POST",
        headers,
    });
}

beforeEach(() => {
    vi.clearAllMocks();
    process.env.CRON_SECRET = "test-secret-value";
    process.env.YOUTUBE_WEBSUB_CALLBACK_URL =
        "https://laugh-track.com/api/webhooks/youtube";
});

afterEach(() => {
    if (ORIGINAL_CRON_SECRET === undefined) delete process.env.CRON_SECRET;
    else process.env.CRON_SECRET = ORIGINAL_CRON_SECRET;

    if (ORIGINAL_CALLBACK_URL === undefined) {
        delete process.env.YOUTUBE_WEBSUB_CALLBACK_URL;
    } else {
        process.env.YOUTUBE_WEBSUB_CALLBACK_URL = ORIGINAL_CALLBACK_URL;
    }
});

describe("POST /api/cron/youtube-websub-renewals", () => {
    it("returns 401 when no Authorization header is provided", async () => {
        const res = await POST(makeRequest());

        expect(res.status).toBe(401);
        expect(mockSync).not.toHaveBeenCalled();
    });

    it("syncs YouTube WebSub subscriptions with the configured callback URL", async () => {
        mockSync.mockResolvedValue({
            gated: false,
            dryRun: false,
            counts: { subscribe: 1, renew: 1, unsubscribe: 0, skip: 3 },
            total: 2,
            succeeded: 1,
            failed: 1,
            results: [],
        });

        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(res.status).toBe(200);
        expect(await res.json()).toEqual({
            gated: false,
            dryRun: false,
            total: 2,
            succeeded: 1,
            failed: 1,
            counts: { subscribe: 1, renew: 1, unsubscribe: 0, skip: 3 },
        });
        expect(mockResolveCallbackUrl).toHaveBeenCalledWith(process.env);
        expect(mockSync).toHaveBeenCalledWith({
            dbClient: db,
            callbackUrl: "https://laugh-track.com/api/webhooks/youtube",
            logger: console,
            dryRun: false,
        });
    });

    it("passes dryRun through when the dryRun query param is set", async () => {
        mockSync.mockResolvedValue({
            gated: false,
            dryRun: true,
            counts: { subscribe: 2, renew: 0, unsubscribe: 1, skip: 0 },
            total: 3,
            succeeded: 0,
            failed: 0,
            results: [],
        });

        const res = await POST(
            makeRequest(
                { authorization: "Bearer test-secret-value" },
                "http://localhost/api/cron/youtube-websub-renewals?dryRun=1",
            ),
        );

        expect(res.status).toBe(200);
        expect(await res.json()).toMatchObject({ dryRun: true, total: 3 });
        expect(mockSync).toHaveBeenCalledWith(
            expect.objectContaining({ dryRun: true }),
        );
    });

    it("reports the gated result when global feed ingestion is disabled", async () => {
        mockSync.mockResolvedValue({
            gated: true,
            dryRun: false,
            counts: { subscribe: 0, renew: 0, unsubscribe: 0, skip: 0 },
            total: 0,
            succeeded: 0,
            failed: 0,
            results: [],
        });

        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(res.status).toBe(200);
        expect(await res.json()).toMatchObject({ gated: true, total: 0 });
    });
});
