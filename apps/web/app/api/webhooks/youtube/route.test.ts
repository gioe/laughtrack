import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("@/lib/metrics", () => ({
    withRequestMetrics: <T>(handler: T) => handler,
}));

vi.mock("@/lib/db", () => ({
    db: {
        comedian: {
            findFirst: vi.fn(),
        },
        youTubeWebSubEvent: {
            create: vi.fn(),
        },
        youTubeLiveNotification: {
            create: vi.fn(),
        },
    },
}));

import { GET, POST } from "./route";
import { db } from "@/lib/db";

const mockFindComedian = vi.mocked(db.comedian.findFirst);
const mockCreateWebSubEvent = vi.mocked(db.youTubeWebSubEvent.create);
const mockCreateYouTubeLiveNotification = vi.mocked(
    db.youTubeLiveNotification.create,
);

const ORIGINAL_CALLBACK_SECRET = process.env.YOUTUBE_WEBSUB_CALLBACK_SECRET;

function makeGetRequest(params: Record<string, string> = {}): NextRequest {
    const url = new URL("http://localhost/api/webhooks/youtube");
    for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
    }

    return new NextRequest(url.toString());
}

function makePostRequest(
    body: string,
    params: Record<string, string> = { secret: "callback-secret" },
): NextRequest {
    const url = new URL("http://localhost/api/webhooks/youtube");
    for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
    }

    return new NextRequest(url.toString(), {
        method: "POST",
        headers: { "content-type": "application/atom+xml" },
        body,
    });
}

function youtubeEntryXml(channelId = "UC-live-channel"): string {
    return `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <yt:videoId>video-123</yt:videoId>
    <yt:channelId>${channelId}</yt:channelId>
    <title>Live set &amp; Q&amp;A</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=video-123"/>
    <published>2026-06-29T20:00:00+00:00</published>
    <updated>2026-06-29T20:01:30+00:00</updated>
  </entry>
</feed>`;
}

beforeEach(() => {
    vi.clearAllMocks();
    process.env.YOUTUBE_WEBSUB_CALLBACK_SECRET = "callback-secret";
});

afterEach(() => {
    if (ORIGINAL_CALLBACK_SECRET === undefined) {
        delete process.env.YOUTUBE_WEBSUB_CALLBACK_SECRET;
    } else {
        process.env.YOUTUBE_WEBSUB_CALLBACK_SECRET = ORIGINAL_CALLBACK_SECRET;
    }
});

describe("GET /api/webhooks/youtube", () => {
    it("echoes the WebSub challenge when the secret, mode, and YouTube topic are valid", async () => {
        const res = await GET(
            makeGetRequest({
                secret: "callback-secret",
                "hub.mode": "subscribe",
                "hub.topic":
                    "https://www.youtube.com/feeds/videos.xml?channel_id=UC-live-channel",
                "hub.challenge": "challenge-token",
            }),
        );

        expect(res.status).toBe(200);
        expect(res.headers.get("content-type")).toContain("text/plain");
        expect(await res.text()).toBe("challenge-token");
    });

    it("accepts hub.verify_token as the callback secret parameter", async () => {
        const res = await GET(
            makeGetRequest({
                "hub.verify_token": "callback-secret",
                "hub.mode": "unsubscribe",
                "hub.topic":
                    "https://www.youtube.com/feeds/videos.xml?channel_id=UC-live-channel",
                "hub.challenge": "challenge-token",
            }),
        );

        expect(res.status).toBe(200);
        expect(await res.text()).toBe("challenge-token");
    });

    it("rejects challenge requests with an invalid secret", async () => {
        const res = await GET(
            makeGetRequest({
                secret: "wrong-secret-here",
                "hub.mode": "subscribe",
                "hub.topic":
                    "https://www.youtube.com/feeds/videos.xml?channel_id=UC-live-channel",
                "hub.challenge": "challenge-token",
            }),
        );

        expect(res.status).toBe(401);
        expect(await res.json()).toEqual({ error: "Unauthorized" });
    });

    it("rejects challenge requests missing required WebSub fields", async () => {
        const res = await GET(
            makeGetRequest({
                secret: "callback-secret",
                "hub.mode": "subscribe",
                "hub.topic":
                    "https://www.youtube.com/feeds/videos.xml?channel_id=UC-live-channel",
            }),
        );

        expect(res.status).toBe(400);
        expect(await res.json()).toEqual({
            error: "invalid_verification_request",
        });
    });
});

