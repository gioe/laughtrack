import { beforeEach, describe, expect, it, vi } from "vitest";

import { verifyPendingYouTubeWebSubEvents } from "./youtubeWebSubVerification";

const verifiedAt = new Date("2026-06-30T01:00:00Z");

function makeDb(
    events: Array<{
        id: number;
        youtubeChannelId: string | null;
        youtubeVideoId: string | null;
    }>,
) {
    return {
        youTubeWebSubEvent: {
            findMany: vi.fn(async () => events),
            findFirst: vi.fn(async () => null as { id: number } | null),
            update: vi.fn(async () => ({})),
        },
    };
}

describe("verifyPendingYouTubeWebSubEvents", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("calls videos.list only for events with a known channel and video pair", async () => {
        const db = makeDb([
            {
                id: 1,
                youtubeChannelId: null,
                youtubeVideoId: "video-1",
            },
            {
                id: 2,
                youtubeChannelId: "UC-live-channel",
                youtubeVideoId: null,
            },
            {
                id: 3,
                youtubeChannelId: "UC-live-channel",
                youtubeVideoId: "video-3",
            },
        ]);
        const verifyFn = vi.fn(async () => ({
            status: "live" as const,
            videoId: "video-3",
            channelId: "UC-live-channel",
            title: "Live now",
            watchUrl: "https://www.youtube.com/watch?v=video-3",
            actualStartTime: "2026-06-30T00:58:00Z",
            scheduledStartTime: null,
        }));

        const result = await verifyPendingYouTubeWebSubEvents({
            dbClient: db,
            apiKey: "youtube-api-key",
            verifyFn,
            now: () => verifiedAt,
        });

        expect(db.youTubeWebSubEvent.findMany).toHaveBeenCalledWith({
            where: { eventStatus: "received" },
            select: {
                id: true,
                youtubeChannelId: true,
                youtubeVideoId: true,
            },
            orderBy: { receivedAt: "asc" },
            take: 50,
        });
        expect(verifyFn).toHaveBeenCalledTimes(1);
        expect(verifyFn).toHaveBeenCalledWith("video-3", {
            apiKey: "youtube-api-key",
        });
        expect(db.youTubeWebSubEvent.update).toHaveBeenCalledWith({
            where: { id: 1 },
            data: {
                eventStatus: "failed",
                verificationStatus: "failed",
                failureReason: "missing_channel_or_video",
                verifiedAt,
            },
        });
        expect(db.youTubeWebSubEvent.update).toHaveBeenCalledWith({
            where: { id: 2 },
            data: {
                eventStatus: "failed",
                verificationStatus: "failed",
                failureReason: "missing_channel_or_video",
                verifiedAt,
            },
        });
        expect(result).toMatchObject({
            total: 3,
            live: 1,
            skipped: 2,
        });
    });

    it("marks events live only when the Data API confirms live state", async () => {
        const db = makeDb([
            {
                id: 10,
                youtubeChannelId: "UC-live-channel",
                youtubeVideoId: "live-video",
            },
        ]);
        const verifyFn = vi.fn(async () => ({
            status: "live" as const,
            videoId: "live-video",
            channelId: "UC-live-channel",
            title: "Live from the club",
            watchUrl: "https://www.youtube.com/watch?v=live-video",
            actualStartTime: "2026-06-30T00:58:00Z",
            scheduledStartTime: "2026-06-30T00:55:00Z",
        }));

        const result = await verifyPendingYouTubeWebSubEvents({
            dbClient: db,
            apiKey: "youtube-api-key",
            verifyFn,
            now: () => verifiedAt,
        });

        expect(db.youTubeWebSubEvent.update).toHaveBeenCalledWith({
            where: { id: 10 },
            data: {
                eventStatus: "verified",
                verificationStatus: "live",
                liveBroadcastContent: "live",
                youtubeVideoId: "live-video",
                youtubeChannelId: "UC-live-channel",
                videoTitle: "Live from the club",
                videoUrl: "https://www.youtube.com/watch?v=live-video",
                actualStartTime: new Date("2026-06-30T00:58:00Z"),
                scheduledStartTime: new Date("2026-06-30T00:55:00Z"),
                verifiedAt,
            },
        });
        expect(result.live).toBe(1);
    });

    it("stores upcoming events distinctly without marking them live", async () => {
        const db = makeDb([
            {
                id: 11,
                youtubeChannelId: "UC-live-channel",
                youtubeVideoId: "upcoming-video",
            },
        ]);
        const verifyFn = vi.fn(async () => ({
            status: "retry" as const,
            reason: "upcoming" as const,
            videoId: "upcoming-video",
            channelId: "UC-live-channel",
            title: "Starting soon",
            scheduledStartTime: "2026-06-30T02:00:00Z",
        }));

        const result = await verifyPendingYouTubeWebSubEvents({
            dbClient: db,
            apiKey: "youtube-api-key",
            verifyFn,
            now: () => verifiedAt,
        });

        expect(db.youTubeWebSubEvent.update).toHaveBeenCalledWith({
            where: { id: 11 },
            data: {
                eventStatus: "verified",
                verificationStatus: "upcoming",
                liveBroadcastContent: "upcoming",
                youtubeVideoId: "upcoming-video",
                youtubeChannelId: "UC-live-channel",
                videoTitle: "Starting soon",
                scheduledStartTime: new Date("2026-06-30T02:00:00Z"),
                verifiedAt,
            },
        });
        expect(result).toMatchObject({ live: 0, upcoming: 1 });
    });

    it("stores non-live events distinctly", async () => {
        const db = makeDb([
            {
                id: 12,
                youtubeChannelId: "UC-live-channel",
                youtubeVideoId: "replay-video",
            },
        ]);
        const verifyFn = vi.fn(async () => ({
            status: "not_live" as const,
            reason: "ended" as const,
            videoId: "replay-video",
            channelId: "UC-live-channel",
            title: "Replay",
        }));

        const result = await verifyPendingYouTubeWebSubEvents({
            dbClient: db,
            apiKey: "youtube-api-key",
            verifyFn,
            now: () => verifiedAt,
        });

        expect(db.youTubeWebSubEvent.update).toHaveBeenCalledWith({
            where: { id: 12 },
            data: {
                eventStatus: "verified",
                verificationStatus: "not_live",
                liveBroadcastContent: "none",
                youtubeVideoId: "replay-video",
                youtubeChannelId: "UC-live-channel",
                videoTitle: "Replay",
                suppressionReason: "ended",
                verifiedAt,
            },
        });
        expect(result.notLive).toBe(1);
    });

    it("stores duplicate events distinctly without another videos.list call", async () => {
        const db = makeDb([
            {
                id: 13,
                youtubeChannelId: "UC-live-channel",
                youtubeVideoId: "duplicate-video",
            },
        ]);
        db.youTubeWebSubEvent.findFirst.mockResolvedValue({ id: 7 });
        const verifyFn = vi.fn();

        const result = await verifyPendingYouTubeWebSubEvents({
            dbClient: db,
            apiKey: "youtube-api-key",
            verifyFn,
            now: () => verifiedAt,
        });

        expect(verifyFn).not.toHaveBeenCalled();
        expect(db.youTubeWebSubEvent.update).toHaveBeenCalledWith({
            where: { id: 13 },
            data: {
                eventStatus: "duplicate",
                verificationStatus: "duplicate",
                suppressionReason: "duplicate_of:7",
                verifiedAt,
            },
        });
        expect(result.duplicate).toBe(1);
    });

    it("stores API failures distinctly", async () => {
        const db = makeDb([
            {
                id: 14,
                youtubeChannelId: "UC-live-channel",
                youtubeVideoId: "failed-video",
            },
        ]);
        const verifyFn = vi.fn(async () => {
            throw new Error("quota exceeded");
        });

        const result = await verifyPendingYouTubeWebSubEvents({
            dbClient: db,
            apiKey: "youtube-api-key",
            verifyFn,
            now: () => verifiedAt,
        });

        expect(db.youTubeWebSubEvent.update).toHaveBeenCalledWith({
            where: { id: 14 },
            data: {
                eventStatus: "failed",
                verificationStatus: "failed",
                failureReason: "quota exceeded",
                verifiedAt,
            },
        });
        expect(result.failed).toBe(1);
    });

    it("fails verification when YouTube returns a mismatched channel", async () => {
        const db = makeDb([
            {
                id: 15,
                youtubeChannelId: "UC-expected",
                youtubeVideoId: "wrong-channel-video",
            },
        ]);
        const verifyFn = vi.fn(async () => ({
            status: "live" as const,
            videoId: "wrong-channel-video",
            channelId: "UC-other",
            title: "Wrong channel",
            watchUrl: "https://www.youtube.com/watch?v=wrong-channel-video",
            actualStartTime: "2026-06-30T00:58:00Z",
            scheduledStartTime: null,
        }));

        const result = await verifyPendingYouTubeWebSubEvents({
            dbClient: db,
            apiKey: "youtube-api-key",
            verifyFn,
            now: () => verifiedAt,
        });

        expect(db.youTubeWebSubEvent.update).toHaveBeenCalledWith({
            where: { id: 15 },
            data: {
                eventStatus: "failed",
                verificationStatus: "failed",
                failureReason: "channel_mismatch",
                videoTitle: "Wrong channel",
                verifiedAt,
            },
        });
        expect(result).toMatchObject({ live: 0, failed: 1 });
    });
});
