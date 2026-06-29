import { describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            findFirst: vi.fn(),
        },
        youTubeLiveNotification: {
            create: vi.fn(),
        },
    },
}));

vi.mock("@/lib/notifications/youtubeLivePush", () => ({
    sendYouTubeLivePushToTokens: vi.fn(),
}));

import { GET, POST } from "./route";
import { db } from "@/lib/db";
import { sendYouTubeLivePushToTokens } from "@/lib/notifications/youtubeLivePush";

const mockFindComedian = vi.mocked(db.comedian.findFirst);
const mockCreateYouTubeLiveNotification = vi.mocked(
    db.youTubeLiveNotification.create,
);
const mockSendYouTubeLivePushToTokens = vi.mocked(sendYouTubeLivePushToTokens);

function makeGetRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/webhooks/youtube");
    for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
    }

    return new NextRequest(url.toString());
}

function makePostRequest(body: string): NextRequest {
    return new NextRequest("http://localhost/api/webhooks/youtube", {
        method: "POST",
        headers: { "content-type": "application/atom+xml" },
        body,
    });
}

function youtubeEntryXml(channelId = "UC-unknown-channel"): string {
    return `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <yt:videoId>video-123</yt:videoId>
    <yt:channelId>${channelId}</yt:channelId>
    <title>Live set</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=video-123"/>
    <published>2026-06-29T20:00:00+00:00</published>
    <updated>2026-06-29T20:01:30+00:00</updated>
  </entry>
</feed>`;
}

describe("GET /api/webhooks/youtube", () => {
    it("echoes the WebSub challenge when required parameters are present", async () => {
        const res = await GET(
            makeGetRequest({
                "hub.mode": "subscribe",
                "hub.topic":
                    "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-live-channel",
                "hub.challenge": "challenge-token",
            }),
        );

        expect(res.status).toBe(200);
        expect(res.headers.get("content-type")).toContain("text/plain");
        expect(await res.text()).toBe("challenge-token");
    });

    it("rejects challenge requests missing the challenge parameter", async () => {
        const res = await GET(
            makeGetRequest({
                "hub.mode": "subscribe",
                "hub.topic":
                    "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC-live-channel",
            }),
        );

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({ error: "missing_challenge" });
    });
});

describe("POST /api/webhooks/youtube", () => {
    it("ignores malformed XML without sending pushes", async () => {
        const res = await POST(makePostRequest("<feed><entry>"));

        expect(res.status).toBe(202);
        expect(await res.json()).toEqual({ ok: true, processed: 0 });
        expect(mockFindComedian).not.toHaveBeenCalled();
        expect(mockCreateYouTubeLiveNotification).not.toHaveBeenCalled();
        expect(mockSendYouTubeLivePushToTokens).not.toHaveBeenCalled();
    });

    it("ignores unknown YouTube channels without sending pushes", async () => {
        mockFindComedian.mockResolvedValue(null as never);

        const res = await POST(makePostRequest(youtubeEntryXml()));

        expect(res.status).toBe(202);
        expect(await res.json()).toEqual({ ok: true, processed: 0 });
        expect(mockFindComedian).toHaveBeenCalledWith(
            expect.objectContaining({
                where: { youtubeChannelId: "UC-unknown-channel" },
            }),
        );
        expect(mockCreateYouTubeLiveNotification).not.toHaveBeenCalled();
        expect(mockSendYouTubeLivePushToTokens).not.toHaveBeenCalled();
    });
});