describe("POST /api/webhooks/youtube", () => {
    it("stores raw XML and parsed channel and video metadata without sending notifications", async () => {
        mockFindComedian.mockResolvedValue({ uuid: "comedian-uuid" } as never);
        mockCreateWebSubEvent.mockResolvedValue({ id: 1 } as never);

        const res = await POST(makePostRequest(youtubeEntryXml()));

        expect(res.status).toBe(202);
        expect(await res.json()).toEqual({ ok: true, stored: 1 });
        expect(mockFindComedian).toHaveBeenCalledWith({
            where: { youtubeChannelId: "UC-live-channel" },
            select: { uuid: true },
        });
        expect(mockCreateWebSubEvent).toHaveBeenCalledWith({
            data: expect.objectContaining({
                comedianId: "comedian-uuid",
                youtubeChannelId: "UC-live-channel",
                youtubeVideoId: "video-123",
                videoTitle: "Live set & Q&A",
                videoUrl: "https://www.youtube.com/watch?v=video-123",
                topicUrl:
                    "https://www.youtube.com/feeds/videos.xml?channel_id=UC-live-channel",
                eventStatus: "received",
                publishedAt: new Date("2026-06-29T20:00:00+00:00"),
                feedUpdatedAt: new Date("2026-06-29T20:01:30+00:00"),
                payloadXml: youtubeEntryXml(),
                payloadJson: {
                    entry: {
                        videoId: "video-123",
                        channelId: "UC-live-channel",
                        title: "Live set & Q&A",
                        link: "https://www.youtube.com/watch?v=video-123",
                        publishedAt: "2026-06-29T20:00:00+00:00",
                        updatedAt: "2026-06-29T20:01:30+00:00",
                    },
                },
            }),
        });
        expect(mockCreateYouTubeLiveNotification).not.toHaveBeenCalled();
    });

    it("uses a valid hub.topic query value when supplied", async () => {
        mockFindComedian.mockResolvedValue(null as never);
        mockCreateWebSubEvent.mockResolvedValue({ id: 1 } as never);

        const topic =
            "https://www.youtube.com/feeds/videos.xml?channel_id=UC-topic";
        const res = await POST(
            makePostRequest(youtubeEntryXml("UC-feed"), {
                secret: "callback-secret",
                "hub.topic": topic,
            }),
        );

        expect(res.status).toBe(202);
        expect(mockCreateWebSubEvent).toHaveBeenCalledWith({
            data: expect.objectContaining({
                youtubeChannelId: "UC-feed",
                topicUrl: topic,
            }),
        });
    });

    it("rejects POST requests with an invalid secret before storing the payload", async () => {
        const res = await POST(
            makePostRequest(youtubeEntryXml(), { secret: "wrong-secret-here" }),
        );

        expect(res.status).toBe(401);
        expect(await res.json()).toEqual({ error: "Unauthorized" });
        expect(mockCreateWebSubEvent).not.toHaveBeenCalled();
        expect(mockCreateYouTubeLiveNotification).not.toHaveBeenCalled();
    });

    it("records malformed XML without sending notifications", async () => {
        mockCreateWebSubEvent.mockResolvedValue({ id: 1 } as never);

        const res = await POST(makePostRequest("<feed><entry>"));

        expect(res.status).toBe(202);
        expect(await res.json()).toEqual({
            ok: false,
            stored: 1,
            error: "malformed_xml",
        });
        expect(mockFindComedian).not.toHaveBeenCalled();
        expect(mockCreateWebSubEvent).toHaveBeenCalledWith({
            data: {
                topicUrl: null,
                eventStatus: "failed",
                failureReason: "malformed_xml",
                payloadXml: "<feed><entry>",
                payloadJson: {
                    error: "malformed_xml",
                },
            },
        });
        expect(mockCreateYouTubeLiveNotification).not.toHaveBeenCalled();
    });
});
