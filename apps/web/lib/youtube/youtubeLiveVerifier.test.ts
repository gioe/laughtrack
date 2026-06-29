import { describe, expect, it, vi } from "vitest";

import { verifyYouTubeLiveState } from "./youtubeLiveVerifier";

function youtubeResponse(body: unknown, init?: ResponseInit): Response {
    return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "content-type": "application/json" },
        ...init,
    });
}

describe("verifyYouTubeLiveState", () => {
    it("calls videos.list and classifies an active live broadcast", async () => {
        const fetchFn = vi.fn(async () =>
            youtubeResponse({
                items: [
                    {
                        id: "live-video",
                        snippet: {
                            channelId: "UC-live-channel",
                            title: "Live from the club",
                            liveBroadcastContent: "live",
                        },
                        liveStreamingDetails: {
                            actualStartTime: "2026-06-29T20:01:00Z",
                            scheduledStartTime: "2026-06-29T20:00:00Z",
                        },
                    },
                ],
            }),
        );

        await expect(
            verifyYouTubeLiveState("live-video", {
                apiKey: "youtube-api-key",
                fetchFn,
            }),
        ).resolves.toEqual({
            status: "live",
            videoId: "live-video",
            channelId: "UC-live-channel",
            title: "Live from the club",
            watchUrl: "https://www.youtube.com/watch?v=live-video",
            actualStartTime: "2026-06-29T20:01:00Z",
            scheduledStartTime: "2026-06-29T20:00:00Z",
        });

        expect(fetchFn).toHaveBeenCalledTimes(1);
        const firstFetchCall = fetchFn.mock.calls[0] as unknown as [string, RequestInit?] | undefined;
        const requestedUrl = new URL(firstFetchCall?.[0] ?? "");
        expect(requestedUrl.origin + requestedUrl.pathname).toBe("https://www.googleapis.com/youtube/v3/videos");
        expect(requestedUrl.searchParams.get("part")).toBe("snippet,liveStreamingDetails");
        expect(requestedUrl.searchParams.get("id")).toBe("live-video");
        expect(requestedUrl.searchParams.get("key")).toBe("youtube-api-key");
    });

    it("classifies upcoming broadcasts as retryable not-yet-live", async () => {
        const fetchFn = vi.fn(async () =>
            youtubeResponse({
                items: [
                    {
                        id: "upcoming-video",
                        snippet: {
                            channelId: "UC-live-channel",
                            title: "Tonight soon",
                            liveBroadcastContent: "upcoming",
                        },
                        liveStreamingDetails: {
                            scheduledStartTime: "2026-06-29T21:00:00Z",
                        },
                    },
                ],
            }),
        );

        await expect(
            verifyYouTubeLiveState("upcoming-video", {
                apiKey: "youtube-api-key",
                fetchFn,
            }),
        ).resolves.toEqual({
            status: "retry",
            reason: "upcoming",
            videoId: "upcoming-video",
            channelId: "UC-live-channel",
            title: "Tonight soon",
            scheduledStartTime: "2026-06-29T21:00:00Z",
        });
    });

    it("classifies missing live streaming details as retryable not-yet-live", async () => {
        const fetchFn = vi.fn(async () =>
            youtubeResponse({
                items: [
                    {
                        id: "new-video",
                        snippet: {
                            channelId: "UC-live-channel",
                            title: "Just notified",
                            liveBroadcastContent: "none",
                        },
                    },
                ],
            }),
        );

        await expect(
            verifyYouTubeLiveState("new-video", {
                apiKey: "youtube-api-key",
                fetchFn,
            }),
        ).resolves.toEqual({
            status: "retry",
            reason: "missing_live_details",
            videoId: "new-video",
            channelId: "UC-live-channel",
            title: "Just notified",
            scheduledStartTime: null,
        });
    });

    it("classifies ended broadcasts as not live", async () => {
        const fetchFn = vi.fn(async () =>
            youtubeResponse({
                items: [
                    {
                        id: "ended-video",
                        snippet: {
                            channelId: "UC-live-channel",
                            title: "Replay",
                            liveBroadcastContent: "none",
                        },
                        liveStreamingDetails: {
                            actualStartTime: "2026-06-29T19:00:00Z",
                            actualEndTime: "2026-06-29T20:00:00Z",
                        },
                    },
                ],
            }),
        );

        await expect(
            verifyYouTubeLiveState("ended-video", {
                apiKey: "youtube-api-key",
                fetchFn,
            }),
        ).resolves.toEqual({
            status: "not_live",
            reason: "ended",
            videoId: "ended-video",
            channelId: "UC-live-channel",
            title: "Replay",
        });
    });
});
