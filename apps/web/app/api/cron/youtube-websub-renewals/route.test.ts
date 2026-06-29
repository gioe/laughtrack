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
    renewYouTubeWebSubSubscriptions: vi.fn(),
    resolveYouTubeWebSubCallbackUrl: vi.fn(
        (env: Record<string, string | undefined>) =>
            env.YOUTUBE_WEBSUB_CALLBACK_URL,
    ),
}));

import { POST } from "./route";
import { db } from "@/lib/db";
import {
    renewYouTubeWebSubSubscriptions,
    resolveYouTubeWebSubCallbackUrl,
} from "@/lib/youtube/youtubeWebSubSubscriptions";

const mockRenew = vi.mocked(renewYouTubeWebSubSubscriptions);
const mockResolveCallbackUrl = vi.mocked(resolveYouTubeWebSubCallbackUrl);

const ORIGINAL_CRON_SECRET = process.env.CRON_SECRET;
const ORIGINAL_CALLBACK_URL = process.env.YOUTUBE_WEBSUB_CALLBACK_URL;

function makeRequest(headers: Record<string, string> = {}): NextRequest {
    return new NextRequest(
        "http://localhost/api/cron/youtube-websub-renewals",
        {
            method: "POST",
            headers,
        },
    );
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
        expect(mockRenew).not.toHaveBeenCalled();
    });

    it("renews YouTube WebSub subscriptions with the configured callback URL", async () => {
        mockRenew.mockResolvedValue({
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
            total: 2,
            succeeded: 1,
            failed: 1,
        });
        expect(mockResolveCallbackUrl).toHaveBeenCalledWith(process.env);
        expect(mockRenew).toHaveBeenCalledWith({
            dbClient: db,
            callbackUrl: "https://laugh-track.com/api/webhooks/youtube",
            logger: console,
        });
    });
});
