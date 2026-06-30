import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/lib/db", () => ({
    db: {
        youTubeWebSubEvent: {
            findMany: vi.fn(),
        },
    },
}));

vi.mock("@/lib/youtube/youtubeWebSubVerification", () => ({
    verifyPendingYouTubeWebSubEvents: vi.fn(),
}));

import { POST } from "./route";
import { db } from "@/lib/db";
import { verifyPendingYouTubeWebSubEvents } from "@/lib/youtube/youtubeWebSubVerification";

const mockVerifyPending = vi.mocked(verifyPendingYouTubeWebSubEvents);

const ORIGINAL_CRON_SECRET = process.env.CRON_SECRET;
const ORIGINAL_YOUTUBE_DATA_API_KEY = process.env.YOUTUBE_DATA_API_KEY;
const ORIGINAL_YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY;

function makeRequest(headers: Record<string, string> = {}): NextRequest {
    return new NextRequest(
        "http://localhost/api/cron/youtube-websub-verifications",
        {
            method: "POST",
            headers,
        },
    );
}

beforeEach(() => {
    vi.clearAllMocks();
    process.env.CRON_SECRET = "test-secret-value";
    process.env.YOUTUBE_DATA_API_KEY = "youtube-data-api-key";
    delete process.env.YOUTUBE_API_KEY;
});

afterEach(() => {
    if (ORIGINAL_CRON_SECRET === undefined) delete process.env.CRON_SECRET;
    else process.env.CRON_SECRET = ORIGINAL_CRON_SECRET;

    if (ORIGINAL_YOUTUBE_DATA_API_KEY === undefined) {
        delete process.env.YOUTUBE_DATA_API_KEY;
    } else {
        process.env.YOUTUBE_DATA_API_KEY = ORIGINAL_YOUTUBE_DATA_API_KEY;
    }

    if (ORIGINAL_YOUTUBE_API_KEY === undefined)
        delete process.env.YOUTUBE_API_KEY;
    else process.env.YOUTUBE_API_KEY = ORIGINAL_YOUTUBE_API_KEY;
});

describe("POST /api/cron/youtube-websub-verifications", () => {
    it("returns 401 when no Authorization header is provided", async () => {
        const res = await POST(makeRequest());

        expect(res.status).toBe(401);
        expect(mockVerifyPending).not.toHaveBeenCalled();
    });

    it("verifies pending WebSub events with the configured YouTube Data API key", async () => {
        mockVerifyPending.mockResolvedValue({
            total: 3,
            live: 1,
            upcoming: 1,
            notLive: 1,
            duplicate: 0,
            failed: 0,
            skipped: 0,
        });

        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(res.status).toBe(200);
        expect(await res.json()).toEqual({
            total: 3,
            live: 1,
            upcoming: 1,
            notLive: 1,
            duplicate: 0,
            failed: 0,
            skipped: 0,
        });
        expect(mockVerifyPending).toHaveBeenCalledWith({
            dbClient: db,
            apiKey: "youtube-data-api-key",
        });
    });

    it("falls back to the legacy YouTube API key env var", async () => {
        delete process.env.YOUTUBE_DATA_API_KEY;
        process.env.YOUTUBE_API_KEY = "legacy-youtube-api-key";
        mockVerifyPending.mockResolvedValue({
            total: 0,
            live: 0,
            upcoming: 0,
            notLive: 0,
            duplicate: 0,
            failed: 0,
            skipped: 0,
        });

        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(res.status).toBe(200);
        expect(mockVerifyPending).toHaveBeenCalledWith({
            dbClient: db,
            apiKey: "legacy-youtube-api-key",
        });
    });

    it("returns 500 when no YouTube API key is configured", async () => {
        delete process.env.YOUTUBE_DATA_API_KEY;
        delete process.env.YOUTUBE_API_KEY;

        const res = await POST(
            makeRequest({ authorization: "Bearer test-secret-value" }),
        );

        expect(res.status).toBe(500);
        expect(await res.json()).toEqual({
            error: "youtube_api_key_missing",
        });
        expect(mockVerifyPending).not.toHaveBeenCalled();
    });
});
