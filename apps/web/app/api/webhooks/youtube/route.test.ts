import { beforeEach, describe, expect, it, vi } from "vitest";
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
        userPushToken: {
            updateMany: vi.fn(),
        },
    },
}));

vi.mock("@/lib/notifications/youtubeLivePush", () => ({
    sendYouTubeLivePushToTokens: vi.fn(),
}));

vi.mock("@/lib/youtube/youtubeLiveVerifier", () => ({
    verifyYouTubeLiveState: vi.fn(),
}));

import { GET, POST } from "./route";
import { db } from "@/lib/db";
import { sendYouTubeLivePushToTokens } from "@/lib/notifications/youtubeLivePush";
import { verifyYouTubeLiveState } from "@/lib/youtube/youtubeLiveVerifier";

const mockFindComedian = vi.mocked(db.comedian.findFirst);
const mockCreateYouTubeLiveNotification = vi.mocked(
    db.youTubeLiveNotification.create,
);
const mockUpdatePushTokens = vi.mocked(db.userPushToken.updateMany);
const mockSendYouTubeLivePushToTokens = vi.mocked(sendYouTubeLivePushToTokens);
const mockVerifyYouTubeLiveState = vi.mocked(verifyYouTubeLiveState);

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

beforeEach(() => {
    vi.clearAllMocks();
});

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

    it("creates a dedupe row and sends pushes for opted-in followers with active tokens", async () => {
        mockFindComedian.mockResolvedValue({
            uuid: "comedian-uuid",
            name: "Jane Comic",
            youtubeChannelId: "UC-live-channel",
            favoriteComedians: [
                {
                    user: {
                        userid: "user-1",
                        pushTokens: [
                            {
                                id: "push-token-1",
                                platform: "ios",
                                token: "apns-token",
                            },
                        ],
                    },
                },
            ],
        } as never);
        mockVerifyYouTubeLiveState.mockResolvedValue({
            status: "live",
            videoId: "video-123",
            channelId: "UC-live-channel",
            title: "Live set",
            watchUrl: "https://www.youtube.com/watch?v=video-123",
            actualStartTime: "2026-06-29T20:02:00Z",
            scheduledStartTime: null,
        });
        mockCreateYouTubeLiveNotification.mockResolvedValue({ id: 1 } as never);
        mockSendYouTubeLivePushToTokens.mockResolvedValue(undefined);

        const res = await POST(makePostRequest(youtubeEntryXml("UC-live-channel")));

        expect(res.status).toBe(202);
        expect(await res.json()).toEqual({ ok: true, processed: 1 });
        expect(mockFindComedian).toHaveBeenCalledWith({
            where: { youtubeChannelId: "UC-live-channel" },
            select: expect.objectContaining({
                uuid: true,
                name: true,
                youtubeChannelId: true,
                favoriteComedians: expect.objectContaining({
                    where: {
                        user: {
                            pushShowNotifications: true,
                            pushTokens: { some: { isActive: true } },
                        },
                    },
                }),
            }),
        });
        expect(mockVerifyYouTubeLiveState).toHaveBeenCalledWith(
            "video-123",
            expect.objectContaining({ apiKey: expect.any(String) }),
        );
        expect(mockCreateYouTubeLiveNotification).toHaveBeenCalledWith({
            data: {
                userId: "user-1",
                comedianId: "comedian-uuid",
                youtubeChannelId: "UC-live-channel",
                youtubeVideoId: "video-123",
                videoTitle: "Live set",
                videoUrl: "https://www.youtube.com/watch?v=video-123",
                notificationType: "push",
            },
        });
        expect(mockSendYouTubeLivePushToTokens).toHaveBeenCalledWith({
            input: {
                comedianId: "comedian-uuid",
                comedianName: "Jane Comic",
                youtubeVideoId: "video-123",
                youtubeChannelId: "UC-live-channel",
                videoTitle: "Live set",
                watchUrl: "https://www.youtube.com/watch?v=video-123",
            },
            tokens: [
                {
                    id: "push-token-1",
                    platform: "ios",
                    token: "apns-token",
                },
            ],
            senders: expect.any(Object),
            deactivateToken: expect.any(Function),
        });

        const deactivateToken = mockSendYouTubeLivePushToTokens.mock.calls[0][0]
            .deactivateToken;
        await deactivateToken("push-token-1");
        expect(mockUpdatePushTokens).toHaveBeenCalledWith({
            where: { id: "push-token-1" },
            data: { isActive: false, revokedAt: expect.any(Date) },
        });
    });

    it("does not resend pushes for duplicate user, comedian, video, and notification type rows", async () => {
        mockFindComedian.mockResolvedValue({
            uuid: "comedian-uuid",
            name: "Jane Comic",
            youtubeChannelId: "UC-live-channel",
            favoriteComedians: [
                {
                    user: {
                        userid: "user-1",
                        pushTokens: [
                            {
                                id: "push-token-1",
                                platform: "ios",
                                token: "apns-token",
                            },
                        ],
                    },
                },
            ],
        } as never);
        mockVerifyYouTubeLiveState.mockResolvedValue({
            status: "live",
            videoId: "video-123",
            channelId: "UC-live-channel",
            title: "Live set",
            watchUrl: "https://www.youtube.com/watch?v=video-123",
            actualStartTime: "2026-06-29T20:02:00Z",
            scheduledStartTime: null,
        });
        mockCreateYouTubeLiveNotification.mockRejectedValue({
            code: "P2002",
        });

        const res = await POST(makePostRequest(youtubeEntryXml("UC-live-channel")));

        expect(res.status).toBe(202);
        expect(await res.json()).toEqual({ ok: true, processed: 0 });
        expect(mockCreateYouTubeLiveNotification).toHaveBeenCalledWith(
            expect.objectContaining({
                data: expect.objectContaining({
                    userId: "user-1",
                    comedianId: "comedian-uuid",
                    youtubeVideoId: "video-123",
                    notificationType: "push",
                }),
            }),
        );
        expect(mockSendYouTubeLivePushToTokens).not.toHaveBeenCalled();
    });
});
